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
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            'avr/thermal/reading': self.handle_thermal,
            'avr/fcm/status': self.handle_status,
            'avr/autonomous/building/drop': self.handle_building_drop,
            'avr/autonomous/enable': self.handle_autonomous,
            'avr/autonomous/recon': self.handle_recon,
            'avr/autonomous/thermal_range': self.handle_thermal_range,
            'avr/autonomous/thermal_targeting': self.handle_thermal_tracker,
            'avr/apriltags/visible': self.handle_apriltags,
            'avr/vio/position/ned': self.handle_vio_position,
            'avr/sandbox/user_in': self.handle_user_in,
            'avr/fusion/position/ned': self.handle_pos,
            'avr/sandbox/test': self.handle_testing,
            'avr/fcm/events': self.handle_events,
            }

        # Assorted booleans
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.pause: bool = False
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.recon: bool = False
        self.fcm_connected: bool = False
        self.thermalAutoAim: bool = False
        
        # Position vars
        self.position: list = [0, 0, 0]
        self.start_pos: tuple = (180, 50, 0)
        self.building_loc: dict[str, tuple[int, int, int]] = {'Building 0': (404, 120, 55), 'Building 1': (404, 45, 55), 'Building 2': (356, 177, 69), 'Building 3': (356, 53, 69), 'Building 4': (310, 125, 121), 'Building 5': (310, 50, 121)}
        self.landing_pads: dict[str, tuple[int, int, int]] = {'ground': (180, 50, 12), 'building': (231, 85, 42)}
        
        # Auton vars
        self.mission_waypoints: list[dict] = []
        self.building_drops: list[bool] = [False, False, False, False, False, False]
        # Advanced Auton vars
        self.sanity: str = 'Gone'
        self.do_pathfinding: bool = False
        self.col_test = collision_dectector((472, 170, 200), 17.3622)
        
        # Thermal tracking vars
        self.thermal_grid: list[list[int]] = [[0 for _ in range(8)] for _ in range(8)]
        self.target_range: tuple[int, int] = (30, 40)
        self.targeting_step: int = 7
        self.laser_on: bool = False
  
        # Flight Controller vars
        self.states: dict[str, str] = {'flightEvent': "UNKNOWN", 'flightMode': "UNKNOWN"} # Dict of current events/modes that pertain to drone operation
        possibleEvents: list[str] = ["IN_AIR", "LANDING", "ON_GROUND", "TAKING_OFF", "UNKNOWN"]
        possibleModes: list[str] = ["UNKNOWN", "READY", "TAKEOFF", "HOLD", "MISSION", "RETURN_TO_LAUNCH", "LAND", "OFFBOARD", "FOLLOW_ME", "MANUAL", "ALTCTL", "POSCTL", "ACRO", "STABILIZED", "RATTITUDE"]
        self.possibleStates: dict[str, list[str]] = {'flightEvent': possibleEvents, 'flightMode': possibleModes}
        self.isArmed: bool = False
        
        # Apriltag vars
        self.cur_apriltag: list = [] # List containing the most recently detected apriltag's info. I've added the Bell-provided documentation on the apriltag payload and its content to this pastebin: https://pastebin.com/Wc7mXs7W
        self.apriltag_ids: list = [] # List containing every apriltag ID that has been detected
        self.flash_queue: list = [] # List containing all the IDs that are queued for LED flashing, along with their in
        self.normal_color: tuple[int, int, int, int] = [255, 78, 205, 196] # wrgb
        self.flash_color: tuple[int, int, int, int] = [255, 255, 0, 0] # wrgb
        
        self.threads: dict
        
        # Only turn on if using home field
        homefield_test: bool = False
        if homefield_test:
            self.start_pos = (231, 85, 52)
            self.building_loc = {building: tuple(list(loc)[2]*.75) for building, loc in self.building_loc.items()}
        
        
    def set_threads(self, threads: dict):
        self.threads: dict = threads

    # ===================
    # Topic Handlers
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
        
    def handle_building_drop(self, payload: AvrAutonomousBuildingDropPayload) -> None:
        self.building_drops[payload['id']] = payload['enabled']
    
    def handle_autonomous(self, payload: AvrAutonomousEnablePayload) -> None:
        self.autonomous = payload['enabled']
        
    def handle_recon(self, payload) -> None:
        self.recon = payload['enabled']
                
    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None: # This handler is only called when an apriltag is scanned and processed successfully
        self.cur_apriltag = payload['tags']

        if not payload['tags'][0]['id'] in self.apriltag_ids:
            # If we haven't detected this apriltag before, add it to a list of detected IDs and queue an LED flash (LED flashing is done in the CIC thread)
            self.apriltag_ids.append(payload['tags'][0]['id'])
            self.flash_queue.append(payload['tags'][0]['id'])
            logger.debug(f"New AT detected, ID: {payload['tags'][0]['id']}")
    
    def handle_vio_position(self, payload: AvrVioPositionNedPayload) -> None:
        self.position = [payload['n'], # X
                         payload['e'], # Y
                         payload['d']] # Z
        
    def handle_user_in(self, payload: dict) -> None:
        try:
            self.pause = payload['pause']
        except:
            pass
        
    def handle_thermal_tracker(self, payload: dict) -> None:
        self.auto_target = payload['enabled']
        if self.auto_target:
            turret_angles = [1450, 1450]
            self.send_message(
                        "avr/pcm/set_servo_abs",
                        AvrPcmSetServoAbsPayload(servo= 2, absolute= turret_angles[0])
                    )
            self.send_message(
                        "avr/pcm/set_servo_abs",
                        AvrPcmSetServoAbsPayload(servo= 3, absolute= turret_angles[1])
                    )
    
    def handle_thermal_range(self, payload: dict) -> None:
        self.target_range = payload['range'][0:2]
        logger.debug(self.target_range)
        self.targeting_step = int(payload['range'][2])
        
    def handle_pos(self, payload: AvrFusionPositionNedPayload):
        # NOTE Check if direction is based on drone start or global
        self.position = [payload['n'], payload['e'], payload['d']]
        
    def handle_testing(self, payload: str):
        name = payload['testName']
        state = payload['testState']
        if not state: # If a test is being deactivated then we don't need to worry about it
            return
        elif name == 'upload flight test':
            # Test automatically uploading and starting mission with one command
            self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0)
            self.add_mission_waypoint('land', (0, 0, 0))
            self.upload_and_engage_mission()
        elif name == 'start flight test':
            self.start_mission()
        elif name == 'sound':
            self.sound_laptop("sound_1")
        elif name == 'arm':
            self.setArmed(True)
        elif name == 'disarm':
            self.setArmed(False)
        elif name == 'Zero NED':
            self.send_message('avr/fcm/capture_home', {})
        
        # Once the test has been run, mark it as inactive
        self.send_message('avr/sandbox/test', {'testName': name, 'testState': False})
            
    def handle_events(self, payload: AvrFcmEventsPayload):
        """ `AvrFcmEventsPayload`:\n\n`name`: event name,\n\n`payload`: event payload"""
        eventName = payload['name']

        # Handle flight states
        if eventName == 'landed_state_in_air_event':
            newState = "IN_AIR"
        elif eventName == 'landed_state_landing_event':
            newState = "LANDING"
        elif eventName == 'landed_state_on_ground_event':
            newState = "ON_GROUND"
        elif eventName == 'landed_state_taking_off_event':
            newState = "TAKING_OFF"
        else:
            newState = "UNKNOWN"
        
        if newState != self.states['flightEvent']:
            logger.debug(f"Flight State Update || Flight State: {newState}")
            self.states['flightEvent'] = newState


    # ===============
    # Threads
    def targeting(self) -> None: # Currently useless as there is no application for it, still works though.
        logger.debug('Thermal Tracking Thread: Online')
        turret_angles = [1450, 1450]
        while True:
            if not self.auto_target:
                if self.laser_on:
                    self.set_laser(False)
                continue
            if not self.laser_on:
                self.set_laser(True)
                
            # Create mask of pixels above thermal threshold
            img = np.array(self.thermal_grid)
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
            
            # Couldn't figure out the math to move the gimbal to the right position
            # so this justs moves reactily in small steps, it also sucks ass.
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
                self.sound_laptop("startup",".mp3") # Play startup sound
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color)) # Turn on the lights
                """for i in range (5, 8): # Opening the sphero holders
                    self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload(servo= i, action= 'open')
                    )"""
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

            # Don't know what coords this corresponds to but it might be important
            if self.position == (42, 42, 42):
                self.sanity = "Here"
            else:
                self.sanity = 'Gone'


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
                    {'Thermal Targeting': onoffline[self.threads['thermal'].is_alive()], 'CIC': onoffline[self.threads['cic'].is_alive()], 'Autonomous': onoffline[self.threads['auto'].is_alive()], 'Recon': onoff[self.recon], 'Sanity': self.sanity, 'Laser': onoff[self.laser_on]}
                )
    
    def Autonomous(self): # What is this, headache city?
        logger.debug('Autonomous Thread: Online')
        # auton_init: bool = False
        while True:
            if not self.autonomous:
                continue
            
            # # Auton initialization process
            # if not auton_init:
            #     self.send_message('avr/fcm/capture_home', {}) # Capture home coordinates (zero NED position, like how you zero a scale)
            #     time.sleep(.5)
            #     self.setArmed(True) # Arm da drone
            #     auton_init = True


            # \\\\\\\\\\ Button-controlled auton //////////
            # takeoff -> go fwd -> go fwd, turn around -> land test
            if self.building_drops[0]:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0, goto_hold_time=3)
                self.add_mission_waypoint('goto', (1, 0, 1), yaw_angle=0, goto_hold_time=3)
                self.add_mission_waypoint('goto', (2, 0, 1), yaw_angle=180, goto_hold_time=3)
                self.add_mission_waypoint('land', (2, 0, 0))
                self.upload_and_engage_mission(5)
                self.setBuildingDrop(0, False)

            # goto -> land test
            if self.building_drops[1]:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0)
                self.add_mission_waypoint('land', (0, 0, 0))
                self.upload_and_engage_mission(5)
                self.setBuildingDrop(1, False)

            # takeoff -> go fwd -> go fwd, turn around -> land test (No delay between upload, arm, and start)
            if self.building_drops[2]:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=0, goto_hold_time=3)
                self.add_mission_waypoint('goto', (1, 0, 1), yaw_angle=0, goto_hold_time=3)
                self.add_mission_waypoint('goto', (2, 0, 1), yaw_angle=180, goto_hold_time=3)
                self.add_mission_waypoint('land', (2, 0, 0))
                self.upload_and_engage_mission()
                self.setBuildingDrop(2, False)

            # Yaw test
            if self.building_drops[3]:
                self.add_mission_waypoint('goto', (0, 0, 1), yaw_angle=90)
                self.upload_and_engage_mission(3)
                self.setBuildingDrop(3, False)


            # \\\\\\\\\\ Fully automatic auton - Will takeoff, move in a square, then land //////////
            if self.recon:
                self.add_mission_waypoint('takeoff', (0, 0, 1)) # takeoff (alt 1 meter??)
                self.add_mission_waypoint('goto', (1, 0, 1)) # fwd 1 meter
                self.add_mission_waypoint('goto', (0, 1, 1)) # right 1 meter
                self.add_mission_waypoint('goto', (-1, 0, 1)) # back 1 meter
                self.add_mission_waypoint('goto', (0, -1, 1)) # left 1 meter
                self.add_mission_waypoint('land', (0, 0, 0)) # land
                self.upload_and_engage_mission(5)

                self.setRecon(False)


    # ========================
    # Drone Control Comands
    
    def move(self, pos: tuple, heading: float = 0, pathing: bool = False) -> None:
        """ Depreciated
        -
        Move the AVR to a specified position on the field

        Args:
            pos (tuple): Absolute position on the field, in inches, as (x: fwd, y: right, z: up)
            heading (float, optional): Heading that the drone will face while moving (?) as a decimal (?). Defaults to 0.
            pathing (bool, optional): If the AVR will attempt to path around buildings (?). Defaults to False.
        """
        if not pathing or not self.col_test.path_check(self.position, pos):
            relative_pos = [0, 0, 0]
            for i in range(3):
                # Get the relative coords of the destination by adding the absolute position to the starting position
                relative_pos[i] = self.inchesToMeters(pos[i]) + self.start_pos[i]
            # Reverse the value of the Z coord since the MQTT syntax is <dis_down> for some reason
            relative_pos[2] *= -1
            # Report the destination and send the command
            logger.debug(f'NED: {relative_pos}')
            self.send_action('goto_location_ned', {'n': relative_pos[0], 'e': relative_pos[1], 'd': relative_pos[2], 'heading': heading})
        else: # Pathfinding process
            if self.do_pathfinding:
                # Paths points along the way to the target destination (?)
                pathed_positions = self.col_test.path_find(self.position, pos)
                for p_pos in pathed_positions:
                    self.move(self.position, p_pos)
                    time.sleep(.5)
            else: # Path obstructed (?)
                logger.debug(f'[({self.position})->({pos})] Path obstructed. Movment command canceled.')
    
    def takeoff(self, alt: float = 1.0, isMeters: bool = True) -> None:
        """ Depreciated
        -
        Tell the AVR to takeoff

        Args:
            alt (float): Height that the AVR will takeoff to in meters. Defaults to 1.0.
            isMeters (bool, optional): If the provided measurement is in meters. Defaults to True.
        """
        if isMeters:
            self.send_action('takeoff', {'alt': alt})
        else:
            self.send_action('takeoff', {'alt': round(self.inchesToMeters(alt), 1)})
    
    def land(self) -> None:
        """ Depreciated
        -
        Land the AVR
        """
        self.send_action('land')
    
    def setArmed(self, armed: bool) -> None:
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
    

    # =========================================
    # Mission and Waypoint commands

    def add_mission_waypoint(self, waypointType: str, coords: tuple[float, float, float], yaw_angle: float = float("nan"), goto_hold_time: float = 0, acceptanceRad: float = .10) -> None:
        """Add a waypoint to the mission_waypoints list.
        NOTE: At this time I am assuming that coordinates are relative to current position

        Args:
            waypointType (str): Must be one of `goto`, `takeoff`, or `land`
            coords (tuple[float, float, float]): Waypoint destination coordinates, in meters, as (fwd, right, up)
            yaw_angle (float, optional): Heading that the drone will turn to. Defaults to float("nan"), which will maintain the current heading mode (most likely straight forward)
            goto_hold_time (float, optional): How long the drone will hold its position at a waypoint, in seconds. Only matters for `goto` waypoints. Defaults to 0
            goto_acceptance_radius (float, optional): Acceptance radius in meters (if the sphere with this radius is hit, the waypoint counts as reached). Only matters for `goto` waypoints. Defaults to .10 (roughly 4 inches)
        """
        if waypointType not in ['goto', 'takeoff', 'land']:
            # If we dont recognize the type of the waypoint throw an error and skip the waypoint
            logger.error(f"Unrecognized waypointType: {waypointType} || Waypoint has not been added to mission")
            return
        # Add the waypoint to the list of waypoints
        self.mission_waypoints.append({'type': waypointType, 'n': coords[0], 'e': coords[1], 'd': coords[2] * -1, 'yaw': yaw_angle, 'holdTime': goto_hold_time, 'acceptRadius': acceptanceRad})
    
    def clear_mission_waypoints(self) -> None:
        """Clear the mission_waypoints list
        """
        self.mission_waypoints = []

    def upload_and_engage_mission(self, delay: float = -1) -> None:
        """Upload a mission to the flight controller, mission waypoints are represented in the mission_waypoints list. See the FCM readme and the fcc_control.py file for more details

        Args:
            delay (float, optional): Delay in seconds between uploading the mission and starting the mission. If not specified, the mission will start as soon as the upload completes.
        """
        self.send_action('upload_mission', {'waypoints': self.mission_waypoints})
        self.clear_mission_waypoints()
        # If delay is left blank the mission should start as soon as the mission upload completes
        if delay == -1:
            while self.states['flightEvent'] != 'request_upload_mission_completed_event':
                pass
            time.sleep(.1)
        else:
            time.sleep(delay)
        self.start_mission()
    
    def start_mission(self) -> None:
        """Arms the drone & starts the uploaded mission
        """
        self.setArmed(True)
        time.sleep(.1)
        self.send_action('start_mission')

    def wait_until_mission_complete(self):
        # wait until the current mission has been completed
        # TODO: Identify the signal that's transmitted upon completing a mission (Theory: It's the hold mode)
        pass


    # ================================
    # Send Message Commands

    def set_geofence(self, min_lat: int, min_lon: int, max_lat: int, max_lon: int):
        self.send_action('set_geofence', {'min_lat': min_lat, 'min_lon': min_lon, 'max_lat': max_lat, 'max_lon': max_lon})

    def move_servo(self, id, angle) -> None:
        self.send_message("avr/pcm/set_servo_abs",AvrPcmSetServoAbsPayload(servo=id, absolute=angle))

    def send_action(self, action: str, payload: dict = {}):
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

    def sound_laptop(self, fileName: str, ext: str = ".WAV", loops: int = 1):
        """Play a specified audio file from the <GUI/assets/sounds> directory on all connected laptops

        Args:
            fileName (str): The name of the file.
            ext (str): The extension of the file. Defaults to ".WAV"
            loops (int, optional): Number of loops. Currently has no effect. Defaults to 1.
        """
        # Plays the sound by publishing the sound topic with the file info as payload, which is processed & handled in autonomy.py
        self.send_message('avr/autonomous/sound', {'fileName': fileName, 'ext': ext, 'loops': loops})
    
    def setAutonomous(self, isEnabled: bool) -> None:
        """Broadcast given boolean for topic `avr/autonomous/enable`, in the `enabled` payload. This will update values on both the sandbox and the GUI.
        """
        self.send_message('avr/autonomous/enable', AvrAutonomousEnablePayload(enabled=isEnabled))
    
    def setRecon(self, isEnabled: bool) -> None:
        """Broadcast given boolean for topic `avr/autonomous/recon`, in the `enabled` payload. This will update values on both the sandbox and the GUI.
        """
        self.send_message('avr/autonomous/recon', {'enabled': isEnabled})
    
    def setBuildingDrop(self, building_id: int, isEnabled: bool) -> None:
        """Broadcast given int and boolean for topic `avr/autonomous/building/drop`, in the `id` and `enabled` payloads, respectively. This will update values on both the sandbox and the GUI.
        """
        self.send_message('avr/autonomous/building/drop', AvrAutonomousBuildingDropPayload(id=building_id, enabled=isEnabled))

    
    # ================================
    # Misc/Helper commands
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
            except: # Catch the IndexError that is thrown if we haven't yet scanned an apriltag (i.e. the list is empty)
                pass
            time.sleep(.025) # Given the low FPS of the CSI camera (which scans for apriltags), this sleep command won't lead to skipping over a detected apriltag
        logger.debug(f'Timeout reached while waiting to detect Apriltag {id}')
        return False

    def wait_for_state(self, stateKey: str, desiredVal: str, timeout: float = 5) -> bool:
        """Wait until a desired value is present for a specific key in the states dict

        Args:
            stateKey (str): The key of the value in the self.states dict that we're waiting for
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
    

if __name__ == '__main__':
    box = Sandbox()
    
    # Create Threads
    targeting_thread = Thread(target=box.targeting, daemon=True)
    if box.thermalAutoAim: targeting_thread.start()
    
    CIC_thread = Thread(target=box.CIC, daemon=True)
    CIC_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous, daemon=True)
    autonomous_thread.start()
    
    box.set_threads({'thermal': targeting_thread, 'cic': CIC_thread, 'auto': autonomous_thread})
    
    box.run()
