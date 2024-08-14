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
        # Recon, Thermal autoaim, Spintake, Sphero controls, and Testing boxes

        custom_layout = QtWidgets.QHBoxLayout()
        
        # ==========================
        # Recon Box
        recon_groupbox = QtWidgets.QGroupBox('Recon')
        recon_layout = QtWidgets.QVBoxLayout()
        recon_groupbox.setLayout(recon_layout)

        self.recon_label = QtWidgets.QLabel(wrap_text('Recon Disabled', 'red'))
        self.recon_label.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        recon_layout.addWidget(self.recon_label)

        custom_recon_go_button = QtWidgets.QPushButton('Enable')
        custom_recon_go_button.clicked.connect(lambda: self.set_recon(True))
        recon_layout.addWidget(custom_recon_go_button)
        
        custom_recon_stop_button = QtWidgets.QPushButton('Disable')
        custom_recon_stop_button.clicked.connect(lambda: self.set_recon(False))
        recon_layout.addWidget(custom_recon_stop_button)
        
        recon_groupbox.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Ignored))
        
        recon_layout.addWidget(recon_groupbox)
        custom_layout.addWidget(recon_groupbox)
        """
        # ==========================
        # Thermal Target Box
        thermal_groupbox = QtWidgets.QGroupBox('Thermal Tracking')
        thermal_layout = QtWidgets.QVBoxLayout()
        thermal_groupbox.setLayout(thermal_layout)
        thermal_groupbox.setMaximumWidth(300)
        
        thermal_go_button = QtWidgets.QPushButton('Start')
        thermal_go_button.clicked.connect(lambda: self.set_thermal_auto(True))
        thermal_layout.addWidget(thermal_go_button)
        
        thermal_stop_button = QtWidgets.QPushButton('Stop')
        thermal_stop_button.clicked.connect(lambda: self.set_thermal_auto(False))
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

        set_temp_range_button = QtWidgets.QPushButton("Set Temp Range")
        temp_range_layout.addWidget(set_temp_range_button)
        thermal_layout.addLayout(temp_range_layout)
        set_temp_range_button.clicked.connect(  # type: ignore
            lambda: self.set_targeting_range(
                float(self.temp_min_line_edit.text()),
                float(self.temp_max_line_edit.text()),
                float(self.temp_step_edit.text()),
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
        """
        # ==========================
        # Spintake Box
        spintake_groupbox = QtWidgets.QGroupBox('Spintake')
        spintake_layout = QtWidgets.QVBoxLayout()
        spintake_groupbox.setLayout(spintake_layout)
        spintake_groupbox.setMaximumWidth(300)

        # ==========================
        # Spintake Spinner Box
        spintake_spinner_groupbox = QtWidgets.QGroupBox('Spinner')
        spintake_spinner_layout = QtWidgets.QVBoxLayout()
        spintake_spinner_groupbox.setLayout(spintake_spinner_layout)
        
        spintake_spinner_go_button = QtWidgets.QPushButton('Start')
        spintake_spinner_go_button.clicked.connect(lambda: self.set_spintake_spinner(True))
        spintake_spinner_layout.addWidget(spintake_spinner_go_button)
        
        spintake_spinner_stop_button = QtWidgets.QPushButton('Stop')
        spintake_spinner_stop_button.clicked.connect(lambda: self.set_spintake_spinner(False))
        spintake_spinner_layout.addWidget(spintake_spinner_stop_button)
        
        speed_layout = QtWidgets.QFormLayout()
        
        speed_precent = DoubleLineEdit()
        speed_layout.addRow(QtWidgets.QLabel("Speed:"), speed_precent)
        speed_precent.setText('100')
        inter = interp1d((100, 0), (1070, self.spin_stop_val))
        
        speed_button = QtWidgets.QPushButton("Set Speed")
        speed_layout.addWidget(speed_button)
        spintake_spinner_layout.addLayout(speed_layout)
        speed_button.clicked.connect(  # type: ignore
            lambda: self.set_spinner_speed(
                inter(float(speed_precent.text()))
            )
        )
        
        self.spintake_spinner_label = QtWidgets.QLabel()
        self.spintake_spinner_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        spintake_spinner_layout.addWidget(spintake_spinner_groupbox)
        spintake_layout.addWidget(spintake_spinner_groupbox)

        # ==========================
        # Spintake Bottom Box
        spintake_bottom_groupbox = QtWidgets.QGroupBox('Bottom')
        spintake_bottom_layout = QtWidgets.QVBoxLayout()
        spintake_bottom_groupbox.setLayout(spintake_bottom_layout)
        
        spintake_bottom_go_button = QtWidgets.QPushButton('Open')
        spintake_bottom_go_button.clicked.connect(lambda: self.set_spintake_bottom('open'))
        spintake_bottom_layout.addWidget(spintake_bottom_go_button)
        
        spintake_bottom_stop_button = QtWidgets.QPushButton('Close')
        spintake_bottom_stop_button.clicked.connect(lambda: self.set_spintake_bottom('close'))
        spintake_bottom_layout.addWidget(spintake_bottom_stop_button)
        
        self.spintake_bottom_label = QtWidgets.QLabel()
        self.spintake_bottom_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignBottom | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        spintake_layout.addWidget(spintake_bottom_groupbox)

        custom_layout.addWidget(spintake_groupbox)

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
        testing_groupbox = QtWidgets.QGroupBox("Testing")
        testing_layout = QtWidgets.QVBoxLayout()
        testing_groupbox.setLayout(testing_layout)

        self.testing_items: list[str] = ['sound', 'arm', 'disarm', 'Zero NED'] # List of tests. If you want to add a test just add the name to this list
        self.testing_states: dict[str, QtWidgets.QLabel] = {}

        # Create a name label, state label, and on/off buttons for each test
        for str in self.testing_items:
            test_layout = QtWidgets.QHBoxLayout()

            test_name = QtWidgets.QLabel(f"{str.title()} test")
            test_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            test_layout.addWidget(test_name)
            
            building_state = QtWidgets.QLabel() # Only show the state of the test if it's active
            building_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            test_layout.addWidget(building_state)
            self.testing_states.update({str: building_state}) # Add the state label to this dict so we can modify it
            
            building_enable_button = QtWidgets.QPushButton("Execute Test")
            test_layout.addWidget(building_enable_button)
            building_enable_button.clicked.connect(functools.partial(self.set_test, str, True))

            # Deactivating the test partway through wouldn't do anything, so this button is useless
            # building_disable_button = QtWidgets.QPushButton("Deactivate Test")
            # test_layout.addWidget(building_disable_button)
            # building_disable_button.clicked.connect(functools.partial(self.set_test, str, False))

            testing_layout.addLayout(test_layout)

        custom_layout.addWidget(testing_groupbox)


        layout.addLayout(custom_layout, 1, 0, 1, 1) # Finalize second row

        # ==========================
        # Buildings
        self.number_of_buildings = 6
        self.building_states: List[QtWidgets.QLabel] = []

        buildings_groupbox = QtWidgets.QGroupBox("Buildings")
        buildings_layout = QtWidgets.QVBoxLayout()
        buildings_groupbox.setLayout(buildings_layout)

        building_all_layout = QtWidgets.QHBoxLayout()

        building_all_enable_button = QtWidgets.QPushButton("Enable All Drops")
        building_all_enable_button.clicked.connect(lambda: self.set_building_all(True))  # type: ignore
        building_all_layout.addWidget(building_all_enable_button)

        building_all_disable_button = QtWidgets.QPushButton("Disable All Drops")
        building_all_disable_button.clicked.connect(lambda: self.set_building_all(False))  # type: ignore
        building_all_layout.addWidget(building_all_disable_button)

        buildings_layout.addLayout(building_all_layout)

            # ======================
            # Make each line of building buttons
        for i in range(self.number_of_buildings):
            building_layout = QtWidgets.QHBoxLayout()

            building_name = QtWidgets.QLabel(f"Building {i+1}")
            building_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            building_layout.addWidget(building_name)
            
            building_state = QtWidgets.QLabel(wrap_text("Drop Disabled", "red"))
            building_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            building_layout.addWidget(building_state)
            self.building_states.append(building_state)
            
            building_enable_button = QtWidgets.QPushButton("Enable Drop")
            building_layout.addWidget(building_enable_button)
            building_enable_button.clicked.connect(functools.partial(self.set_building, i, True))  # type: ignore

            building_disable_button = QtWidgets.QPushButton("Disable Drop")
            building_layout.addWidget(building_disable_button)
            building_disable_button.clicked.connect(functools.partial(self.set_building, i, False))  # type: ignore
            
            buildings_layout.addLayout(building_layout)
        layout.addWidget(buildings_groupbox, 2, 0, 4, 1)


    # \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\ MESSAGING FUNCTIONS //////////////////////////////
    """
    NOTE: The reason that label change operations (like when auton is enabled & goes from "Disabled" to "Enabled") are processed in
    the message handler and not the messaging functions is so we can confirm that the drone gets the command, since the Jetson runs the MQTT server.
    """
    # ================
    # Auton messengers
    def set_building(self, number: int, state: bool) -> None:
        # sourcery skip: assign-if-exp
        """
        Set a building state
        """
        self.send_message("avr/autonomous/building/drop", AvrAutonomousBuildingDropPayload(id=number, enabled=state))

    def set_building_all(self, state: bool) -> None:
        """
        Set all building states at once
        """
        for i in range(self.number_of_buildings):
            self.set_building(i, state)

    def set_autonomous(self, state: bool) -> None:
        """
        Set autonomous mode
        """
        self.send_message("avr/autonomous/enable", AvrAutonomousEnablePayload(enabled=state))

    def set_recon(self, state: bool) -> None:
        """ Starts AVR Recon. """
        self.send_message('avr/autonomous/recon', {'enabled': state})
    
    def set_test(self, test_name: str, test_state: bool) -> None:
        self.send_message('avr/sandbox/test', {'testName': test_name, 'testState': test_state})

    # ==========================
    # Thermal autoaim messengers
    def set_thermal_auto(self, state: bool) -> None:
        """ Starts autonomous thermal targeting. """
        self.send_message(
            'avr/autonomous/thermal_targeting', {'enabled': state}
        )
        
        if state:
            text = 'Thermal Tracking Enabled'
            color = 'green'
        else:
            text = 'Thermal Tracking Disabled'
            color = 'red'
            
        self.thermal_label.setText(wrap_text(text, color))

    def set_targeting_range(self, lower: int, upper: int, step: int) -> None:
        config.temp_range = (lower, upper, step)
        self.send_message(
            'avr/autonomous/thermal_range',
            {'range': (lower, upper, step)}
        )

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
        if topic == "avr/autonomous/recon": # If the value of the recon bool is changing
            state = payload['enabled']
            if state:
                text = 'Recon Enabled'
                color = 'green'
            else:
                text = 'Recon Disabled'
                color = 'red'
            self.recon_label.setText(wrap_text(text, color))
        elif topic == "avr/autonomous/enable": # If the value of the auton bool is changing
            state = payload['enabled']
            if state:
                text = "Autonomous Enabled"
                color = "green"
            else:
                text = "Autonomous Disabled"
                color = "red"
            self.autonomous_label.setText(wrap_text(text, color))
        elif topic == "avr/autonomous/building/drop": # If the value of building drop bools are changing
            state = payload['enabled']
            if state:
                text = "Drop Enabled"
                color = "green"
            else:
                text = "Drop Disabled"
                color = "red"
            self.building_states[payload['id']].setText(wrap_text(text, color))
        elif topic == 'avr/sandbox/test': # If we're activating or deactivating a test
            name = payload['testName']
            state = payload['testState']
            if state:
                self.testing_states[name].setText(wrap_text("Executing...", "red"))
            else:
                self.testing_states[name].setText("")