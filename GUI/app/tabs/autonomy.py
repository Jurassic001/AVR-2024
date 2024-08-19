from __future__ import annotations

import functools, json, os
from typing import List

from bell.avr.mqtt.payloads import *
from PySide6 import QtCore, QtWidgets

from ..lib.color import wrap_text
from ..lib.widgets import DoubleLineEdit
from ..lib.config import config
from .base import BaseTabWidget

from scipy.interpolate import interp1d


class AutonomyWidget(BaseTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.spinner_speed_val = 1070
        self.setWindowTitle("Autonomy")
        self.spin_stop_val = 1472


    def build(self) -> None:
        """
        Build the GUI layout
        """
        print(os.getcwd())
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        # ==========================
        # Autonomous mode
        autonomous_groupbox = QtWidgets.QGroupBox("Autonomous")
        autonomous_layout = QtWidgets.QHBoxLayout()
        autonomous_groupbox.setLayout(autonomous_layout)

        autonomous_enable_button = QtWidgets.QPushButton("Enable")
        autonomous_enable_button.clicked.connect(lambda: self.set_autonomous(True))  # type: ignore
        autonomous_layout.addWidget(autonomous_enable_button)

        autonomous_disable_button = QtWidgets.QPushButton("Disable")
        autonomous_disable_button.clicked.connect(lambda: self.set_autonomous(False))  # type: ignore
        autonomous_layout.addWidget(autonomous_disable_button)

        self.autonomous_label = QtWidgets.QLabel(wrap_text("Autonomous Disabled", "red"))
        self.autonomous_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        autonomous_layout.addWidget(self.autonomous_label)

        layout.addWidget(autonomous_groupbox, 0, 0, 1, 1)
        
        # ==========================
        # Thermal autoaim, Spintake, Sphero controls, and Testing boxes

        custom_layout = QtWidgets.QHBoxLayout()
        
        # ==========================
        # Thermal Operations Box
        thermal_groupbox = QtWidgets.QGroupBox('Thermal Operations')
        thermal_layout = QtWidgets.QVBoxLayout()
        thermal_groupbox.setLayout(thermal_layout)
        thermal_groupbox.setMaximumWidth(300)
        
        thermal_tracking_button = QtWidgets.QPushButton('Start Tracking')
        thermal_tracking_button.clicked.connect(lambda: self.set_thermal_data(2))
        thermal_layout.addWidget(thermal_tracking_button)

        thermal_scanning_button = QtWidgets.QPushButton('Start Scanning')
        thermal_scanning_button.clicked.connect(lambda: self.set_thermal_data(1))
        thermal_layout.addWidget(thermal_scanning_button)
        
        thermal_stop_button = QtWidgets.QPushButton('Stop All')
        thermal_stop_button.clicked.connect(lambda: self.set_thermal_data(0))
        thermal_layout.addWidget(thermal_stop_button)
        
        temp_range_layout = QtWidgets.QFormLayout()

        self.temp_min_line_edit = DoubleLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Min:"), self.temp_min_line_edit)
        self.temp_min_line_edit.setText(str(config.temp_range[0]))

        self.temp_max_line_edit = DoubleLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Max:"), self.temp_max_line_edit)
        self.temp_max_line_edit.setText(str(config.temp_range[1]))
        
        self.temp_step_edit = DoubleLineEdit()
        temp_range_layout.addRow(QtWidgets.QLabel("Step:"), self.temp_step_edit)
        self.temp_step_edit.setText(str(config.temp_range[2]))

        set_temp_range_button = QtWidgets.QPushButton("Update Thermal Params")
        temp_range_layout.addWidget(set_temp_range_button)
        thermal_layout.addLayout(temp_range_layout)
        set_temp_range_button.clicked.connect(  # type: ignore
            lambda: self.set_thermal_data(
                lower=float(self.temp_min_line_edit.text()),
                upper=float(self.temp_max_line_edit.text()),
                step=float(self.temp_step_edit.text()),
            )
        )
        
        self.thermal_label = QtWidgets.QLabel()
        self.thermal_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        self.thermal_label.setText(wrap_text("Thermal Tracking Disabled", "red"))
        thermal_layout.addWidget(self.thermal_label)

        thermal_layout.addWidget(thermal_groupbox)
        
        custom_layout.addWidget(thermal_groupbox)
        
        # ==========================
        # Sphero Holder Box
        sphero_groupbox = QtWidgets.QGroupBox('Sphero Holder')
        sphero_layout = QtWidgets.QGridLayout()
        sphero_groupbox.setLayout(sphero_layout)
        
        sphero_groupbox1 = QtWidgets.QGroupBox('Holder 1')
        sphero_layout1 = QtWidgets.QVBoxLayout()
        sphero_groupbox1.setLayout(sphero_layout1)
        sphero_go_button1 = QtWidgets.QPushButton('Open')
        sphero_go_button1.clicked.connect(lambda: self.set_sphero_holder(1, 'open'))
        sphero_layout1.addWidget(sphero_go_button1)
        sphero_stop_button1 = QtWidgets.QPushButton('Close')
        sphero_stop_button1.clicked.connect(lambda: self.set_sphero_holder(1, 'close'))
        sphero_layout1.addWidget(sphero_stop_button1)
        sphero_layout.addWidget(sphero_groupbox1, 0, 0)

        sphero_groupbox1 = QtWidgets.QGroupBox('Holder 2')
        sphero_layout1 = QtWidgets.QVBoxLayout()
        sphero_groupbox1.setLayout(sphero_layout1)
        sphero_go_button1 = QtWidgets.QPushButton('Open')
        sphero_go_button1.clicked.connect(lambda: self.set_sphero_holder(2, 'open'))
        sphero_layout1.addWidget(sphero_go_button1)
        sphero_stop_button1 = QtWidgets.QPushButton('Close')
        sphero_stop_button1.clicked.connect(lambda: self.set_sphero_holder(2, 'close'))
        sphero_layout1.addWidget(sphero_stop_button1)
        sphero_layout.addWidget(sphero_groupbox1, 0, 1)
        
        sphero_groupbox1 = QtWidgets.QGroupBox('Holder 3')
        sphero_layout1 = QtWidgets.QVBoxLayout()
        sphero_groupbox1.setLayout(sphero_layout1)
        sphero_go_button1 = QtWidgets.QPushButton('Open')
        sphero_go_button1.clicked.connect(lambda: self.set_sphero_holder(3, 'open'))
        sphero_layout1.addWidget(sphero_go_button1)
        sphero_stop_button1 = QtWidgets.QPushButton('Close')
        sphero_stop_button1.clicked.connect(lambda: self.set_sphero_holder(3, 'close'))
        sphero_layout1.addWidget(sphero_stop_button1)
        sphero_layout.addWidget(sphero_groupbox1, 0, 2)

        sphero_all_groupbox = QtWidgets.QGroupBox('All')
        sphero_all_layout = QtWidgets.QGridLayout()
        sphero_all_groupbox.setLayout(sphero_all_layout)
        sphero_go_button1 = QtWidgets.QPushButton('Open')
        sphero_go_button1.clicked.connect(lambda: self.set_sphero_holder(0, 'open'))
        sphero_all_layout.addWidget(sphero_go_button1, 1, 1)
        sphero_stop_button1 = QtWidgets.QPushButton('Close')
        sphero_stop_button1.clicked.connect(lambda: self.set_sphero_holder(0, 'close'))
        sphero_all_layout.addWidget(sphero_stop_button1, 1, 2)
        sphero_layout.addWidget(sphero_all_groupbox, 1, 0, 1, 3)
        
        custom_layout.addWidget(sphero_groupbox)
        
        # ==================================
        # Testing box
        testing_groupbox = QtWidgets.QGroupBox("Test Commands")
        testing_layout = QtWidgets.QVBoxLayout()
        testing_groupbox.setLayout(testing_layout)

        self.testing_items: list[str] = ['Arm', 'Disarm', 'Zero NED'] # List of tests. If you want to add a test just add the name to this list
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
            test_exec_btn.clicked.connect(functools.partial(self.set_test, item, True))

            # Deactivating the test partway through wouldn't do anything, so this button is useless
            # building_disable_button = QtWidgets.QPushButton("Deactivate Test")
            # test_layout.addWidget(building_disable_button)
            # building_disable_button.clicked.connect(functools.partial(self.set_test, item, False))

            testing_layout.addLayout(test_layout)

        custom_layout.addWidget(testing_groupbox)


        layout.addLayout(custom_layout, 1, 0, 1, 1) # Finalize second row

        # ==========================
        # Auton positions
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


    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ MESSAGING FUNCTIONS //////////////////////////////
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
    def set_thermal_data(self, state: int = -1, lower: int = -1, upper: int = -1, step: int = -1) -> None:
        """Handles sending thermal scanning and targeting data

        Args:
            state (int, optional): State of thermal operations, 0 for off, 1 for scanning, 2 for targeting. A value of -1 (default) will make no change.
            lower (int, optional): Lowest temp to scan for. A value of -1 (default) will make no change.
            upper (int, optional): Highest temp to scan for. A value of -1 (default) will make no change.
            step (int, optional): Step of movement for the tracking gimbal to make. A value of -1 (default) will make no change.
        """
        if (lower, upper, step).count(-1) == 0:
            config.temp_range = (lower, upper, step)
            if state != -1:
                self.send_message('avr/autonomous/thermal_data', {'state': state, 'range': (lower, upper, step)})
            else:
                self.send_message('avr/autonomous/thermal_data', {'range': (lower, upper, step)})
        elif state != -1:
            self.send_message('avr/autonomous/thermal_data', {'state': state})
        
        match state:
            case 2:
                text = 'Thermal Tracking Enabled'
                color = 'green'
            case 1:
                text = 'Thermal Scanning Enabled'
                color = 'blue'
            case 0:
                text = 'Thermal Operations Disabled'
                color = 'red'
            case _:
                return
     
        self.thermal_label.setText(wrap_text(text, color))

    # ===================
    # Spintake messengers
    def set_spintake_spinner(self, state: bool) -> None:
        vals ={True: 200, False: 81} # Check 200, ask Row what val is max speed.
        if state:
            self.send_message(
                "avr/pcm/set_servo_abs",
                AvrPcmSetServoAbsPayload(servo= 0, absolute= self.spinner_speed_val)
            )
        else:
            self.send_message(
                "avr/pcm/set_servo_abs",
                AvrPcmSetServoAbsPayload(servo= 0, absolute= self.spin_stop_val)
            )
        
    def set_spintake_bottom(self, open_close: str) -> None:
        """ [Placeholder]"""
        self.send_message( #Open: 41
        "avr/pcm/set_servo_open_close",
        AvrPcmSetServoOpenClosePayload(servo= 1, action= open_close)
        )

    def set_spinner_speed(self, precent: float) -> None:
        print(precent)
        self.spinner_speed_val = int(precent)
    
    # =======================
    # Sphero holder messenger
    def set_sphero_holder(self, door: int, open_close: str) -> None:
        """ Open sphero gates. \n\n`door` = 0 opens/closes all.  """
        if door == 0:
            for i in range (5, 8):
                self.send_message(
                "avr/pcm/set_servo_open_close",
                AvrPcmSetServoOpenClosePayload(servo= i, action= open_close)
                )
        else:
            self.send_message(
                "avr/pcm/set_servo_open_close",
                AvrPcmSetServoOpenClosePayload(servo= 4+door, action= open_close)
            )

    # \\\\\\\\\\\\\\\ MQTT Message Handling ///////////////
    def process_message(self, topic: str, payload: dict) -> None:
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
        elif topic == 'avr/sandbox/test': # If we're activating or deactivating a test
            name = payload['testName']
            state = payload['testState']
            if state:
                self.testing_states[name].setText(wrap_text("Executing...", "red"))
            else:
                self.testing_states[name].setText("")