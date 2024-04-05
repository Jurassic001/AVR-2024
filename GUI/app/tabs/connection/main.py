from PySide6 import QtWidgets, QtGui, QtCore

from ..base import BaseTabWidget
from .mqtt import MQTTConnectionWidget
from .serial import SerialConnectionWidget


class MainConnectionWidget(BaseTabWidget):
    """
    This manages connections to all the external services, and features quick window resizing options
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.setWindowTitle("Connections")
    
    def resize_window(self, parent: QtWidgets.QWidget, preset: int):
        """Internal function for resizing windows with buttons or keybinds

        Args:
            parent (QtWidgets.QWidget): The window object, self explanatory
            preset (int): 0 for small, 1 for medium, 2 for large
        """
        if preset > 3:
            preset = 3
        elif preset < 0:
            preset = 0
        parent.resize(parent.sizePresets[preset][0], parent.sizePresets[preset][1])
        parent.curPreset = preset

    def build(self, parent: QtWidgets.QWidget) -> None:
        """
        Build the GUI layout
        """
        # Create connection page layout
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # Create the Options box
        options_groupbox = QtWidgets.QGroupBox("Options & Configs")
        options_layout = QtWidgets.QVBoxLayout()
        options_groupbox.setLayout(options_layout)

        # Create the Window Size Preset layout & buttons
        """winOptions_groupbox = QtWidgets.QGroupBox("Window Size Presets")
        windowBtns_layout = QtWidgets.QHBoxLayout()
        winOptions_groupbox.setLayout(windowBtns_layout)"""
        windowBtns_layout = QtWidgets.QHBoxLayout()

        setSizeSmall_btn = QtWidgets.QPushButton("Small Window")
        windowBtns_layout.addWidget(setSizeSmall_btn)
        setSizeSmall_btn.clicked.connect(lambda: self.resize_window(parent, 0))

        setSizeMed_btn = QtWidgets.QPushButton("Medium Window")
        windowBtns_layout.addWidget(setSizeMed_btn)
        setSizeMed_btn.clicked.connect(lambda: self.resize_window(parent, 1))

        setSizeLarge_btn = QtWidgets.QPushButton("Large Window (Default)")
        windowBtns_layout.addWidget(setSizeLarge_btn)
        setSizeLarge_btn.clicked.connect(lambda: self.resize_window(parent, 2))

        setSizeMax_btn = QtWidgets.QPushButton("Maximize Window")
        windowBtns_layout.addWidget(setSizeMax_btn)
        setSizeMax_btn.clicked.connect(lambda: self.resize_window(parent, 3))

        # Create keybinds for changing window size
        shrink_keybind = QtGui.QShortcut(QtGui.QKeySequence("-"), parent)
        shrink_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset - 1))

        grow_keybind = QtGui.QShortcut(QtGui.QKeySequence("="), parent)
        grow_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset + 1))


        # Create second group box of buttons for Window Features
        """featureBtn_groupbox = QtWidgets.QGroupBox("Configs")
        featureBtn_layout = QtWidgets.QHBoxLayout()
        featureBtn_groupbox.setLayout(featureBtn_layout)"""
        featureBtns_layout = QtWidgets.QHBoxLayout()

        close_btn = QtWidgets.QPushButton("Exit GUI")
        featureBtns_layout.addWidget(close_btn)
        close_btn.clicked.connect(lambda: parent.closeEvent())

        # Add both button groupboxes to the Options groupbox
        options_layout.addLayout(windowBtns_layout)
        options_layout.addLayout(featureBtns_layout)

        # Set Box size policies
        options_groupbox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(options_groupbox)

        # ===================================
        # Create the MQTT connections box
        mqtt_groupbox = QtWidgets.QGroupBox("MQTT")
        mqtt_layout = QtWidgets.QVBoxLayout()
        mqtt_groupbox.setLayout(mqtt_layout)

        self.mqtt_connection_widget = MQTTConnectionWidget(self)
        self.mqtt_connection_widget.build()
        mqtt_layout.addWidget(self.mqtt_connection_widget)

        mqtt_groupbox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(mqtt_groupbox)

        # ======================================================
        # Create the serial connections box (cereal box hehe)
        serial_groupbox = QtWidgets.QGroupBox("Serial")
        serial_layout = QtWidgets.QVBoxLayout()
        serial_groupbox.setLayout(serial_layout)

        self.serial_connection_widget = SerialConnectionWidget(self)
        self.serial_connection_widget.build()
        serial_layout.addWidget(self.serial_connection_widget)

        serial_groupbox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(serial_groupbox)
