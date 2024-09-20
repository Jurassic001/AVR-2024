import base64
import time
from threading import Thread

import cv2
import numpy as np
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from loguru import logger
from scipy import ndimage
from scipy.interpolate import interp1d


class Sandbox(MQTTModule):
    # region Init
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            "avr/thermal/reading": self.handle_thermal,
            "avr/fcm/status": self.handle_status,
            "avr/autonomous/position": self.handle_auton_positions,
            "avr/autonomous/enable": self.handle_autonomous,
            "avr/autonomous/thermal_data": self.handle_thermal_data,
            "avr/apriltags/visible": self.handle_apriltags,
            "avr/fcm/location/local": self.handle_fcm_pos,
            "avr/fusion/position/ned": self.handle_fus_pos,
            "avr/fcm/attitude/euler": self.handle_attitude,
            "avr/sandbox/test": self.handle_testing,
            "avr/fcm/events": self.handle_events,
        }

        # Assorted booleans
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.autonomous: bool = False
        self.fcm_connected: bool = False

        # Position vars
        self.fcm_position: list = [0, 0, 0]
        self.fus_position: list = [0, 0, 0]
        self.attitude: dict[str, float] = {"pitch": 0.0, "roll": 0.0, "yaw": 0.0}

        # Auton vars
        self.mission_waypoints: list[dict] = []
        self.auton_position: int = 0

        # Thermal tracking vars
        self.thermal_grid: list[list[int]] = [[0 for _ in range(8)] for _ in range(8)]
        self.target_range: tuple[int, int] = (30, 40)
        self.targeting_step: int = 7
        self.thermal_state: int = 0  # Value determines the state of the thermal process. 0 for no thermal processing, 1 for thermal hotspot scanning but not targeting, 2 for hotspot targeting

        # Flight Controller vars
        self.states: dict[str, str] = {"flightEvent": "UNKNOWN", "flightMode": "UNKNOWN"}  # Dict of current events/modes that pertain to drone operation
        self.possibleEvents: dict[str, str] = {
            "landed_state_in_air_event": "IN_AIR",
            "landed_state_landing_event": "LANDING",
            "landed_state_on_ground_event": "ON_GROUND",
            "landed_state_taking_off_event": "TAKING_OFF",
            "go_to_started_event": "GOTO_START",
            "goto_complete_event": "GOTO_FINISH",
            "mission_upload_success_event": "MISSION_UPLOAD_GOOD",
            "mission_upload_failed_event": "MISSION_UPLOAD_BAD",
        }
        possibleModes: list[str] = [
            "UNKNOWN",
            "READY",
            "TAKEOFF",
            "HOLD",
            "MISSION",
            "RETURN_TO_LAUNCH",
            "LAND",
            "OFFBOARD",
            "FOLLOW_ME",
            "MANUAL",
            "ALTCTL",
            "POSCTL",
            "ACRO",
            "STABILIZED",
            "RATTITUDE",
        ]
        self.possibleStates: dict[str, list[str]] = {"flightEvent": self.possibleEvents.values(), "flightMode": possibleModes}
        self.isArmed: bool = False

        # Apriltag vars
        self.cur_apriltag: dict = (
            {}
        )  # Dict containing the most recently detected apriltag's info. I've added the Bell-provided documentation on the apriltag payload and its content to this pastebin: https://pastebin.com/Wc7mXs7W
        self.apriltag_ids: list = []  # List containing every apriltag ID that has been detected
        self.flash_queue: list = []  # List containing all the IDs that are queued for LED flashing
        self.normal_color: tuple[int, int, int, int] = [255, 78, 205, 196]  # wrgb (white, red, green, blue)
        self.flash_color: tuple[int, int, int, int] = [255, 255, 0, 0]  # wrgb
        self.hotspot_color: tuple[int, int, int, int] = [255, 0, 0, 0]  # wrgb

        self.threads: dict[str, Thread] = {}

    # endregion

    # region Topic Handlers
    def handle_thermal(self, payload: AvrThermalReadingPayload) -> None:
        # Handle the raw data from the thermal camera
        data = payload["data"]
        # decode the payload
        base64Decoded = data.encode("utf-8")
        asbytes = base64.b64decode(base64Decoded)
        pixel_ints = list(bytearray(asbytes))
        k = 0
        for i in range(len(self.thermal_grid)):
            for j in range(len(self.thermal_grid[0])):
                self.thermal_grid[j][i] = pixel_ints[k]
                k += 1

    def handle_status(self, payload: AvrFcmStatusPayload) -> None:
        # Set the flight controller's mode and armed status
        self.isArmed = payload["armed"]
        mode = payload["mode"]
        if self.states["flightMode"] != mode:
            logger.debug(f"Flight Mode Update || Flight Mode: {mode}")
            self.states["flightMode"] = mode
        self.fcm_connected = True

    def handle_auton_positions(self, payload: dict) -> None:
        self.auton_position = payload["position"]

    def handle_autonomous(self, payload: AvrAutonomousEnablePayload) -> None:
        self.autonomous = payload["enabled"]

    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None:  # This handler is only called when an apriltag is scanned and processed successfully
        self.cur_apriltag = payload["tags"][0]
        tag_id = payload["tags"][0]["id"]

        if tag_id not in self.apriltag_ids:
            # If we haven't detected this apriltag before, add it to a list of detected IDs and queue an LED flash (LED flashing is done in the CIC thread)
            self.apriltag_ids.append(tag_id)
            self.flash_queue.append(tag_id)
            logger.debug(f"New AT detected, ID: {tag_id}")

    def handle_thermal_data(self, payload: dict) -> None:
        self.thermal_state = payload["state"]
        if self.thermal_state == 2:
            turret_angles = [1450, 1450]
            self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=2, absolute=turret_angles[0]))
            self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=3, absolute=turret_angles[1]))
        self.target_range = payload["range"][:2]
        logger.debug(self.target_range)
        self.targeting_step = int(payload["range"][2])

    def handle_fcm_pos(self, payload: AvrFcmLocationLocalPayload) -> None:
        self.fcm_position = [payload["dX"], payload["dY"], payload["dZ"] * -1]

    def handle_fus_pos(self, payload: AvrFusionPositionNedPayload) -> None:
        self.fus_position = [payload["n"], payload["e"], payload["d"] * -1]

    def handle_attitude(self, payload: AvrFcmAttitudeEulerPayload) -> None:
        self.attitude["pitch"] = payload["pitch"]
        self.attitude["roll"] = payload["roll"]
        self.attitude["yaw"] = payload["yaw"]

    def handle_testing(self, payload: dict):
        name = payload["testName"]
        state = payload["testState"]
        if not state:  # If a test is being deactivated then we don't need to worry about it
            return
        elif name == "kill":
            self.send_action("kill", {})
        elif name == "arm":
            self.set_armed(True)
        elif name == "disarm":
            self.set_armed(False)
        elif name == "zero ned":
            self.send_message("avr/fcm/capture_home", {})

        # Once the test has been run, mark it as inactive
        self.send_message("avr/sandbox/test", {"testName": name, "testState": False})

    def handle_events(self, payload: AvrFcmEventsPayload):
        # Handle flight events
        eventName = payload["name"]

        newState = self.possibleEvents.get(eventName, "UNKNOWN")

        if newState not in [self.states["flightEvent"], "UNKNOWN"]:
            logger.debug(f"New Flight Event: {newState}")
            self.states["flightEvent"] = newState

    # endregion

    # region Thermal Thread
    def Thermal(self) -> None:
        logger.debug("Thermal Thread: Online")
        turret_angles = [1450, 1450]
        while True:

            if self.thermal_state == 0:  # If you aren't scanning or targeting, then don't scan or target
                continue

            # Thermal scanning process
            img = np.array(self.thermal_grid)  # Create mask of pixels above thermal threshold
            lowerb = np.array(self.target_range[0], np.uint8)
            upperb = np.array(self.target_range[1], np.uint8)
            mask = cv2.inRange(img, lowerb, upperb)
            logger.debug(f"\n{mask}")
            if np.all(np.array(mask) == 0):
                continue
            blobs = mask > 100
            labels, nlabels = ndimage.label(blobs)
            # find the center of mass of each label
            t = ndimage.center_of_mass(mask, labels, np.arange(nlabels) + 1)
            # calc sum of each label, this gives the number of pixels belonging to the blob
            s = ndimage.sum(blobs, labels, np.arange(nlabels) + 1)
            heat_center = [float(x) for x in t[s.argmax()][::-1]]
            move_range = [15, -15]
            m = interp1d([0, 8], move_range)
            logger.debug(heat_center)

            if self.thermal_state < 2:  # If you aren't targeting then don't target
                continue

            self.set_laser(True)  # If you are targeting, make sure the laser is on

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

    # endregion

    # region CIC Thread
    def CIC(self) -> None:
        logger.debug("Command, Information, & Control Thread: Online")
        status_thread = Thread(target=self.status)
        status_thread.daemon = True
        status_thread.start()
        light_init = False
        last_flash: dict = {"time": 0, "iter": 0}  # Contains the data of the last LED flash, including the time that the flash happened and the number of flashes we've done for that ID
        while True:
            if not self.CIC_loop:
                continue

            # Once the FCM is initialized, do some housekeeping
            if self.fcm_connected and not light_init:
                self.send_message("avr/pcm/set_base_color", AvrPcmSetBaseColorPayload(wrgb=self.normal_color))  # Turn on the lights
                """
                FROM LAST YEAR
                for i in range (5, 8): # Opening the sphero holders
                    self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload(servo= i, action= "open")
                    )
                """
                self.set_geofence(200000000, 850000000, 400000000, 1050000000)  # Set the geofence from 20 N, 85 W to 40 N, 105 W
                light_init = True

            # Flashing the LEDs when a new apriltag ID is detected
            if self.flash_queue and time.time() > last_flash["time"] + 1:  # Make sure it's been at least one second since the last LED flash
                self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=self.flash_color, time=0.5))
                last_flash["time"] = time.time()
                # logger.debug(f"Flashing LEDs for ID: {self.flash_queue[0]}")
                if last_flash["iter"] >= 2:
                    last_flash["iter"] = 0
                    del self.flash_queue[0]
                else:
                    last_flash["iter"] += 1

    # endregion

    # region Status Sub-Thread
    def status(self):
        """Shows the status of the threads."""
        logger.debug("Status Sub-Thread: Online")
        while True:
            if self.show_status:
                time.sleep(0.5)
                self.send_message(
                    "avr/sandbox/status",
                    {
                        "Autonomous": self.threads["auto"].is_alive(),
                        "CIC": self.threads["CIC"].is_alive(),
                        "Thermal": self.threads["thermal"].is_alive(),
                    },
                )

    # endregion

    # region Autonomous Thread
    def Autonomous(self):
        # sourcery skip: extract-duplicate-method, extract-method
        logger.debug("Autonomous Thread: Online")
        LZ = {"start": (0.0, 0.0, 0.0), "loading": (0.085, 10.822, 0.0), "train 1": (0.105, 4.516, 0)}  # coordinates of landing zones (LZ's, yes I am a nerd) in meters
        auton_init: bool = False
        while True:
            if not self.autonomous:
                continue

            # Auton initialization process
            if not auton_init:
                self.send_message("avr/fcm/capture_home", {})  # Capture home coordinates (zero NED position, like how you zero a scale)
                auton_init = True

            if self.auton_position == 0:
                continue

            # go to the starting point and land
            if self.auton_position == 1:
                self.add_mission_waypoint("goto", (0, 0, 1))
                self.add_mission_waypoint("land", LZ["start"])
                self.upload_and_engage_mission()
                self.set_position()

            # loiter forever, one meter above starting point
            if self.auton_position == 2:
                self.add_mission_waypoint("loiter", (0, 0, 1))
                self.upload_and_engage_mission()
                self.set_position()

            # three meter side strut
            if self.auton_position == 3:
                self.add_mission_waypoint("goto", (0, 0, 1), 90)
                self.add_mission_waypoint("goto", (1, 0, 1), 90)
                self.add_mission_waypoint("goto", (2, 0, 1), 90)
                self.add_mission_waypoint("goto", (3, 0, 1), 90)
                self.add_mission_waypoint("land", (3, 0, 0), 90)
                self.upload_and_engage_mission()
                self.set_position()

            # three meter side strut w/ box transport
            if self.auton_position == 4:
                self.set_magnet(True)  # start by picking up the box

                self.add_mission_waypoint("goto", (0, 0, 1), 90)
                self.add_mission_waypoint("goto", (1, 0, 1), 90)
                self.add_mission_waypoint("goto", (2, 0, 1), 90)
                self.add_mission_waypoint("goto", (3, 0, 1), 90)
                self.add_mission_waypoint("land", (3, 0, 0), 90)
                self.upload_and_engage_mission()

                # wait 5 sec, then start checking to see if we've landed. when we land, drop the magnet. If we haven't landed in 45 seconds, then stop checking.
                time.sleep(5)
                reached_waypoint = self.wait_for_state("flightEvent", "ON_GROUND", 45)
                self.set_magnet(not reached_waypoint)

            # test float("nan") as heading setting
            if self.auton_position == 5:
                self.add_mission_waypoint("goto", (1, 0, 1), float("nan"))
                self.add_mission_waypoint("goto", (1, 1, 1), float("nan"))
                self.add_mission_waypoint("goto", (2, 1, 1), float("nan"))
                self.add_mission_waypoint("goto", (3, 1, 1), float("nan"))
                self.add_mission_waypoint("goto", (1, 1, 1), float("nan"))
                self.add_mission_waypoint("goto", (0, 0, 1), float("nan"))
                self.add_mission_waypoint("goto", LZ["start"], 0)
                self.upload_and_engage_mission()
                self.set_position()

            # phase one auton v1 (intended to be as fast as possible)
            if self.auton_position == 6:
                self.add_mission_waypoint("goto", (0, 5, 1), acceptanceRad=0.5)
                self.add_mission_waypoint("land", LZ["loading"])
                self.upload_and_engage_mission()

                time.sleep(5)
                self.wait_for_state("flightEvent", "ON_GROUND", 25)  # engage the magnet as soon as we reach the landing zone
                self.set_magnet(True)

                self.add_mission_waypoint("goto", (0, 5, 1), acceptanceRad=0.5)
                self.add_mission_waypoint("land", LZ["train 1"])
                self.upload_and_engage_mission()

                time.sleep(5)
                reached_waypoint = self.wait_for_state("flightEvent", "ON_GROUND", 25)
                self.set_magnet(not reached_waypoint)  # If we reach the drop zone, deactivate the magnet

                self.set_position()

    # endregion

    # region Mission and Waypoint methods
    # PX4 mission mode docs: https://docs.px4.io/main/en/flight_modes_mc/mission.html
    def add_mission_waypoint(
        self, waypointType: Literal["goto", "land", "loiter"], coords: tuple[float, float, float], yaw_angle: float = 0, goto_hold_time: float = 0, acceptanceRad: float = 0.10
    ) -> None:
        """Add a waypoint to the mission_waypoints list.

        Args:
            waypointType (Literal["goto", "land", "loiter"]): Either `goto` a set of coordinates, `land` at a set of coordinates, or `loiter` indefinitely around a set of coordinates. If the drone is landed, it will takeoff first before preceeding towards the waypoint
            coords (tuple[float, float, float]): Absolute waypoint destination coordinates, in meters, as (fwd, right, up)
            yaw_angle (float, optional): Heading that the drone will be facing when it reaches the waypoint. Defaults to 0, which is straight forward from start
            goto_hold_time (float, goto ONLY): How long the drone will hold its position at a waypoint, in seconds. Only matters for `goto` waypoints. Defaults to 0
            goto_acceptance_radius (float, goto ONLY): Acceptance radius in meters (if the sphere with this radius is hit, the waypoint counts as reached). Only matters for `goto` waypoints. Defaults to .10 (roughly 4 inches)

        MAVLink mission syntax docs:
        https://mavlink.io/en/messages/common.html#MAV_CMD_NAV_WAYPOINT
        """
        # Add the waypoint to the list of waypoints
        self.mission_waypoints.append({"type": waypointType, "n": coords[0], "e": coords[1], "d": coords[2] * -1, "yaw": yaw_angle, "holdTime": goto_hold_time, "acceptRadius": acceptanceRad})

    def clear_mission_waypoints(self) -> None:
        """Clear the mission_waypoints list"""
        self.mission_waypoints = []

    def upload_and_engage_mission(self, delay: float = -1) -> None:
        """Upload a mission to the flight controller, mission waypoints are represented in the self.mission_waypoints list.

        Args:
            delay (float, optional): Delay in seconds between uploading the mission and starting the mission. Negative or no delay will cause the mission to start as soon as the upload completes.
        """
        self.send_action("upload_mission", {"waypoints": self.mission_waypoints})
        self.clear_mission_waypoints()
        # If delay is left blank the mission should start as soon as the mission upload completes
        if delay < 0:
            self.wait_for_state("flightEvent", "MISSION_UPLOAD_GOOD")
        else:
            time.sleep(delay)

        self.start_mission()

    def start_mission(self) -> None:
        """Arms the drone & starts the uploaded mission"""
        self.set_armed(True)
        time.sleep(0.1)
        self.send_action("start_mission")

    # endregion

    # region Messenger methods
    def set_geofence(self, min_lat: int, min_lon: int, max_lat: int, max_lon: int):
        self.send_action("set_geofence", {"min_lat": min_lat, "min_lon": min_lon, "max_lat": max_lat, "max_lon": max_lon})

    def set_armed(self, armed: bool) -> None:
        """Arm or disarm the FCC

        Args:
            armed (bool): True to arm the drone, False to disarm
        """
        if armed:
            self.send_action("arm")
        else:
            self.send_action("disarm")

        while self.isArmed != armed:  # Wait until the drone is in the requested state
            time.sleep(0.01)

    def move_servo(self, id, angle) -> None:
        self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=id, absolute=angle))

    def send_action(self, action: str, payload: dict = {}):
        # sourcery skip: default-mutable-arg
        """Send one of many possible action payloads to the `avr/fcm/actions` MQTT topic.

        Args:
            action (str): The action you want to send
            payload (dict, optional): The payload of the action you want to send. Defaults to {}.
        """
        self.send_message("avr/fcm/actions", {"action": action, "payload": payload})

    def set_laser(self, state: bool) -> None:
        if state:
            topic = "avr/pcm/set_laser_on"
            payload = AvrPcmSetLaserOnPayload()
        else:
            topic = "avr/pcm/set_laser_off"
            payload = AvrPcmSetLaserOffPayload()

        self.send_message(topic, payload)

    def set_magnet(self, enabled: bool) -> None:
        """Enable/disable magnet power. The magnet should be wired into the `high power load` terminal on the MOSFET, where the laser is typically wired (https://the-avr.github.io/AVR-2022/drone-peripheral-assembly/gimbal-assembly/#powering-laser-and-the-fpv)"""
        self.send_message("avr/pcm/set_magnet", {"enabled": enabled})

    def set_autonomous(self, isEnabled: bool) -> None:
        """Broadcast given boolean for topic `avr/autonomous/enable`, in the `enabled` payload. This will update values on both the sandbox and the GUI."""
        self.send_message("avr/autonomous/enable", AvrAutonomousEnablePayload(enabled=isEnabled))

    def set_position(self, number: int = 0) -> None:
        """Broadcast current auton position"""
        self.send_message("avr/autonomous/position", {"position": number})

    # endregion

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
                if self.cur_apriltag["id"] == id:
                    return True
            except IndexError:  # Catch the IndexError that is thrown if we haven't yet scanned an apriltag (i.e. the list is empty)
                pass
            time.sleep(0.025)  # Given the low FPS of the CSI camera (which scans for apriltags), this sleep command won't lead to skipping over a detected apriltag
        logger.debug(f"Timeout reached while waiting to detect Apriltag {id}")
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
            if desiredVal not in self.possibleStates[stateKey]:  # Check to make sure that we're waiting for a valid key that can contain the given value
                logger.error(f"The given key {stateKey} cannot contain the value {desiredVal}")
                return False
        except KeyError as e:  # If you get this error it means the key you're looking for doesn't exist
            logger.error(e)
            return False

        start_time = time.time()
        while start_time + timeout > time.time():
            if self.states[stateKey] == desiredVal:
                return True
            time.sleep(0.005)
        logger.debug(f"Timeout reached while waiting for {stateKey} value {desiredVal}")
        return False

    # From Quentin: Bell gives us field dimensions in inches then programs the drone to use meters because fuck you
    def inchesToMeters(self, inches: float) -> float:
        """Converts inches to meters

        Args:
            inches (float): Self explanatory, distance in inches

        Returns:
            float: Distance in meters
        """
        return inches / 39.37

    # endregion


# region Main process
if __name__ == "__main__":
    box = Sandbox()

    # Create Threads
    thermal_thread = Thread(target=box.Thermal, daemon=True)
    CIC_thread = Thread(target=box.CIC, daemon=True)
    autonomous_thread = Thread(target=box.Autonomous, daemon=True)

    # Create dict of threads (for status reporting)
    box.threads = {"thermal": thermal_thread, "CIC": CIC_thread, "auto": autonomous_thread}

    # Start threads and run sandbox
    thermal_thread.start()
    CIC_thread.start()
    autonomous_thread.start()

    box.run()
