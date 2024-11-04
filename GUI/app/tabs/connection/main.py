from PySide6 import QtWidgets

from ..base import BaseTabWidget
from .mqtt import MQTTConnectionWidget
from .networking import WIFIConnectionWidget
from .serial import SerialConnectionWidget


class MainConnectionWidget(BaseTabWidget):
    """
    This manages connections to all the external services, and features quick window resizing options
    """

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.setWindowTitle("Connections")

    def build(self, app: QtWidgets.QWidget) -> None:
        """
        Build the GUI layout
        """
        # Create connection page layout
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # region WIFI connection
        wifi_groupbox = QtWidgets.QGroupBox("WiFi")
        wifi_layout = QtWidgets.QVBoxLayout()
        wifi_groupbox.setLayout(wifi_layout)

        self.wifi_connection_widget = WIFIConnectionWidget(self)
        self.wifi_connection_widget.build()
        wifi_layout.addWidget(self.wifi_connection_widget)

        wifi_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(wifi_groupbox)

        # region MQTT connection
        mqtt_groupbox = QtWidgets.QGroupBox("MQTT")
        mqtt_layout = QtWidgets.QVBoxLayout()
        mqtt_groupbox.setLayout(mqtt_layout)

        self.mqtt_connection_widget = MQTTConnectionWidget(self)
        self.mqtt_connection_widget.build(app)
        mqtt_layout.addWidget(self.mqtt_connection_widget)

        # Connect MQTT connection state signal to WiFi disconnect handler
        self.mqtt_connection_widget.connection_state.connect(self.wifi_connection_widget.on_mqtt_disconnect)

        mqtt_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(mqtt_groupbox)

        # region serial connection
        serial_groupbox = QtWidgets.QGroupBox("Serial")
        serial_layout = QtWidgets.QVBoxLayout()
        serial_groupbox.setLayout(serial_layout)

        self.serial_connection_widget = SerialConnectionWidget(self)
        self.serial_connection_widget.build()
        serial_layout.addWidget(self.serial_connection_widget)

        serial_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(serial_groupbox)
