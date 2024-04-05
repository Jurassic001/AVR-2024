from PySide6 import QtWidgets

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

    def build(self, parent, monitor: object) -> None:
        """
        Build the GUI layout
        """
        # Create the window size options box
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        winSize_groupbox = QtWidgets.QGroupBox("Window Size Options")
        winSize_layout = QtWidgets.QHBoxLayout()
        winSize_groupbox.setLayout(winSize_layout)

        setSizeSmall_button = QtWidgets.QPushButton("Small Window")
        winSize_layout.addWidget(setSizeSmall_button)

        setSizeSmall_button.clicked.connect(
            lambda: parent.resize(500, 400)
        )

        setSizeMed_button = QtWidgets.QPushButton("Medium Window")
        winSize_layout.addWidget(setSizeMed_button)

        setSizeMed_button.clicked.connect(
            lambda: parent.resize(monitor.width - 800, monitor.height - 500)
        )

        setSizeLarge_button = QtWidgets.QPushButton("Large Window (Default)")
        winSize_layout.addWidget(setSizeLarge_button)

        setSizeLarge_button.clicked.connect(
            lambda: parent.resize(monitor.width, monitor.height)
        )

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
