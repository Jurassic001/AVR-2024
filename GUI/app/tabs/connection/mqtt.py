import socket
from typing import Any

import paho.mqtt.client as mqtt
import playsound
from loguru import logger
from PySide6 import QtCore, QtGui, QtWidgets

from ...lib.color import wrap_text
from ...lib.config import config
from ...lib.enums import ConnectionState
from ...lib.widgets import IntLineEdit


class MQTTClient(QtCore.QObject):
    # This class MUST inherit from QObject in order for the signals to work

    # This class works with a QSigna based architecture, as the MQTT client
    # runs in a seperate thread. The callbacks from the MQTT client run in the same
    # thread as the client and thus those cannot update the GUI, as only the
    # thread that started the GUI is allowed to update it. Thus, set up the
    # MQTT client in a seperate class with signals that are emitted and connected to
    # so the data gets passed back to the GUI thread.

    # Once the Signal objects are created, they transform into SignalInstance objects
    connection_state: QtCore.SignalInstance = QtCore.Signal(object)  # type: ignore
    message: QtCore.SignalInstance = QtCore.Signal(str, str)  # type: ignore

    def __init__(self) -> None:
        super().__init__()

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        """
        Callback when the MQTT client connects
        """
        # subscribe to all topics
        logger.debug("Subscribing to all topics")
        client.subscribe("#")
        playsound.playsound(f"./GUI/assets/sounds/winXP_start.mp3", False)

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """
        Callback for every MQTT message
        """
        self.message.emit(msg.topic, msg.payload.decode("utf-8"))

    def on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int,
    ) -> None:
        """
        Callback when the MQTT client disconnects
        """
        logger.debug("Disconnected from MQTT server")
        self.connection_state.emit(ConnectionState.disconnected)
        playsound.playsound(f"./GUI/assets/sounds/winXP_err.mp3", False)

    def login(self, localHost: bool, host: str, port: int) -> None:
        """
        Connect the MQTT client to the server. This method cannot be named "connect"
        as this conflicts with the connect methods of the Signals
        """
        # do nothing on empty string
        if not host:
            return

        logger.info(f"Connecting to MQTT server at {host}:{port}")
        self.connection_state.emit(ConnectionState.connecting)

        try:
            # try to connect to MQTT server
            self.client.connect(host=host, port=port, keepalive=60)
            self.client.loop_start()

            # only save settings if you're running images on the Jetson
            if not localHost:
                config.mqtt_host = host
                config.mqtt_port = port

            # emit success
            logger.success("Connected to MQTT server")
            self.connection_state.emit(ConnectionState.connected)

        except Exception:
            logger.exception("Connection failed to MQTT server")
            self.connection_state.emit(ConnectionState.failure)

    def logout(self) -> None:
        """
        Disconnect the MQTT client to the server.
        """
        logger.info("Disconnecting from MQTT server")
        self.connection_state.emit(ConnectionState.disconnecting)

        self.client.disconnect()
        self.client.loop_stop()

        logger.info("Disconnected from MQTT server")
        self.connection_state.emit(ConnectionState.disconnected)

    def publish(self, topic: str, payload: Any) -> None:
        """
        Publish an MQTT message. Proxy function to the underlying client
        """
        if not topic:
            return

        logger.debug(f"Publishing message {topic}: {payload}")
        self.client.publish(topic, payload)


class MQTTConnectionWidget(QtWidgets.QWidget):
    connection_state: QtCore.SignalInstance = QtCore.Signal(object)  # type: ignore

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.localHost = False
        self.mqtt_client = MQTTClient()
        self.mqtt_client.connection_state.connect(self.set_connected_state)

    def hostnameSetter(self, hostLine: QtWidgets.QLineEdit) -> None:
        """Set the value of the host based on the localHost boolean

        Args:
            hostLine (QtWidgets.QLineEdit): The hostLine object
        """
        if self.localHost_checkbox.isChecked():
            # Set the hostLine value to the user's current IP address
            hostLine.setText(socket.gethostbyname(socket.gethostname()))
        else:
            # Set the hostLine value to the configured AVR address
            hostLine.setText(config.mqtt_host)

    def build(self, app: QtWidgets.QWidget) -> None:
        """
        Build the GUI layout
        """
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # lay out the host label and line edit
        host_layout = QtWidgets.QFormLayout()

        self.hostname_line_edit = QtWidgets.QLineEdit()
        host_layout.addRow(QtWidgets.QLabel("Host:"), self.hostname_line_edit)

        self.port_line_edit = IntLineEdit()
        host_layout.addRow(QtWidgets.QLabel("Port:"), self.port_line_edit)

        layout.addLayout(host_layout)

        # lay out the bottom connection state and buttons
        bottom_layout = QtWidgets.QHBoxLayout()
        self.state_label = QtWidgets.QLabel()
        bottom_layout.addWidget(self.state_label)

        button_layout = QtWidgets.QHBoxLayout()
        self.connect_button = QtWidgets.QPushButton("Connect [Forward Slash]")
        self.connect_button.setShortcut("/")
        button_layout.addWidget(self.connect_button)

        self.disconnect_button = QtWidgets.QPushButton("Disconnect")
        button_layout.addWidget(self.disconnect_button)

        bottom_layout.addLayout(button_layout)

        layout.addLayout(bottom_layout)

        # create the local hosting checkbox
        options_layout = QtWidgets.QHBoxLayout()
        self.localHost_checkbox = QtWidgets.QCheckBox("Enable Local Hosting?")
        options_layout.addWidget(self.localHost_checkbox)

        # create the force enable tabs checkbox
        self.forceEnableTabs_checkbox = QtWidgets.QCheckBox("Force Enable Tabs? [F]")
        self.forceEnableTabs_checkbox.setShortcut(QtGui.QKeySequence("F"))
        options_layout.addWidget(self.forceEnableTabs_checkbox)

        layout.addLayout(options_layout)

        # set starting state
        self.set_connected_state(ConnectionState.disconnected)

        self.hostnameSetter(self.hostname_line_edit)
        self.port_line_edit.setText(str(config.mqtt_port))

        # set up connections
        self.hostname_line_edit.editingFinished.connect(lambda: self.setFocus())
        self.port_line_edit.editingFinished.connect(lambda: self.setFocus())
        self.connect_button.clicked.connect(lambda: self.mqtt_client.login(self.localHost_checkbox.isChecked(), self.hostname_line_edit.text(), self.port_line_edit.text_int()))  # type: ignore
        self.disconnect_button.clicked.connect(self.mqtt_client.logout)  # type: ignore
        self.localHost_checkbox.stateChanged.connect(lambda: self.hostnameSetter(self.hostname_line_edit))
        self.forceEnableTabs_checkbox.stateChanged.connect(lambda: app.setActiveTabs(self.forceEnableTabs_checkbox.isChecked()))

    def set_connected_state(self, connection_state: ConnectionState) -> None:
        """
        Set the connected state of the MQTT connection widget elements.
        """
        color_lookup = {
            ConnectionState.connected: "Green",
            ConnectionState.connecting: "DarkGoldenRod",
            ConnectionState.disconnecting: "DarkGoldenRod",
            ConnectionState.disconnected: "Red",
            ConnectionState.failure: "Red",
        }

        connected = connection_state == ConnectionState.connected
        disconnected = connection_state in [
            ConnectionState.failure,
            ConnectionState.disconnected,
        ]

        self.state_label.setText(f"State: {wrap_text(connection_state.name.title(), color_lookup[connection_state])}")

        self.disconnect_button.setEnabled(connected)
        self.connect_button.setDisabled(connected)

        self.hostname_line_edit.setReadOnly(not disconnected)
        self.port_line_edit.setReadOnly(not disconnected)

        self.connection_state.emit(connection_state)
        QtGui.QGuiApplication.processEvents()
