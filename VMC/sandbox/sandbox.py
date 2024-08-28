import base64, cv2, time, asyncio
import numpy as np
from threading import Thread
from scipy import ndimage
from scipy.interpolate import interp1d
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from bell.avr.utils import decorators
from loguru import logger
from collision_avoidance import collision_dectector
from contextvars import ContextVar

class Sandbox(MQTTModule):
    # region Init
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            'avr/thermal/reading': self.handle_thermal,
            'avr/fcm/status': self.handle_status,
            'avr/autonomous/position': self.handle_auton_positions,
            'avr/autonomous/enable': self.handle_autonomous,
            'avr/autonomous/thermal_data': self.handle_thermal_data,
            'avr/apriltags/visible': self.handle_apriltags,
            'avr/fcm/location/local': self.handle_fcm_pos,
            'avr/fusion/position/ned': self.handle_fus_pos,
            'avr/fcm/attitude/euler': self.handle_attitude,
            'avr/sandbox/test': self.handle_testing,
            'avr/fcm/events': self.handle_events,
            }

        # Assorted booleans
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.pause: bool = False
        self.autonomous: bool = False
        self.fcm_connected: bool = False
        self.thermalThreadRun: bool = False # Determines if the thermal thread will be run
        
        # Position vars
        self.fcm_position: list = [0, 0, 0]
        self.fus_position: list = [0, 0, 0]
        self.attitude: dict[str, float] = {"pitch": 0.0, "roll": 0.0, "yaw": 0.0}
        self.start_pos: tuple = (0, 0, 0) # In meters
        self.landing_pads: dict[str, tuple[float, float, float]] = {'start': (0.0, 0.0, 0.0), 'end': (0.0, 0.0, 0.0)} # This is in meters, so compare to FCM coords, not Fusion coords
        
        # Auton vars
        self.mission_waypoints: list[dict] = []
        self.auton_position: int = 0
        
        # Thermal tracking vars
        self.thermal_grid: list[list[int]] = [[0 for _ in range(8)] for _ in range(8)]
        self.target_range: tuple[int, int] = (30, 40)
        self.targeting_step: int = 7
        self.laser_on: bool = False
        self.thermal_state: int = 0 # Value determines the state of the thermal process. 0 for no thermal processing, 1 for thermal hotspot scanning but not targeting, 2 for hotspot targeting
  
        # Flight Controller vars
        self.states: dict[str, str] = {'flightEvent': "UNKNOWN", 'flightMode': "UNKNOWN"} # Dict of current events/modes that pertain to drone operation
        possibleEvents: list[str] = ["IN_AIR", "LANDING", "ON_GROUND", "TAKING_OFF", "GOTO_FINISH", "MISSION_UPLOAD_GOOD", "MISSION_UPLOAD_BAD", "UNKNOWN"]
        possibleModes: list[str] = ["UNKNOWN", "READY", "TAKEOFF", "HOLD", "MISSION", "RETURN_TO_LAUNCH", "LAND", "OFFBOARD", "FOLLOW_ME", "MANUAL", "ALTCTL", "POSCTL", "ACRO", "STABILIZED", "RATTITUDE"]
        self.possibleStates: dict[str, list[str]] = {'flightEvent': possibleEvents, 'flightMode': possibleModes}
        self.disposableEvents: list[str] = [ # List of all the "junk" events that we want to ignore. 3/4 of these are flight mode updates, which are tracked in the status handler
            "fcc_busy_event", "fcc_telemetry_connected_event", "fcc_telemetry_disconnected_event", "fcc_armed_event", "fcc_disarmed_event",
            "fcc_unknown_mode_event", "fcc_ready_mode_event", "fcc_takeoff_mode_event", "fcc_hold_mode_event", "fcc_mission_mode_event",
            "fcc_rtl_mode_event", "fcc_land_mode_event", "fcc_offboard_mode_event", "fcc_follow_mode_event", "fcc_manual_mode_event",
            "fcc_alt_mode_event", "fcc_pos_mode_event", "fcc_acro_mode_event", "fcc_stabilized_mode_event", "fcc_rattitude_mode_event"
            ]
        self.isArmed: bool = False
        
        # Apriltag vars
        self.cur_apriltag: list = [] # List containing the most recently detected apriltag's info. I've added the Bell-provided documentation on the apriltag payload and its content to this pastebin: https://pastebin.com/Wc7mXs7W
        self.apriltag_ids: list = [] # List containing every apriltag ID that has been detected
        self.flash_queue: list = [] # List containing all the IDs that are queued for LED flashing
        self.normal_color: tuple[int, int, int, int] = [255, 78, 205, 196] # wrgb
        self.flash_color: tuple[int, int, int, int] = [255, 255, 0, 0] # wrgb
        
        self.threads: dict
        
        
    def set_threads(self, threads: dict):
        self.threads: dict = threads

    # region Topic Handlers
    def handle_thermal(self, payload: AvrThermalReadingPayload) -> None:
        # Handle the raw data from the thermal camera
        data = payload['data']
        # decode the payload
        base64Decoded = data.encode("utf-8")
        asbytes = base64.b64decode(base64Decoded)
        pixel_ints = list(bytearray(asbytes))
        k = 0
        for i in range(len(self.thermal_grid)):
            for j in range(len(self.thermal_grid[0])):
                self.thermal_grid[j][i] = pixel_ints[k]
                k+=1
        
    def handle_status(self, payload: AvrFcmStatusPayload) -> None:
        # Set the flight controller's mode and armed status
        if self.states['flightMode'] != payload['mode']:
            logger.debug(f"Flight Mode Update || Flight Mode: {payload['mode']}")
            self.states['flightMode'] = payload['mode']
        self.isArmed = payload['armed']
        self.fcm_connected = True
        
    def handle_auton_positions(self, payload: dict) -> None:
        self.auton_position = payload['position']
    
    def handle_autonomous(self, payload: AvrAutonomousEnablePayload) -> None:
        self.autonomous = payload['enabled']
    
    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None: # This handler is only called when an apriltag is scanned and processed successfully
        self.cur_apriltag = payload['tags']

        if payload['tags'][0]['id'] not in self.apriltag_ids:
            # If we haven't detected this apriltag before, add it to a list of detected IDs and queue an LED flash (LED flashing is done in the CIC thread)
            self.apriltag_ids.append(payload['tags'][0]['id'])
            self.flash_queue.append(payload['tags'][0]['id'])
            logger.debug(f"New AT detected, ID: {payload['tags'][0]['id']}")
        
    def handle_thermal_data(self, payload: dict) -> None:
        if payload.keys().__contains__('state'):
            self.thermal_state = payload['state']
            if self.thermal_state == 2:
                turret_angles = [1450, 1450]
                self.send_message(
                            "avr/pcm/set_servo_abs",
                            AvrPcmSetServoAbsPayload(servo= 2, absolute= turret_angles[0])
                        )
                self.send_message(
                            "avr/pcm/set_servo_abs",
                            AvrPcmSetServoAbsPayload(servo= 3, absolute= turret_angles[1])
                        )
        if payload.keys().__contains__('range'):
            self.target_range = payload['range'][:2]
            logger.debug(self.target_range)
            self.targeting_step = int(payload['range'][2])

    def handle_fcm_pos(self, payload: AvrFcmLocationLocalPayload) -> None:
        self.fcm_position = [payload['dX'], payload['dY'], payload['dZ']*-1]
    
    def handle_fus_pos(self, payload: AvrFusionPositionNedPayload) -> None:
        self.fus_position = [payload['n'], payload['e'], payload['d']*-1]
    
    def handle_attitude(self, payload: AvrFcmAttitudeEulerPayload) -> None:
        self.attitude["pitch"] = payload["pitch"]
        self.attitude["roll"] = payload["roll"]
        self.attitude["yaw"] = payload["yaw"]

    def handle_testing(self, payload: dict):
        name = payload['testName']
        state = payload['testState']
        if not state: # If a test is being deactivated then we don't need to worry about it
            return
        elif name == 'kill':
            self.send_action("kill", {})
        elif name == 'arm':
            self.set_armed(True)
        elif name == 'disarm':
            self.set_armed(False)
        elif name == 'zero ned':
            self.send_message('avr/fcm/capture_home', {})
        
        # Once the test has been run, mark it as inactive
        self.send_message('avr/sandbox/test', {'testName': name, 'testState': False})
            
    def handle_events(self, payload: AvrFcmEventsPayload):
        """Event names are transformed to help weed out all the extra events. Only the important events are recorded and logged"""
        eventName = payload['name']

        if eventName in self.disposableEvents: # Discard unwanted events
            return
        
        # Handle flight events (match-case statements do not work on the drone's version of Python [2.7.17])
        if eventName == 'landed_state_in_air_event':
            newState = "IN_AIR"
        elif eventName == 'landed_state_landing_event':
            newState = "LANDING"
        elif eventName == 'landed_state_on_ground_event':
            newState = "ON_GROUND"
        elif eventName == 'landed_state_taking_off_event':
            newState = "TAKING_OFF"
        elif eventName == 'go_to_started_event':
            newState = "GOTO_START"
        elif eventName == 'goto_complete_event':
            newState = "GOTO_FINISH"
        elif eventName == 'mission_upload_success_event':
            newState = 'MISSION_UPLOAD_GOOD'
        elif eventName == 'mission_upload_failed_event':
            newState = 'MISSION_UPLOAD_BAD'
        else:
            newState = "UNKNOWN"
        
        if newState != self.states['flightEvent']:
            logger.debug(f"New Flight Event: {newState}")
            self.states['flightEvent'] = newState


    # region Thermal Thread
    def Thermal(self) -> None:
        logger.debug('Thermal Scanning/Targeting Thread: Online')
        turret_angles = [1450, 1450]
        while True:
            
            if self.thermal_state == 0: # If you aren't scanning or targeting, then don't scan or target
                continue
            
            # Thermal scanning process
            img = np.array(self.thermal_grid) # Create mask of pixels above thermal threshold
            lowerb = np.array(self.target_range[0], np.uint8)
            upperb = np.array(self.target_range[1], np.uint8)
            mask = cv2.inRange(img, lowerb, upperb)
            logger.debug(f'\n{mask}')
            if np.all(np.array(mask) == 0):
                continue
            blobs = mask > 100
            labels, nlabels = ndimage.label(blobs)
            # find the center of mass of each label
            t = ndimage.center_of_mass(mask, labels, np.arange(nlabels) + 1 )
            # calc sum of each label, this gives the number of pixels belonging to the blob
            s  = ndimage.sum(blobs, labels,  np.arange(nlabels) + 1 )
            heat_center = [float(x) for x in t[s.argmax()][::-1]]
            move_range = [15, -15]
            m = interp1d([0, 8], move_range)
            logger.debug(heat_center)

            if self.thermal_state < 2: # If you aren't targeting then don't target
                continue
            elif not self.laser_on: # If you are targeting, make sure the laser is on
                self.set_laser(True)
            
            # This just moves reactily in small steps, it also sucks ass.
            if heat_center[0] > 4:
                turret_angles[0] += self.targeting_step
                self.move_servo(2, turret_angles[0])
            elif heat_center[0] < 4:
                turret_angles[0] -= self.targeting_step
                self.move_servo(2, turret_angles[0])
            if heat_center[1] < 4:
                turret_angles[1] += self.targeting_step
                self.move_servo(3, turret_angles[1])
            elif heat_center[1] > 4:
                turret_angles[1] -= self.targeting_step
                self.move_servo(3, turret_angles[1])

    # region CIC Thread
    def CIC(self) -> None:
        logger.debug('Command, Information, & Control Thread: Online')
        status_thread = Thread(target=self.status)
        status_thread.daemon = True
        status_thread.start()
        light_init = False
        last_flash: dict = {'time': 0, 'iter': 0} # Contains the data of the last LED flash, including the time that the flash happened and the number of flashes we've done for that ID
        while True:
            if not self.CIC_loop:
                continue
            
            # Once the FCM is initialized, do some housekeeping
            if self.fcm_connected and not light_init:
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color)) # Turn on the lights
                """
                FROM LAST YEAR
                for i in range (5, 8): # Opening the sphero holders
                    self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload(servo= i, action= 'open')
                    )
                """
                self.set_geofence(200000000, 850000000, 400000000, 1050000000) # Set the geofence from 20 N, 85 W to 40 N, 105 W
                light_init = True

            # Flashing the LEDs when a new apriltag ID is detected
            if self.flash_queue and time.time() > last_flash['time'] + 1: # Make sure it's been at least one second since the last LED flash
                self.send_message('avr/pcm/set_temp_color', AvrPcmSetTempColorPayload(wrgb=self.flash_color, time=.5))
                last_flash['time'] = time.time()
                # logger.debug(f"Flashing LEDs for ID: {self.flash_queue[0]}")
                if last_flash['iter'] >= 2:
                    last_flash['iter'] = 0
                    del self.flash_queue[0]
                else:
                    last_flash['iter'] += 1
            
    # region Status Sub-Thread
    def status(self):
        """ Shows the stats of the threads.
        """
        logger.debug('Status Sub-Thread: Online')
        onoffline = {True: 'Online', False: 'Offline'}
        onoff = {True: 'On', False: 'Off'}
        while True:
            if self.show_status:
                time.sleep(0.5)
                self.send_message(
                    'avr/sandbox/CIC',
                    {'Thermal Scanning/Targeting': onoffline[self.threads['thermal'].is_alive()], 'CIC': onoffline[self.threads['cic'].is_alive()], 'Autonomous': onoffline[self.threads['auto'].is_alive()], 'Laser': onoff[self.laser_on]}
                )
    
    # region Autonomous Thread
    def Autonomous(self):
        # sourcery skip: extract-duplicate-method, extract-method
        logger.debug("Autonomous Thread: Online")
        auton_init: bool = False
        while True:
            if not self.autonomous:
                continue
            
            # Auton initialization process
            if not auton_init:
                self.send_message('avr/fcm/capture_home', {}) # Capture home coordinates (zero NED position, like how you zero a scale)
                auton_init = True

            if self.auton_position == 0:
                continue

            # \\\\\\\\\\ Button-controlled auton //////////
            # more precise movement?
            if self.auton_position == 1:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0, goto_hold_time=5, acceptanceRad=.05)
                self.add_mission_waypoint('goto', (1, 0, 1), yaw_angle=0, goto_hold_time=5, acceptanceRad=.05)
                self.add_mission_waypoint('land', (1, 0, 0))
                self.upload_and_engage_mission()
                self.setPosition()

            # takeoff, go forward and hold for 20 seconds, land
            if self.auton_position == 2:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0)
                self.add_mission_waypoint('goto', (1, 0, 1), yaw_angle=0, goto_hold_time=20)
                self.add_mission_waypoint('land', (0, 0, 1), yaw_angle=0)
                self.upload_and_engage_mission()
                self.setPosition(3)

            # go a little bit to the right
            if self.auton_position == 3:
                time.sleep(10)

                self.send_action('goto_location_ned', {'n': 0, 'e': 1, 'd': -1, 'heading': 0, 'rel': True})
                self.wait_for_state("flightEvent", "GOTO_FINISH", 10)
                
                self.setPosition()

            # takeoff, move in a square, land
            if self.auton_position == 4:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0)
                self.add_mission_waypoint('goto', (1, 0, 1), yaw_angle=45)
                self.add_mission_waypoint('goto', (1, 1, 1), yaw_angle=135)
                self.add_mission_waypoint('goto', (0, 1, 1), yaw_angle=225)
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0)
                self.add_mission_waypoint('land', (0, 0, 0), yaw_angle=0)
                self.upload_and_engage_mission()
                self.setPosition()
            
            # More complex movement pattern
            if self.auton_position == 5:
                self.add_mission_waypoint('goto', (0, 0, 1))
                self.add_mission_waypoint('goto', (1, .25, 1), 20, 3)
                self.add_mission_waypoint('goto', (2, .25, 1), 0, 3)
                self.add_mission_waypoint('goto', (2, 2, 1.5), 270, 3)
                self.add_mission_waypoint('goto', (0, 0, 1))
                self.add_mission_waypoint('land', (0, 0, 0))
                self.upload_and_engage_mission()
                self.setPosition()
            
            # Do you even need a 'takeoff' command?
            if self.auton_position == 6:
                self.add_mission_waypoint('goto', (1, 0, 1), goto_hold_time=5)
                self.add_mission_waypoint('land', (1, 0, 0))
                self.upload_and_engage_mission()
                self.setPosition()

    

    # region Mission and Waypoint methods
    # PX4 mission mode docs: https://docs.px4.io/main/en/flight_modes_mc/mission.html
    def add_mission_waypoint(self, waypointType: Literal["goto", "land"], coords: tuple[float, float, float], yaw_angle: float = 0, goto_hold_time: float = 0, acceptanceRad: float = .10) -> None:
        """Add a waypoint to the mission_waypoints list.

        Args:
            waypointType (Literal["goto", "land"]): Must be one of `goto` or `land`. If the drone is landed, it will takeoff first before preceeding towards the waypoint
            coords (tuple[float, float, float]): Absolute waypoint destination coordinates, in meters, as (fwd, right, up)
            yaw_angle (float, optional): Heading that the drone will be facing when it reaches the waypoint. Defaults to 0, which is straight forward from start
            goto_hold_time (float, optional): How long the drone will hold its position at a waypoint, in seconds. Only matters for `goto` waypoints. Defaults to 0
            goto_acceptance_radius (float, optional): Acceptance radius in meters (if the sphere with this radius is hit, the waypoint counts as reached). Only matters for `goto` waypoints. Defaults to .10 (roughly 4 inches)
 
        MAVLink mission syntax docs:
        https://mavlink.io/en/messages/common.html#MAV_CMD_NAV_WAYPOINT
        """
        # Add the waypoint to the list of waypoints
        self.mission_waypoints.append({'type': waypointType, 'n': coords[0], 'e': coords[1], 'd': coords[2] * -1, 'yaw': yaw_angle, 'holdTime': goto_hold_time, 'acceptRadius': acceptanceRad})
    
    def clear_mission_waypoints(self) -> None:
        """Clear the mission_waypoints list
        """
        self.mission_waypoints = []

    def upload_and_engage_mission(self, delay: float = -1) -> None:
        """Upload a mission to the flight controller, mission waypoints are represented in the self.mission_waypoints list.

        Args:
            delay (float, optional): Delay in seconds between uploading the mission and starting the mission. Negative or no delay will cause the mission to start as soon as the upload completes.
        """
        self.send_action('upload_mission', {'waypoints': self.mission_waypoints})
        self.clear_mission_waypoints()
        # If delay is left blank the mission should start as soon as the mission upload completes
        if delay < 0:
            self.wait_for_state('flightEvent', 'MISSION_UPLOAD_GOOD')
        else:
            time.sleep(delay)

        self.start_mission()
    
    def start_mission(self) -> None:
        """Arms the drone & starts the uploaded mission
        """
        self.set_armed(True)
        time.sleep(.1)
        self.send_action('start_mission')


    # region Messenger methods
    def set_geofence(self, min_lat: int, min_lon: int, max_lat: int, max_lon: int):
        self.send_action('set_geofence', {'min_lat': min_lat, 'min_lon': min_lon, 'max_lat': max_lat, 'max_lon': max_lon})
    
    def set_armed(self, armed: bool) -> None:
        """Arm or disarm the FCC
        
        Args:
            armed (bool): True to arm the drone, False to disarm
        """
        if armed:
            self.send_action("arm")
        else:
            self.send_action("disarm")
        
        while self.isArmed != armed: # Wait until the drone is in the requested state
            time.sleep(.01)

    def move_servo(self, id, angle) -> None:
        self.send_message("avr/pcm/set_servo_abs",AvrPcmSetServoAbsPayload(servo=id, absolute=angle))

    def send_action(self, action: str, payload: dict = {}):
        # sourcery skip: default-mutable-arg
        """Send one of many possible action payloads to the `avr/fcm/actions` MQTT topic.

        Args:
            action (str): The action you want to send
            payload (dict, optional): The payload of the action you want to send. Defaults to {}.
        """
        self.send_message('avr/fcm/actions', {'action': action, 'payload': payload})

    def set_laser(self, state: bool) -> None:
        self.laser_on = state
        if state:
            topic = "avr/pcm/set_laser_on"
            payload = AvrPcmSetLaserOnPayload()
        else:
            topic = "avr/pcm/set_laser_off"
            payload = AvrPcmSetLaserOffPayload()
        self.send_message(topic, payload)
    
    def setAutonomous(self, isEnabled: bool) -> None:
        """Broadcast given boolean for topic `avr/autonomous/enable`, in the `enabled` payload. This will update values on both the sandbox and the GUI.
        """
        self.send_message('avr/autonomous/enable', AvrAutonomousEnablePayload(enabled=isEnabled))
    
    def setPosition(self, number: int = 0) -> None:
        """Broadcast current auton position
        """
        self.send_message("avr/autonomous/position", {"position": number})

    def set_objscanner_params(self, state: int) -> None:
        """Handles sending parameter updates to the object scanner

        Args:
            state (int): Value determines the state of the object scanner. 0 is no scanning, 1 is scan for objects and report relevant data, 2 is automatically move towards detected objects (aka auto-align)
        """
        self.send_message('avr/objscanner/params', {"state": state})

    
    # region Helper methods
    def wait_for_apriltag_id(self, id: int, timeout: float = 5) -> bool:
        """Wait until a specificied Apriltag ID is detected, or a timeout is reached

        Args:
            id (int): The ID of the apriltag we're looking for
            timeout (float): The time in seconds until the wait times out. Defaults to 5.

        Returns:
            bool: True if the AT was detected, False if timeout was reached
        """
        start_time = time.time()
        while start_time + timeout > time.time():
            try:
                if self.cur_apriltag[0]['id'] == id:
                    return True
            except IndexError: # Catch the IndexError that is thrown if we haven't yet scanned an apriltag (i.e. the list is empty)
                pass
            time.sleep(.025) # Given the low FPS of the CSI camera (which scans for apriltags), this sleep command won't lead to skipping over a detected apriltag
        logger.debug(f'Timeout reached while waiting to detect Apriltag {id}')
        return False

    def wait_for_state(self, stateKey: Literal["flightEvent", "flightMode"], desiredVal: str, timeout: float = 5) -> bool:
        """Wait until a desired value is present for a specific key in the states dict

        Args:
            stateKey (Literal["flightEvent", "flightMode"]): The key of the value in the self.states dict that we're waiting for
            desiredVal (str): The desired value that we're waiting for
            timeout (float, optional): The time in seconds that we wait for. Defaults to 5.

        Returns:
            bool: True if desired value is found, False if timeout is reached
        """
        try:
            if desiredVal not in self.possibleStates[stateKey]: # Check to make sure that we're waiting for a valid key that can contain the given value
                logger.error(f'The given key {stateKey} cannot contain the value {desiredVal}')
                return False
        except KeyError as e: # If you get this error it means the key you're looking for doesn't exist
                logger.error(e)
                return False

        start_time = time.time()
        while start_time + timeout > time.time():
            if self.states[stateKey] == desiredVal:
                return True
            time.sleep(.005)
        logger.debug(f'Timeout reached while waiting for {stateKey} value {desiredVal}')
        return False
    
    # From Quentin: Bell gives us field dimensions in inches then programs the drone to use meters because fuck you
    def inchesToMeters(self, inches: float) -> float:
        """ Converts inches to meters
        
        Args:
            inches (float): Self explanatory, distance in inches

        Returns:
            float: Distance in meters
        """
        return inches/39.37
    
# region Main process
if __name__ == '__main__':
    box = Sandbox()
    
    # Create Threads
    thermal_thread = Thread(target=box.Thermal, daemon=True)
    if box.thermalThreadRun: thermal_thread.start()
    
    CIC_thread = Thread(target=box.CIC, daemon=True)
    CIC_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous, daemon=True)
    autonomous_thread.start()
    
    box.set_threads({'thermal': thermal_thread, 'cic': CIC_thread, 'auto': autonomous_thread})
    
    box.run()
