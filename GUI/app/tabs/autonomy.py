from __future__ import annotations

import functools  # Use functools.partial to assign different button press actions to buttons inside for-loops
import json
from ctypes import POINTER, cast
from typing import Dict, List

import playsound
from bell.avr.mqtt.payloads import AvrPcmSetLaserOffPayload, AvrPcmSetLaserOnPayload
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from PySide6 import QtCore, QtGui, QtWidgets

from ..lib.color import wrap_text
from ..lib.config import config
from ..lib.widgets import FloatLineEdit, StatusLabel
from .base import BaseTabWidget


class AutonomyWidget(BaseTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Autonomy")
        # default variables (mutable)
        self.thermal_state: int = 0
        self.auton_enabled: bool = False
        self.auton_mission: int = 0

        # default values (immutable)
        self.HOTSPOT_LED_FLASH_DEFAULT: bool = True

        self.topic_status_map: Dict[str, StatusLabel] = {}
        self.topic_timers: Dict[str, QtCore.QTimer] = {}

    def build(self) -> None:
        """
        Build the GUI layout
        """
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        # region Autonomous state
        sandbox_groupbox = QtWidgets.QGroupBox("Sandbox")
        sandbox_layout = QtWidgets.QVBoxLayout()
        sandbox_groupbox.setLayout(sandbox_layout)
        sandbox_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(sandbox_groupbox, 0, 0, 1, 5)

        # Autonomous control layout
        autonomous_layout = QtWidgets.QHBoxLayout()
        sandbox_layout.addLayout(autonomous_layout)

        autonomous_enable_button = QtWidgets.QPushButton("Enable Auton [E]")
        autonomous_enable_button.clicked.connect(lambda: self.set_autonomous_state(state=True))
        autonomous_enable_button.setShortcut(QtGui.QKeySequence("E"))
        autonomous_layout.addWidget(autonomous_enable_button)

        autonomous_disable_button = QtWidgets.QPushButton("Disable Auton [D]")
        autonomous_disable_button.clicked.connect(lambda: self.set_autonomous_state(state=False))
        autonomous_disable_button.setShortcut(QtGui.QKeySequence("D"))
        autonomous_layout.addWidget(autonomous_disable_button)

        self.autonomous_label = QtWidgets.QLabel(wrap_text("Autonomous Disabled", "red"))
        self.autonomous_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.autonomous_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        autonomous_layout.addWidget(self.autonomous_label)

        # Sandbox thread status
        module_status_layout = QtWidgets.QHBoxLayout()
        sandbox_layout.addLayout(module_status_layout)

        self.topic_status_map: Dict[str, StatusLabel] = {}  # data structure to hold the topic prefixes and the corresponding widget
        self.topic_timers: Dict[str, QtCore.QTimer] = {}

        auto_status = StatusLabel("Autonomous Thread")
        self.topic_status_map["Autonomous"] = auto_status
        self.create_status_timer("Autonomous")
        module_status_layout.addWidget(auto_status)

        cic_status = StatusLabel("Command, Information, & Control Thread")
        self.topic_status_map["CIC"] = cic_status
        self.create_status_timer("CIC")
        module_status_layout.addWidget(cic_status)

        thermal_status = StatusLabel("Thermal Thread")
        self.topic_status_map["Thermal"] = thermal_status
        self.create_status_timer("Thermal")
        module_status_layout.addWidget(thermal_status)
        # endregion

        # region Thermal & Laser
        thermal_laser_groupbox = QtWidgets.QGroupBox("Thermal and Laser Operations")
        thermal_laser_layout = QtWidgets.QVBoxLayout()
        thermal_laser_groupbox.setLayout(thermal_laser_layout)
        thermal_laser_groupbox.setMaximumWidth(350)
        layout.addWidget(thermal_laser_groupbox, 1, 0, 1, 1)

        # thermal control buttons
        thermal_buttons_layout = QtWidgets.QHBoxLayout()
        thermal_laser_layout.addLayout(thermal_buttons_layout)

        thermal_tracking_button = QtWidgets.QPushButton("Start Tracking [U]")
        thermal_tracking_button.clicked.connect(lambda: self.set_thermal_config(2))
        thermal_tracking_button.setShortcut(QtGui.QKeySequence("U"))
        thermal_buttons_layout.addWidget(thermal_tracking_button)

        thermal_scanning_button = QtWidgets.QPushButton("Start Scanning [H]")
        thermal_scanning_button.clicked.connect(lambda: self.set_thermal_config(1))
        thermal_scanning_button.setShortcut(QtGui.QKeySequence("H"))
        thermal_buttons_layout.addWidget(thermal_scanning_button)

        thermal_stop_button = QtWidgets.QPushButton("Stop All [B]")
        thermal_stop_button.clicked.connect(lambda: self.set_thermal_config(0))
        thermal_stop_button.setShortcut(QtGui.QKeySequence("B"))
        thermal_buttons_layout.addWidget(thermal_stop_button)

        # Hotspot LED Flash toggle button
        self.hotspot_flash_togglebtn = QtWidgets.QPushButton("Flash LEDs on hotspot detection")
        self.hotspot_flash_togglebtn.setCheckable(True)
        self.hotspot_flash_togglebtn.setChecked(self.HOTSPOT_LED_FLASH_DEFAULT)
        self.hotspot_flash_togglebtn.clicked.connect(lambda: self.set_thermal_config())
        self.hotspot_flash_togglebtn.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        thermal_laser_layout.addWidget(self.hotspot_flash_togglebtn)

        # Thermal logging toggle button (thermal data from the sandbox will overwhelm the terminal, FYI)
        self.thermal_log_togglebtn = QtWidgets.QPushButton("Log Thermal Data from Sandbox")
        self.thermal_log_togglebtn.setCheckable(True)
        self.thermal_log_togglebtn.clicked.connect(lambda: self.set_thermal_config())
        self.thermal_log_togglebtn.setStyle(QtWidgets.QStyleFactory.create("Fusion"))
        thermal_laser_layout.addWidget(self.thermal_log_togglebtn)

        # temp range/step settings
        temp_range_layout = QtWidgets.QFormLayout()
        thermal_laser_layout.addLayout(temp_range_layout)

        self.temp_min_line_edit = FloatLineEdit()
        self.temp_min_line_edit.setText(str(config.temp_range[0]))
        self.temp_min_line_edit.editingFinished.connect(lambda: self.set_thermal_config())
        self.temp_min_line_edit.editingFinished.connect(lambda: self.setFocus())
        temp_range_layout.addRow(QtWidgets.QLabel("Min:"), self.temp_min_line_edit)

        self.temp_max_line_edit = FloatLineEdit()
        self.temp_max_line_edit.setText(str(config.temp_range[1]))
        self.temp_max_line_edit.editingFinished.connect(lambda: self.set_thermal_config())
        self.temp_max_line_edit.editingFinished.connect(lambda: self.setFocus())
        temp_range_layout.addRow(QtWidgets.QLabel("Max:"), self.temp_max_line_edit)

        self.temp_step_edit = FloatLineEdit()
        self.temp_step_edit.setText(str(config.temp_range[2]))
        self.temp_step_edit.editingFinished.connect(lambda: self.set_thermal_config())
        self.temp_step_edit.editingFinished.connect(lambda: self.setFocus())
        temp_range_layout.addRow(QtWidgets.QLabel("Step:"), self.temp_step_edit)

        # thermal status label
        self.thermal_label = QtWidgets.QLabel()
        self.thermal_label.setText(wrap_text("Thermal Tracking Disabled", "red"))
        self.thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        thermal_laser_layout.addWidget(self.thermal_label)

        # laser controls
        laser_layout = QtWidgets.QHBoxLayout()
        thermal_laser_layout.addLayout(laser_layout)

        laser_on_button = QtWidgets.QPushButton("Laser On")
        laser_on_button.clicked.connect(lambda: self.set_laser(True))
        laser_layout.addWidget(laser_on_button)

        laser_off_button = QtWidgets.QPushButton("Laser Off")
        laser_off_button.clicked.connect(lambda: self.set_laser(False))
        laser_layout.addWidget(laser_off_button)

        self.laser_toggle_label = QtWidgets.QLabel()
        self.laser_toggle_label.setText(wrap_text("Laser Off", "red"))
        self.laser_toggle_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        laser_layout.addWidget(self.laser_toggle_label)
        # endregion

        # region Magnet control
        """
        NOTE: Magnets and lasers are mutually exclusive, because they are attached to the same power terminal on the drone
        These commands don't know what device they are controlling, they just control the flow of power to the device
        """
        magnet_groupbox = QtWidgets.QGroupBox("Magnet Control")
        magnet_layout = QtWidgets.QVBoxLayout()
        magnet_groupbox.setLayout(magnet_layout)
        layout.addWidget(magnet_groupbox, 1, 1, 1, 1)

        magnet_on_btn = QtWidgets.QPushButton("Activate Magnet [M]")
        magnet_on_btn.clicked.connect(lambda: self.set_magnet(True))
        magnet_on_btn.setShortcut(QtGui.QKeySequence("M"))
        magnet_layout.addWidget(magnet_on_btn)

        magnet_off_btn = QtWidgets.QPushButton("Deactivate Magnet [K]")
        magnet_off_btn.clicked.connect(lambda: self.set_magnet(False))
        magnet_off_btn.setShortcut(QtGui.QKeySequence("K"))
        magnet_layout.addWidget(magnet_off_btn)

        self.magnet_label = QtWidgets.QLabel()
        self.magnet_label.setText(wrap_text("Magnet Disabled", "red"))
        self.magnet_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))
        self.magnet_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        magnet_layout.addWidget(self.magnet_label)
        # endregion

        # region FCM Telemetry
        telemetry_groupbox = QtWidgets.QGroupBox("FCM Telemetry")
        telemetry_layout = QtWidgets.QGridLayout()
        telemetry_groupbox.setLayout(telemetry_layout)
        layout.addWidget(telemetry_groupbox, 1, 2, 1, 1)

        # Armed status
        arm_name = QtWidgets.QLabel("Armed Status:")
        telemetry_layout.addWidget(arm_name, 0, 0, 1, 1)

        self.armed_label = QtWidgets.QLabel(wrap_text("Disarmed", "green"))
        telemetry_layout.addWidget(self.armed_label, 0, 1, 1, 1)

        # Flight mode
        flight_mode_name = QtWidgets.QLabel("Flight Mode:")
        telemetry_layout.addWidget(flight_mode_name, 1, 0, 1, 1)

        self.flight_mode_label = QtWidgets.QLabel("N/A")
        telemetry_layout.addWidget(self.flight_mode_label, 1, 1, 1, 1)

        # Battery status
        battery_status_name = QtWidgets.QLabel("Battery Status:")
        telemetry_layout.addWidget(battery_status_name, 2, 0, 1, 1)

        self.battery_label = QtWidgets.QLabel("N/A")
        telemetry_layout.addWidget(self.battery_label, 2, 1, 1, 1)
        # endregion

        # region Testing
        testing_groupbox = QtWidgets.QGroupBox("Test Commands")
        testing_layout = QtWidgets.QGridLayout()
        testing_groupbox.setLayout(testing_layout)
        layout.addWidget(testing_groupbox, 1, 4, 1, 1)

        self.testing_items: list[str] = [
            "kill",
            "arm",
            "disarm",
            "zero ned",
        ]  # List of tests

        # Arrange test commands in a grid
        for index, item in enumerate(self.testing_items):
            test_name = QtWidgets.QLabel(f"{item.title()} test")
            test_name.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
            testing_layout.addWidget(test_name, index, 0)

            test_exec_btn = QtWidgets.QPushButton("Execute Test")
            test_exec_btn.clicked.connect(functools.partial(self.run_test, item.lower()))
            testing_layout.addWidget(test_exec_btn, index, 1)
        # endregion

        # region Manual Control
        manual_groupbox = QtWidgets.QGroupBox("Manual Control")
        manual_layout = QtWidgets.QGridLayout()
        manual_groupbox.setLayout(manual_layout)
        layout.addWidget(manual_groupbox, 1, 3, 1, 1)

        up_button = QtWidgets.QPushButton("Up")
        up_button.clicked.connect(lambda: self.run_test("bump fwd"))
        up_button.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Up))
        manual_layout.addWidget(up_button, 0, 1)

        left_button = QtWidgets.QPushButton("Left")
        left_button.clicked.connect(lambda: self.run_test("bump left"))
        left_button.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left))
        manual_layout.addWidget(left_button, 1, 0)

        down_button = QtWidgets.QPushButton("Down")
        down_button.clicked.connect(lambda: self.run_test("bump down"))
        down_button.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Down))
        manual_layout.addWidget(down_button, 1, 1)

        right_button = QtWidgets.QPushButton("Right")
        right_button.clicked.connect(lambda: self.run_test("bump right"))
        right_button.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right))
        manual_layout.addWidget(right_button, 1, 2)
        # endregion

        # region Auton missions
        self.missions_groupbox = QtWidgets.QGroupBox("Missions - numbered left to right by horizontal position on field")
        missions_layout = QtWidgets.QGridLayout()
        self.missions_groupbox.setLayout(missions_layout)
        self.missions_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding))
        layout.addWidget(self.missions_groupbox, 2, 0, 1, 5)
        self.missions_groupbox.setEnabled(self.auton_enabled)

        missions: List[str] = [  # List of names for each mission
            "Land @ Start",
            "Land @ Loading Zone",
            "Land @ Train One",
            "Land @ Train Two",
            "Land @ Bridge One",
            "Land @ Bridge Two",
            "Land @ Bridge Three",
            "Land @ Bridge Four",
            "Land @ Container Yard One",
            "Land @ Container Yard Two",
            "Scan Transformers & Land @ Start",
            "Land @ (-1, 1.5)",
            "Land @ (0, 3)",
            "Thermal Check @ (0, 3) & Land @ Start",
        ]
        self.mission_states: List[QtWidgets.QLabel] = []

        # Make each line of mission buttons
        for i, mission in enumerate(missions):
            # If there are more than 10 missions, split them into 2 columns
            if i > (len(missions) - 1) / 2 and len(missions) > 10:
                col = 3
                row = i - (len(missions) / 2)
            else:
                col = 0
                row = i

            mission_name = QtWidgets.QLabel(mission)
            mission_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            missions_layout.addWidget(mission_name, row, col)

            mission_state = QtWidgets.QLabel("")
            mission_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            missions_layout.addWidget(mission_state, row, col + 1)
            self.mission_states.append(mission_state)

            mission_exec_btn = QtWidgets.QPushButton("Execute Mission Command")
            mission_exec_btn.clicked.connect(functools.partial(self.set_autonomous_mission, mission_id=i + 1))
            missions_layout.addWidget(mission_exec_btn, row, col + 2)
        # endregion

    def create_status_timer(self, key: str) -> None:
        timer = QtCore.QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda k=key: self.handle_status_timeout(k))
        self.topic_timers[key] = timer

    def handle_status_timeout(self, key: str) -> None:
        self.topic_status_map[key].set_health(False)

    # region Messengers
    """NOTE: The reason that label change operations (like when auton is enabled & goes from "Disabled" to "Enabled") are processed in
    the message handler and not the messaging functions is so we can confirm that the drone gets the command, since the Jetson runs the MQTT server."""

    def set_autonomous_state(self, state: bool) -> None:
        """Set autonomous mode on or off

        Args:
            state (bool): Whether or not autonomous mode is enabled.
        """
        self.auton_enabled = state
        self.send_message("avr/sandbox/autonomous", {"enabled": self.auton_enabled})

    def set_autonomous_mission(self, mission_id: int) -> None:
        """Set the autonomous mission id

        Args:
            mission_id (int): The ID of the autonomous mission.
        """
        self.auton_mission = mission_id
        self.send_message("avr/sandbox/autonomous", {"mission_id": self.auton_mission})

    def run_test(self, test_name: str) -> None:
        """Activate a test"""
        self.send_message("avr/sandbox/test", {"testName": test_name})

    def set_thermal_config(self, state: int | None = None) -> None:
        """Handles sending thermal scanning and targeting data

        Args:
            state (int | None, optional): State of thermal operations, 0 for off, 1 for scanning, 2 for targeting. If not specified, the state will not change.
        """
        if state is not None:
            self.thermal_state = state
        hotspot_flash = self.hotspot_flash_togglebtn.isChecked()
        therm_log = self.thermal_log_togglebtn.isChecked()
        lower = self.temp_min_line_edit.text_float()
        upper = self.temp_max_line_edit.text_float()
        step = self.temp_step_edit.text_float()

        config.temp_range = (lower, upper, step)

        self.send_message("avr/sandbox/thermal_config", {"state": self.thermal_state, "hotspot flash": hotspot_flash, "logging": therm_log, "range": (lower, upper, step)})

    def set_laser(self, state: bool) -> None:
        """Enable/disable laser firing"""
        if state:
            topic = "avr/pcm/set_laser_on"
            payload = AvrPcmSetLaserOnPayload()
        else:
            topic = "avr/pcm/set_laser_off"
            payload = AvrPcmSetLaserOffPayload()

        self.send_message(topic, payload)

    def set_magnet(self, enabled: bool) -> None:
        """Enable/disable magnet power

        MAGNETS AND LASERS ARE MUTUALLY EXCLUSIVE
        """
        self.send_message("avr/pcm/set_magnet", {"enabled": enabled})

    # endregion

    # region MQTT Handler
    def process_message(self, topic: str, payload: dict) -> None:
        """Processes incoming messages based on the specified topic and updates the UI accordingly.
        This function handles various topics related to autonomous operations, including enabling/disabling autonomy, updating missions, and handling thermal data.
        """
        payload = json.loads(payload)

        if topic == "avr/sandbox/autonomous":
            # Handle auton enable/disable
            self.auton_enabled = payload.get("enabled", self.auton_enabled)
            self.missions_groupbox.setEnabled(self.auton_enabled)
            if self.auton_enabled:
                text = "Autonomous Enabled"
                color = "green"
            else:
                text = "Autonomous Disabled"
                color = "red"
            self.autonomous_label.setText(wrap_text(text, color))
            # Handle mission execution
            mission_id = payload.get("mission_id", 0)
            if mission_id == 0:
                for state in self.mission_states:
                    state.setText("")
                return
            else:
                self.mission_states[mission_id - 1].setText(wrap_text("Executing mission command...", "red"))
        elif topic == "avr/sandbox/thermal_config":
            # Update the thermal state and thermal label
            self.thermal_state = payload.get("state", self.thermal_state)
            match self.thermal_state:
                case 2:
                    text = "Thermal Tracking Enabled"
                    color = "green"
                case 1:
                    text = "Thermal Scanning Enabled"
                    color = "blue"
                case 0:
                    text = "Thermal Operations Disabled"
                    color = "red"
                case _:
                    return

            self.thermal_label.setText(wrap_text(text, color))
        elif topic in {"avr/pcm/set_laser_on", "avr/pcm/set_laser_off"}:
            text = "Laser On" if topic == "avr/pcm/set_laser_on" else "Laser Off"
            color = "green" if topic == "avr/pcm/set_laser_on" else "red"

            self.laser_toggle_label.setText(wrap_text(text, color))
        elif topic == "avr/pcm/set_magnet":
            state = payload["enabled"]

            text = "Magnet Enabled" if state else "Magnet Disabled"
            color = "green" if state else "red"

            self.magnet_label.setText(wrap_text(text, color))
        elif topic == "avr/sandbox/status":
            for key in payload.keys():
                self.topic_status_map[key].set_health(payload[key])
                if payload[key]:
                    self.topic_timers[key].start(5000)  # Start/reset timer for 5 seconds
        elif topic == "avr/fcm/status":
            if payload["armed"]:
                color = "Red"
                text = "Armed & Dangerous"
            else:
                color = "Green"
                text = "Disarmed"
            self.armed_label.setText(wrap_text(text, color))
            self.flight_mode_label.setText(payload["mode"])
        elif topic == "avr/fcm/battery":
            # get percentage of battery remaining (state of charge)
            soc = payload["soc"]
            # prevent it from dropping below 0
            soc = max(soc, 0)
            # prevent it from going above 100
            soc = min(soc, 100)

            self.battery_label.setText(f"{int(soc)}%")

            if int(soc) < 25:
                self.send_message("avr/autonomous/sound", {"file_name": "low_battery", "ext": ".mp3"})
        elif topic == "avr/autonomous/sound":
            file_name: str = payload["file_name"]
            ext: str = payload["ext"]
            max_volume: bool = payload.get("max_vol", False)

            playsound.playsound(f"./GUI/assets/sounds/{file_name}{ext}", False)

            if max_volume:
                # Get the default audio device
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

                while True:  # Set the volume to maximum (1.0 represents 100%)
                    volume.SetMasterVolumeLevelScalar(1.0, None)

    # endregion
