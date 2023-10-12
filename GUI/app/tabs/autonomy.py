from __future__ import annotations

import functools
from typing import List

from bell.avr.mqtt.payloads import (
    AvrAutonomousBuildingDropPayload,
    AvrAutonomousEnablePayload,
)
from PySide6 import QtCore, QtWidgets

from ..lib.color import wrap_text
from .base import BaseTabWidget


class AutonomyWidget(BaseTabWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.setWindowTitle("Autonomy")

    def build(self) -> None:
        """
        Build the GUI layout
        """
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

        self.autonomous_label = QtWidgets.QLabel()
        self.autonomous_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        autonomous_layout.addWidget(self.autonomous_label)

        layout.addWidget(autonomous_groupbox, 0, 0, 1, 1)
        
        # ==========================
        # Custom Box
        custom_main_groupbox = QtWidgets.QGroupBox('Custom')
        custom_layout = QtWidgets.QHBoxLayout()
        custom_main_groupbox.setLayout(custom_layout)
        
            # ==========================
            # Recon Box
        recon_groupbox = QtWidgets.QGroupBox('Recon')
        recon_layout = QtWidgets.QVBoxLayout()
        recon_groupbox.setLayout(recon_layout)
        
        custom_recon_go_button = QtWidgets.QPushButton('Go')
        custom_recon_go_button.clicked.connect(lambda: self.set_recon(True))
        recon_layout.addWidget(custom_recon_go_button)
        
        custom_recon_stop_button = QtWidgets.QPushButton('Pause')
        custom_recon_stop_button.clicked.connect(lambda: self.set_recon(False))
        recon_layout.addWidget(custom_recon_stop_button)
        
        self.recon_label = QtWidgets.QLabel()
        self.recon_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        recon_layout.addWidget(recon_groupbox)
        custom_layout.addWidget(recon_groupbox)
            # ==========================
            # Thermal Target Box
        thermal_groupbox = QtWidgets.QGroupBox('Thermal Tracking')
        thermal_layout = QtWidgets.QVBoxLayout()
        thermal_groupbox.setLayout(thermal_layout)
        
        thermal_go_button = QtWidgets.QPushButton('Start')
        thermal_go_button.clicked.connect(lambda: self.set_thermal_auto(True))
        thermal_layout.addWidget(thermal_go_button)
        
        thermal_stop_button = QtWidgets.QPushButton('Stop')
        thermal_stop_button.clicked.connect(lambda: self.set_thermal_auto(False))
        thermal_layout.addWidget(thermal_stop_button)
        
        self.thermal_label = QtWidgets.QLabel()
        self.thermal_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        thermal_layout.addWidget(thermal_groupbox)
        custom_layout.addWidget(thermal_groupbox)
            # ==========================
            # Placeholder Box
        _groupbox = QtWidgets.QGroupBox('Placeholder')
        _layout = QtWidgets.QVBoxLayout()
        _groupbox.setLayout(_layout)
        
        _go_button = QtWidgets.QPushButton('_')
        _go_button.clicked.connect(lambda: self.set_(True))
        _layout.addWidget(_go_button)
        
        _stop_button = QtWidgets.QPushButton('_')
        _stop_button.clicked.connect(lambda: self.set_(False))
        _layout.addWidget(_stop_button)
        
        self._label = QtWidgets.QLabel()
        self._label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        _layout.addWidget(_groupbox)
        custom_layout.addWidget(_groupbox)
        
        self.custom_label = QtWidgets.QLabel()
        self.custom_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        custom_layout.addWidget(self.custom_label)
        layout.addWidget(custom_main_groupbox, 1, 0, 1, 1)

        # ==========================
        # Buildings
        self.number_of_buildings = 6
        self.building_labels: List[QtWidgets.QLabel] = []

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

        for i in range(self.number_of_buildings):
            building_groupbox = QtWidgets.QGroupBox(f"Building {i}")
            building_layout = QtWidgets.QHBoxLayout()
            building_groupbox.setLayout(building_layout)

            building_enable_button = QtWidgets.QPushButton("Enable Drop")
            building_enable_button.clicked.connect(functools.partial(self.set_building, i, True))  # type: ignore
            building_layout.addWidget(building_enable_button)

            building_disable_button = QtWidgets.QPushButton("Disable Drop")
            building_disable_button.clicked.connect(functools.partial(self.set_building, i, False))  # type: ignore
            building_layout.addWidget(building_disable_button)

            building_label = QtWidgets.QLabel()
            building_label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignRight
                | QtCore.Qt.AlignmentFlag.AlignVCenter
            )
            building_layout.addWidget(building_label)
            self.building_labels.append(building_label)

            buildings_layout.addWidget(building_groupbox)

        layout.addWidget(buildings_groupbox, 2, 0, 4, 1)

    def set_building(self, number: int, state: bool) -> None:
        # sourcery skip: assign-if-exp
        """
        Set a building state
        """
        self.send_message(
            "avr/autonomous/building/drop",
            AvrAutonomousBuildingDropPayload(id=number, enabled=state),
        )

        if state:
            text = "Drop Enabled"
            color = "green"
        else:
            text = "Drop Disabled"
            color = "red"

        self.building_labels[number].setText(wrap_text(text, color))

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
        self.send_message(
            "avr/autonomous/enable", AvrAutonomousEnablePayload(enabled=state)
        )

        if state:
            text = "Autonomous Enabled"
            color = "green"
        else:
            text = "Autonomous Disabled"
            color = "red"

        self.autonomous_label.setText(wrap_text(text, color))
        
    def set_recon(self, state: bool) -> None:
        """ Starts AVR Recon. """
        self.send_message(
            'avr/autonomous/recon', {'enabled': state}
        )
        
        if state:
            text = 'Recon Enabled'
            color = 'green'
        else:
            text = 'Recon Disabled'
            color = 'red'
            
        self.recon_label.setText(wrap_text(text, color))
            
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
    
    def set_(self, state: bool) -> None:
        """ [Place Holder] """
        self.send_message(
            'avr/autonomous/placeholder', {'enabled': state}
        )