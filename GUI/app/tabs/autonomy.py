from __future__ import annotations

import functools, json, os, playsound # Use functools.partial to assign different button press actions to buttons inside for-loops
from typing import List, Dict

from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
from ctypes import cast, POINTER

from bell.avr.mqtt.payloads import *
from PySide6 import QtCore, QtWidgets

from ..lib.color import wrap_text
from ..lib.widgets import FloatLineEdit, StatusLabel
from ..lib.config import config
from .base import BaseTabWidget

from scipy.interpolate import interp1d


class AutonomyWidget(BaseTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Autonomy")
        self.thermal_state: int = 0

    def build(self) -> None:
        # sourcery skip: extract-duplicate-method, simplify-dictionary-update
        """
        Build the GUI layout
        """
        # print(os.getcwd())
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        # region Autonomous state
        sandbox_groupbox = QtWidgets.QGroupBox("Sandbox")
        sandbox_layout = QtWidgets.QVBoxLayout()
        sandbox_groupbox.setLayout(sandbox_layout)

        # Autonomous control layout
        autonomous_layout = QtWidgets.QHBoxLayout()

        autonomous_enable_button = QtWidgets.QPushButton("Enable Auton")
        autonomous_enable_button.clicked.connect(lambda: self.set_autonomous(True))  # type: ignore
        autonomous_layout.addWidget(autonomous_enable_button)

        autonomous_disable_button = QtWidgets.QPushButton("Disable Auton")
        autonomous_disable_button.clicked.connect(lambda: self.set_autonomous(False))  # type: ignore
        autonomous_layout.addWidget(autonomous_disable_button)

        self.autonomous_label = QtWidgets.QLabel(wrap_text("Autonomous Disabled", "red"))
        self.autonomous_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.autonomous_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        autonomous_layout.addWidget(self.autonomous_label)

        sandbox_layout.addLayout(autonomous_layout)

        # Sandbox threads status
        module_status_layout = QtWidgets.QHBoxLayout()

        # data structure to hold the topic prefixes and the corresponding widget
        self.topic_status_map: Dict[str, StatusLabel] = {}

        auto_status = StatusLabel("Autonomous Thread")
        self.topic_status_map["Autonomous"] = auto_status
        module_status_layout.addWidget(auto_status)

        cic_status = StatusLabel("Command, Information, & Control Thread")
        self.topic_status_map["CIC"] = cic_status
        module_status_layout.addWidget(cic_status)

        thermal_status = StatusLabel("Thermal Thread")
        self.topic_status_map["Thermal"] = thermal_status
        module_status_layout.addWidget(thermal_status)

        sandbox_layout.addLayout(module_status_layout)

        sandbox_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        layout.addWidget(sandbox_groupbox, 0, 0, 1, 1)

        custom_layout = QtWidgets.QHBoxLayout()
        
        # region Thermal & Laser
        thermal_laser_groupbox = QtWidgets.QGroupBox('Thermal and Laser Operations')
        thermal_laser_layout = QtWidgets.QVBoxLayout()
        thermal_laser_groupbox.setLayout(thermal_laser_layout)

        # thermal control buttons
        thermal_buttons_layout = QtWidgets.QHBoxLayout()

        thermal_tracking_button = QtWidgets.QPushButton('Start Tracking')
        thermal_tracking_button.clicked.connect(lambda: self.set_thermal_data(2))
        thermal_buttons_layout.addWidget(thermal_tracking_button)

        thermal_scanning_button = QtWidgets.QPushButton('Start Scanning')
        thermal_scanning_button.clicked.connect(lambda: self.set_thermal_data(1))
        thermal_buttons_layout.addWidget(thermal_scanning_button)
        
        thermal_stop_button = QtWidgets.QPushButton('Stop All')
        thermal_stop_button.clicked.connect(lambda: self.set_thermal_data(0))
        thermal_buttons_layout.addWidget(thermal_stop_button)

        thermal_laser_layout.addLayout(thermal_buttons_layout)
        
        # temp range/step settings
        temp_range_layout = QtWidgets.QFormLayout()

        self.temp_min_line_edit = FloatLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Min:"), self.temp_min_line_edit)
        self.temp_min_line_edit.setText(str(config.temp_range[0]))

        self.temp_max_line_edit = FloatLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Max:"), self.temp_max_line_edit)
        self.temp_max_line_edit.setText(str(config.temp_range[1]))
        
        self.temp_step_edit = FloatLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Step:"), self.temp_step_edit)
        self.temp_step_edit.setText(str(config.temp_range[2]))

        set_temp_range_button = QtWidgets.QPushButton("Update Thermal Params")
        set_temp_range_button.clicked.connect(lambda: self.set_thermal_data())
        temp_range_layout.addWidget(set_temp_range_button)
        
        thermal_laser_layout.addLayout(temp_range_layout)
        
        # thermal status label
        self.thermal_label = QtWidgets.QLabel()
        self.thermal_label.setText(wrap_text("Thermal Tracking Disabled", "red"))
        self.thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        thermal_laser_layout.addWidget(self.thermal_label)

        # laser controls
        laser_layout = QtWidgets.QHBoxLayout()

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

        thermal_laser_layout.addLayout(laser_layout)


        thermal_laser_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        custom_layout.addWidget(thermal_laser_groupbox)


        # region Magnet control
        """
        NOTE: Magnets and lasers are mutually exclusive, because they are attached to the same power terminal on the drone
        These commands don't know what device they are controlling, they just control the flow of power to the device
        """
        magnet_groupbox = QtWidgets.QGroupBox("Magnet Control")
        magnet_layout = QtWidgets.QVBoxLayout()
        magnet_groupbox.setLayout(magnet_layout)
        
        magnet_on_btn = QtWidgets.QPushButton("Activate Magnet")
        magnet_on_btn.clicked.connect(lambda: self.set_magnet(True))
        magnet_layout.addWidget(magnet_on_btn)

        magnet_off_btn = QtWidgets.QPushButton("Deactivate Magnet")
        magnet_off_btn.clicked.connect(lambda: self.set_magnet(False))
        magnet_layout.addWidget(magnet_off_btn)

        self.magnet_label = QtWidgets.QLabel()
        self.magnet_label.setText(wrap_text("Magnet Disabled", "red"))
        self.magnet_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        magnet_layout.addWidget(self.magnet_label)
        
        custom_layout.addWidget(magnet_groupbox)
        
        # region Testing
        testing_groupbox = QtWidgets.QGroupBox("Test Commands")
        testing_layout = QtWidgets.QVBoxLayout()
        testing_groupbox.setLayout(testing_layout)

        self.testing_items: list[str] = ['kill', 'arm', 'disarm', 'zero ned'] # List of tests. If you want to add a test just add the name to this list
        self.testing_states: dict[str, QtWidgets.QLabel] = {}

        # Create a name label, state label, and on/off buttons for each test
        for item in self.testing_items:
            test_layout = QtWidgets.QHBoxLayout()

            test_name = QtWidgets.QLabel(f"{item.title()} test")
            test_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            test_layout.addWidget(test_name)
            
            test_state = QtWidgets.QLabel() # Only show the state of the test if it's active
            test_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            test_layout.addWidget(test_state)
            self.testing_states.update({item: test_state}) # Add the state label to this dict so we can modify it
            
            test_exec_btn = QtWidgets.QPushButton("Execute Test")
            test_layout.addWidget(test_exec_btn)
            test_exec_btn.clicked.connect(functools.partial(self.set_test, item.lower(), True))

            # Deactivating the test partway through wouldn't do anything, so this button is useless
            # building_disable_button = QtWidgets.QPushButton("Deactivate Test")
            # test_layout.addWidget(building_disable_button)
            # building_disable_button.clicked.connect(functools.partial(self.set_test, item, False))

            testing_layout.addLayout(test_layout)

        custom_layout.addWidget(testing_groupbox)


        layout.addLayout(custom_layout, 1, 0, 1, 1) # Finalize second row

        # region Auton positions
        self.positions: List[str] = [ # List of names for each position
            "Position 1", "Position 2", "Position 3", "Position 4", "Position 5",
            "Position 6", "Position 7", "Position 8", "Position 9", "Position 10"
        ]
        self.position_states: List[QtWidgets.QLabel] = []

        positions_groupbox = QtWidgets.QGroupBox("Positions")
        positions_layout = QtWidgets.QVBoxLayout()
        positions_groupbox.setLayout(positions_layout)

            # ======================
            # Make each line of position buttons
        for i in range (len(self.positions)):
            position_layout = QtWidgets.QHBoxLayout()

            position_name = QtWidgets.QLabel(self.positions[i])
            position_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            position_layout.addWidget(position_name)
            
            position_state = QtWidgets.QLabel("")
            position_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            position_layout.addWidget(position_state)
            self.position_states.append(position_state)
            
            position_exec_btn = QtWidgets.QPushButton("Execute Position Command")
            position_layout.addWidget(position_exec_btn)
            position_exec_btn.clicked.connect(functools.partial(self.set_position, i+1))  # type: ignore
            
            positions_layout.addLayout(position_layout)
        layout.addWidget(positions_groupbox, 2, 0, 4, 1)


    # region Messengers
    """
    NOTE: The reason that label change operations (like when auton is enabled & goes from "Disabled" to "Enabled") are processed in
    the message handler and not the messaging functions is so we can confirm that the drone gets the command, since the Jetson runs the MQTT server.
    """
    # ================
    # Auton messengers
    def set_position(self, number: int) -> None:
        # sourcery skip: assign-if-exp
        """
        Set the current target position for auton control
        """
        self.send_message("avr/autonomous/position", {"position": number})

    def set_autonomous(self, state: bool) -> None:
        """
        Set autonomous mode
        """
        self.send_message("avr/autonomous/enable", AvrAutonomousEnablePayload(enabled=state))
    
    def set_test(self, test_name: str, test_state: bool) -> None:
        self.send_message('avr/sandbox/test', {'testName': test_name, 'testState': test_state})

    # ==========================
    # Thermal scanning/targeting messenger
    def set_thermal_data(self, state: int | None = None) -> None:
        """Handles sending thermal scanning and targeting data

        Args:
            state (int | None, optional): State of thermal operations, 0 for off, 1 for scanning, 2 for targeting. If not specified, the state will not change.
        """
        if state is not None:
            self.thermal_state = state
        lower = self.temp_min_line_edit.text_float()
        upper = self.temp_max_line_edit.text_float()
        step = self.temp_step_edit.text_float()

        self.send_message('avr/autonomous/thermal_data', {'state': self.thermal_state, 'range': (lower, upper, step)})

    # ==============================
    # Laser messenger
    def set_laser(self, state: bool) -> None:
        if state:
            topic = "avr/pcm/set_laser_on"
            payload = AvrPcmSetLaserOnPayload()
        else:
            topic = "avr/pcm/set_laser_off"
            payload = AvrPcmSetLaserOffPayload()

        self.send_message(topic, payload)
    
    # =======================
    # Magnet messenger
    def set_magnet(self, enabled: bool) -> None:
        """Enable/disable magnet power

        MAGNETS AND LASERS ARE MUTUALLY EXCLUSIVE
        """
        self.send_message("avr/pcm/set_magnet", {"enabled": enabled})
    

    # region MQTT Handler
    def process_message(self, topic: str, payload: dict) -> None:
        # sourcery skip: low-code-quality
        # Yeah, you're telling me
        """
        Processes incoming messages based on the specified topic and updates the UI accordingly.
        This function handles various topics related to autonomous operations, including enabling/disabling autonomy, updating positions, managing test states, and handling thermal and object scanner data.
        """
        payload = json.loads(payload)
        if topic == "avr/autonomous/enable": # If the value of the auton bool is changing
            state = payload['enabled']
            if state:
                text = "Autonomous Enabled"
                color = "green"
            else:
                text = "Autonomous Disabled"
                color = "red"
            self.autonomous_label.setText(wrap_text(text, color))
        elif topic == "avr/autonomous/position":
            pos_num = payload['position']
            if pos_num == 0:
                for state in self.position_states:
                    state.setText("")
                return
            else:
                self.position_states[pos_num-1].setText(wrap_text("Executing position command...", "red"))
        elif topic == "avr/sandbox/test": # If we're activating or deactivating a test
            name = payload['testName']
            state = payload['testState']
            if state:
                self.testing_states[name].setText(wrap_text("Executing...", "red"))
            else:
                self.testing_states[name].setText("")
        elif topic == "avr/autonomous/thermal_data":
            match payload['state']:
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
            color == "green" if state else "red"

            self.magnet_label.setText(wrap_text(text, color))
        elif topic == "avr/sandbox/status":
            for key in payload.keys():
                self.topic_status_map[key].set_health(payload[key])
        elif topic == "avr/autonomous/sound":
            file_name = payload['fileName']
            ext = payload['ext']
            if 'max_vol' in payload.keys():
                max_volume: bool = payload['max_vol']

            playsound.playsound(f"./GUI/assets/sounds/{file_name}{ext}", False)

            if max_volume:
                # Get the default audio device
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))

                while True: # Set the volume to maximum (1.0 represents 100%)
                    volume.SetMasterVolumeLevelScalar(1.0, None)
