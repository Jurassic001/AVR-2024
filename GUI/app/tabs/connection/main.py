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
        if preset > 2:
            preset = 2
        elif preset < 0:
            preset = 0
        parent.resize(parent.sizePresets[preset][0], parent.sizePresets[preset][1])
        parent.curPreset = preset

    def build(self, parent: QtWidgets.QWidget) -> None:
        """
        Build the GUI layout
        """
        # Create the window size options box
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        winSize_groupbox = QtWidgets.QGroupBox("Window Size Options")
        winSize_layout = QtWidgets.QHBoxLayout()
        winSize_groupbox.setLayout(winSize_layout)

        # Create size buttons
        setSizeSmall_button = QtWidgets.QPushButton("Small Window")
        winSize_layout.addWidget(setSizeSmall_button)
        setSizeSmall_button.clicked.connect(lambda: self.resize_window(parent, 0))

        setSizeMed_button = QtWidgets.QPushButton("Medium Window")
        winSize_layout.addWidget(setSizeMed_button)
        setSizeMed_button.clicked.connect(lambda: self.resize_window(parent, 1))

        setSizeLarge_button = QtWidgets.QPushButton("Large Window (Default)")
        winSize_layout.addWidget(setSizeLarge_button)
        setSizeLarge_button.clicked.connect(lambda: self.resize_window(parent, 2))

        # Create keybinds for changing window size
        shrink_keybind = QtGui.QShortcut(QtGui.QKeySequence("-"), parent)
        shrink_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset - 1))

        grow_keybind = QtGui.QShortcut(QtGui.QKeySequence("="), parent)
        grow_keybind.activated.connect(lambda: self.resize_window(parent, parent.curPreset + 1))

        winSize_groupbox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(winSize_groupbox)

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
