from PySide6 import QtWidgets, QtGui

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

        # Create the Options/Configs box
        options_groupbox = QtWidgets.QGroupBox("Options / Configs")
        options_layout = QtWidgets.QVBoxLayout()
        options_groupbox.setLayout(options_layout)

        # Create the Window Size Preset layout & buttons
        windowBtns_layout = QtWidgets.QHBoxLayout()

        windowBtns_text = QtWidgets.QLabel("Window Size Presets (Use -/+ to switch around):")
        windowBtns_text.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        windowBtns_layout.addWidget(windowBtns_text)

        setSizeSmall_btn = QtWidgets.QPushButton("Small Window")
        setSizeSmall_btn.clicked.connect(lambda: self.resize_window(parent, 0))
        windowBtns_layout.addWidget(setSizeSmall_btn)
        
        setSizeMed_btn = QtWidgets.QPushButton("Medium Window")
        setSizeMed_btn.clicked.connect(lambda: self.resize_window(parent, 1))
        windowBtns_layout.addWidget(setSizeMed_btn)
        
        setSizeLarge_btn = QtWidgets.QPushButton("Large Window (Default)")
        setSizeLarge_btn.clicked.connect(lambda: self.resize_window(parent, 2))
        windowBtns_layout.addWidget(setSizeLarge_btn)

        setSizeMax_btn = QtWidgets.QPushButton("Maximize Window")
        setSizeMax_btn.clicked.connect(lambda: self.resize_window(parent, 3))
        windowBtns_layout.addWidget(setSizeMax_btn)
        
        # Keybinds for changing window size
        shrink_keybind = QtGui.QShortcut(QtGui.QKeySequence("-"), parent)
        shrink_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset - 1))

        grow_keybind = QtGui.QShortcut(QtGui.QKeySequence("="), parent)
        grow_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset + 1))


        # Create the Config layout & buttons
        configBtns_layout = QtWidgets.QHBoxLayout()

        testing_btn = QtWidgets.QPushButton("Second row button")
        # testing_btn.clicked.connect(lambda: )
        configBtns_layout.addWidget(testing_btn)

        # Add button layouts to the Options layout
        options_layout.addLayout(windowBtns_layout)
        options_layout.addLayout(configBtns_layout)

        # Set Options/Configs box size policies
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