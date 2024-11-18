import base64
import time
from threading import Thread

import cv2
import numpy as np
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from loguru import logger
from scipy import ndimage


class Sandbox(MQTTModule):
    # region Init
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            "avr/thermal/reading": self.handle_thermal,
            "avr/sandbox/thermal_config": self.handle_thermal_config,
            "avr/apriltags/visible": self.handle_apriltags,
            "avr/fusion/position/ned": self.handle_position,
            "avr/sandbox/autonomous": self.handle_autonomous,
            "avr/fcm/status": self.handle_status,
            "avr/fcm/events": self.handle_events,
            "avr/sandbox/test": self.handle_testing,
        }

        # Assorted booleans
        self.autonomous: bool = False  # For enabling/disabling autonomous actions via the GUI
        self.fcm_connected: bool = False  # Used to determine if the FCM is broadcasting messages

        # Position vars
        self.position: list = [0, 0, 0]  # Current position in centimeters, as (forward, right, up)

        # Auton vars
        self.mission_waypoints: list[dict] = []
        self.auton_mission_id: int = 0

        # Thermal tracking vars
        self.thermal_grid: list[list[int]] = [[0 for _ in range(8)] for _ in range(8)]
        self.target_range: tuple[float, float] = (25.0, 40.0)
        self.targeting_step: float = 1.0
        self.flash_leds_on_detection: bool = True
        self.log_thermal_data: bool = False
        self.thermal_state: int = 1  # Value determines the state of the thermal process. 0 for no thermal processing, 1 for thermal hotspot scanning but not targeting, 2 for hotspot targeting

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

        # LED color presets in "WRGB" format (white, red, green, blue)
        # AFAIK the "white" doesn't do anything, there is no difference between white of zero and white of 255
        self.normal_color: tuple[int, int, int, int] = (255, 0, 128, 128)  # Cyan
        self.flash_color: tuple[int, int, int, int] = (255, 255, 0, 0)  # Red
        self.hotspot_color: tuple[int, int, int, int] = (255, 255, 255, 255)  # White

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

    def handle_thermal_config(self, payload: dict) -> None:
        old_thermal_range: tuple[float, float, float] = (self.target_range[0], self.target_range[1], self.targeting_step)
        # get new thermal config values. If they aren't present, keep the old values
        self.thermal_state = payload.get("state", self.thermal_state)
        self.target_range = payload.get("range", old_thermal_range)[:2]
        self.targeting_step = payload.get("range", old_thermal_range)[2]
        self.flash_leds_on_detection = payload.get("hotspot flash", self.flash_leds_on_detection)
        self.log_thermal_data = payload.get("logging", self.log_thermal_data)
        if self.thermal_state == 2:
            # if activating thermal autoaim, center the gimbal
            turret_angles = [1450, 1450]
            self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=2, absolute=turret_angles[0]))
            self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=3, absolute=turret_angles[1]))
        logger.debug(f"State: {self.thermal_state}, Range: {self.target_range}, Step: {self.targeting_step}, Hotspot Flash: {self.flash_leds_on_detection}, Log Data: {self.log_thermal_data}")

    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None:  # This handler is only called when an apriltag is scanned and processed successfully
        self.cur_apriltag = payload["tags"][0]
        tag_id = payload["tags"][0]["id"]

        if tag_id not in self.apriltag_ids:
            # If we haven't detected this apriltag before, add it to a list of detected IDs and queue an LED flash (LED flashing is done in the CIC thread)
            self.apriltag_ids.append(tag_id)
            self.flash_queue.append(tag_id)
            logger.debug(f"New AT detected, ID: {tag_id}")

    def handle_position(self, payload: AvrFusionPositionNedPayload) -> None:
        # Handle the position data from the fusion module. We use this data because it's the most accurate
        self.position = [payload["n"], payload["e"], payload["d"] * -1]

    def handle_autonomous(self, payload: dict) -> None:
        self.autonomous = payload.get("enabled", self.autonomous)
        self.auton_mission_id = payload.get("mission_id", self.auton_mission_id)

    def handle_status(self, payload: AvrFcmStatusPayload) -> None:
        # Set the flight controller's mode and armed status
        self.isArmed = payload["armed"]
        mode = payload["mode"]
        if self.states["flightMode"] != mode:
            logger.debug(f"Flight Mode Update || Flight Mode: {mode}")
            self.states["flightMode"] = mode
        self.fcm_connected = True

    def handle_events(self, payload: AvrFcmEventsPayload):
        # Handle flight events
        eventName = payload["name"]

        newState = self.possibleEvents.get(eventName, "UNKNOWN")

        if newState not in [self.states["flightEvent"], "UNKNOWN"]:
            logger.debug(f"New Flight Event: {newState}")
            self.states["flightEvent"] = newState

    def handle_testing(self, payload: dict):
        name = payload["testName"]
        if name == "kill":
            self.send_action("kill", {})
        elif name == "arm":
            self.set_armed(True)
        elif name == "disarm":
            self.set_armed(False)
        elif name == "zero ned":
            self.send_message("avr/fcm/capture_home", {})

    # endregion

    # region Thermal Thread
    def Thermal(self) -> None:
        logger.debug("Thermal Thread: Online")
        turret_angles = [1450, 1450]
        last_therm_flash = time.time()
        while True:
            if self.thermal_state == 0:  # If you aren't scanning or targeting, then don't scan or target
                continue

            # Thermal scanning process
            img = np.array(self.thermal_grid)  # Convert thermal grid to numpy array
            lowerb = np.array(self.target_range[0], np.uint8)  # Lower bound for thermal threshold
            upperb = np.array(self.target_range[1], np.uint8)  # Upper bound for thermal threshold
            mask = cv2.inRange(img, lowerb, upperb)  # Create mask of pixels within thermal threshold
            if self.log_thermal_data:
                logger.debug(f"\nThermal Scanning Mask: {mask}")

            if np.all(mask == 0):  # If no pixels are within the thermal threshold, continue
                continue
            elif self.flash_leds_on_detection and time.time() > last_therm_flash + 1:
                # If we're flashing LEDs on hotspot detection and it's been one second since the last flash, flash the LEDs
                logger.debug("Thermal hotspot(s) detected, flashing LEDs")
                self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=self.hotspot_color, time=0.5))
                last_therm_flash = time.time()

            blobs = mask > 100  # Identify blobs in the mask
            labels, nlabels = ndimage.label(blobs)  # Label the blobs
            centers_of_mass = ndimage.center_of_mass(mask, labels, np.arange(nlabels) + 1)  # Find centers of mass
            blob_sizes = ndimage.sum(blobs, labels, np.arange(nlabels) + 1)  # Calculate size of each blob
            heat_center: Tuple[float, float] = tuple(float(coord) for coord in centers_of_mass[blob_sizes.argmax()][::-1])  # Find largest blob's center (x/y coords)
            if self.log_thermal_data:
                logger.debug(f"Heat Center: {heat_center}")

            if self.thermal_state < 2:  # If not in targeting state, continue
                continue
            self.set_laser(True)  # Turn on the laser if targeting

            # Adjust turret angles to target the heat center
            if heat_center[0] > 4:
                turret_angles[0] += self.targeting_step
            elif heat_center[0] < 4:
                turret_angles[0] -= self.targeting_step
            self.move_servo(2, turret_angles[0])

            if heat_center[1] < 4:
                turret_angles[1] += self.targeting_step
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
        last_at_flash: dict = {"time": 0, "iter": 0}  # Contains the data of the last LED flash, including the time that the flash happened and the number of flashes we've done for that ID
        while True:
            # Once the FCM is initialized, do some housekeeping
            if self.fcm_connected and not light_init:
                self.send_message("avr/pcm/set_base_color", AvrPcmSetBaseColorPayload(wrgb=self.normal_color))  # Turn on the lights
                self.set_magnet(False)  # Make sure the magnet is off
                self.set_geofence(200000000, 850000000, 400000000, 1050000000)  # Set the geofence from 20 N, 85 W to 40 N, 105 W
                light_init = True

            # Flashing the LEDs when a new apriltag ID is detected
            if self.flash_queue and time.time() > last_at_flash["time"] + 1:  # Make sure it's been at least one second since the last LED flash
                self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=self.flash_color, time=0.5))
                last_at_flash["time"] = time.time()
                logger.debug(f"Flashing LEDs for ID: {self.flash_queue[0]}")
                if last_at_flash["iter"] >= 2:
                    last_at_flash["iter"] = 0
                    del self.flash_queue[0]
                else:
                    last_at_flash["iter"] += 1

    # endregion

    # region Status Sub-Thread
    def status(self):
        """Shows the status of the threads."""
        logger.debug("Status Sub-Thread: Online")
        while True:
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
        logger.debug("Autonomous Thread: Online")
        LZ: dict[str, tuple[float, float, float]] = {
            "start": (0.0, 0.0, 0.0),
            "loading": (0.085, 10.822, 0.0),
            "train one": (0.105, 1.417, 0.0),
            "train two": (0.105, 4.516, 0.0),
            "bridge one": (1.496, 0.757, 1.314),
            "bridge two": (1.396, 1.976, 1.314),
            "bridge three": (1.396, 3.957, 1.314),
            "bridge four": (1.496, 5.176, 1.314),
            "yard one": (0.20, 6.40, 0.0),
            "yard two": (0.20, 9.40, 0.0),
        }  # coordinates of landing zones (LZ's, yes I am a nerd) in meters
        auton_init: bool = False
        while True:
            if not self.autonomous:
                continue

            # Auton initialization process
            if not auton_init:
                self.send_message("avr/fcm/capture_home", {})  # Capture home coordinates (zero NED position, like how you zero a scale)
                auton_init = True

            if self.auton_mission_id == 0:
                continue

            # Land @ Start
            if self.auton_mission_id == 1:
                self.add_mission_waypoint("goto", (LZ["start"][0], LZ["start"][1], 1))
                self.add_mission_waypoint("goto", (LZ["start"][0], LZ["start"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["start"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Land @ Loading Zone
            if self.auton_mission_id == 2:
                self.add_mission_waypoint("goto", (LZ["loading"][0], LZ["loading"][1], 1))
                self.add_mission_waypoint("goto", (LZ["loading"][0], LZ["loading"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["loading"], acceptanceRad=0.05)
                self.upload_and_engage_mission()

            # Land @ Train One
            if self.auton_mission_id == 3:
                self.add_mission_waypoint("goto", (LZ["train one"][0], LZ["train one"][1], 1))
                self.add_mission_waypoint("goto", (LZ["train one"][0], LZ["train one"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["train one"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Land @ Train Two
            if self.auton_mission_id == 4:
                self.add_mission_waypoint("goto", (LZ["train two"][0], LZ["train two"][1], 1))
                self.add_mission_waypoint("goto", (LZ["train two"][0], LZ["train two"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["train two"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Land @ Bridge One
            if self.auton_mission_id == 5:
                self.add_mission_waypoint("goto", (0, LZ["bridge one"][1], 2))
                self.add_mission_waypoint("goto", (LZ["bridge one"][0], LZ["bridge one"][1], 2), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["bridge one"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

                # make sure the drone can safely exit the bridge at the start of the next mission
                self.add_mission_waypoint("goto", (0, LZ["bridge one"][1], 2))

            # Land @ Bridge Two
            if self.auton_mission_id == 6:
                self.add_mission_waypoint("goto", (0, LZ["bridge two"][1], 2))
                self.add_mission_waypoint("goto", (LZ["bridge two"][0], LZ["bridge two"][1], 2), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["bridge two"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

                # make sure the drone can safely exit the bridge at the start of the next mission
                self.add_mission_waypoint("goto", (0, LZ["bridge two"][1], 2))

            # Land @ Bridge Three
            if self.auton_mission_id == 7:
                self.add_mission_waypoint("goto", (0, LZ["bridge three"][1], 2))
                self.add_mission_waypoint("goto", (LZ["bridge three"][0], LZ["bridge three"][1], 2), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["bridge three"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

                # make sure the drone can safely exit the bridge at the start of the next mission
                self.add_mission_waypoint("goto", (0, LZ["bridge three"][1], 2))

            # Land @ Bridge Four
            if self.auton_mission_id == 8:
                self.add_mission_waypoint("goto", (0, LZ["bridge four"][1], 2))
                self.add_mission_waypoint("goto", (LZ["bridge four"][0], LZ["bridge four"][1], 2), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["bridge four"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

                # make sure the drone can safely exit the bridge at the start of the next mission
                self.add_mission_waypoint("goto", (0, LZ["bridge four"][1], 2))

            # Land @ Container Yard One
            if self.auton_mission_id == 9:
                self.add_mission_waypoint("goto", (LZ["yard one"][0], LZ["yard one"][1], 1))
                self.add_mission_waypoint("goto", (LZ["yard one"][0], LZ["yard one"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["yard one"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Land @ Container Yard Two
            if self.auton_mission_id == 10:
                self.add_mission_waypoint("goto", (LZ["yard two"][0], LZ["yard two"][1], 1))
                self.add_mission_waypoint("goto", (LZ["yard two"][0], LZ["yard two"][1], 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", LZ["yard two"], acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Scan Transformers & Land @ Start
            if self.auton_mission_id == 11:
                self.add_mission_waypoint("goto", (0.0, 7.469, 3.5))  # start at the "baseline"
                self.add_mission_waypoint("goto", (2.524, 7.469, 3.5), goto_hold_time=1)  # transformer one
                self.add_mission_waypoint("goto", (2.524, 5.729, 3.5), goto_hold_time=1)  # transformer two
                self.add_mission_waypoint("goto", (2.524, 3.989, 3.5), goto_hold_time=1)  # transformer three
                self.add_mission_waypoint("goto", (2.524, 2.249, 3.5), goto_hold_time=1)  # transformer four
                self.add_mission_waypoint("goto", (2.524, 0.509, 3.5), goto_hold_time=1)  # transformer five
                self.add_mission_waypoint("goto", (LZ["start"][0], LZ["start"][1], 3.5))  # hover above start
                self.add_mission_waypoint("land", LZ["start"])  # land at start
                self.upload_and_engage_mission()
                self.set_mission_id()

                self.set_thermal_state(1)

            # Land @ (0, 6)
            if self.auton_mission_id == 12:
                self.add_mission_waypoint("goto", (0, 6, 1))
                self.add_mission_waypoint("goto", (0, 6, 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", (0, 6, 0), acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Land @ (0, 3)
            if self.auton_mission_id == 13:
                self.add_mission_waypoint("goto", (0, 3, 1))
                self.add_mission_waypoint("goto", (0, 3, 1), acceptanceRad=0.05)
                self.add_mission_waypoint("land", (0, 3, 0), acceptanceRad=0.05)
                self.upload_and_engage_mission()
                self.set_mission_id()

            # Thermal Check @ (0, 5) & Land @ Start
            if self.auton_mission_id == 14:
                self.add_mission_waypoint("goto", (0, 5, 1), goto_hold_time=3)
                self.add_mission_waypoint("goto", (LZ["start"][0], LZ["start"][1], 1))
                self.add_mission_waypoint("land", LZ["start"])
                self.upload_and_engage_mission()
                self.set_mission_id()

                self.set_thermal_state(1)

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
        if waypointType == "land" and coords[2] == 0.0:
            # PX4 doesn't like landing waypoints at 0.0, so we have to set the altitude to 0.1
            # Trust me, this doesn't effect landing at all, your drone will not drop from the sky, I've tested it
            coords = (coords[0], coords[1], 0.1)
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
            if not self.wait_for_state("flightEvent", "MISSION_UPLOAD_GOOD"):
                # If the mission upload fails flash LEDs orange, if the upload is never confirmed then flash LEDs yellow
                if self.states["flightEvent"] == "MISSION_UPLOAD_BAD":
                    self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=(255, 255, 128, 0), time=0.5))
                else:
                    self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=(255, 255, 255, 0), time=0.5))
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

    def move_servo(self, id, angle) -> None:
        self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=id, absolute=angle))

    def send_action(self, action: str, payload: dict = {}):
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

    def set_mission_id(self, mission_id: int = 0) -> None:
        """Set autonomous mode on or off and/or set auton mission id

        Args:
            mission_id (int, optional): The ID of the autonomous mission. Defaults to 0.
        """
        self.auton_mission_id = mission_id
        self.send_message("avr/sandbox/autonomous", {"enabled": self.autonomous, "mission_id": self.auton_mission_id})

    def set_thermal_state(self, state: int) -> None:
        """Set the state of thermal operations

        Args:
            state (int): State of thermal operations, 0 for off, 1 for scanning, 2 for targeting.
        """
        self.send_message("avr/sandbox/thermal_config", {"state": state})

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
