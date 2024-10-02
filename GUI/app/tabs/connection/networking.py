import subprocess
import time

from PySide6 import QtWidgets

from ...lib.color import wrap_text
from ...lib.config import config


class WIFIConnectionWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

    def build(self) -> None:
        """Build the GUI layout for the WiFi Connection widget"""
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        network_layout = QtWidgets.QFormLayout()

        self.network_name_lnedit = QtWidgets.QLineEdit()
        self.network_name_lnedit.setText(config.network_name)
        network_layout.addRow(QtWidgets.QLabel("Network Name:"), self.network_name_lnedit)

        connect_btn = QtWidgets.QPushButton(text="Attempt to connect to WiFi Network")
        connect_btn.clicked.connect(lambda: self.network_connect())
        network_layout.addWidget(connect_btn)

        self.connection_label = QtWidgets.QLabel("")
        network_layout.addWidget(self.connection_label)

        layout.addLayout(network_layout)

        self.network_connect()

    def network_connect(self) -> None:
        # attempt to connect to the specified network
        network_name = self.network_name_lnedit.text()
        subprocess.run(["netsh", "wlan", "connect", f"name={network_name}"], capture_output=True)

        for _ in range(10):
            # check if we connected successfully ten times, once every 100ms
            time.sleep(0.1)
            check_network = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
            if network_name in check_network.stdout:
                # update the status label and network config on successful connection
                self.connection_label.setText(wrap_text(f'Successfully connected to "{network_name}"', "Green"))
                config.network_name = network_name
                return
        # if the connection cannot be established in one second, then assume the connection attempt has failed
        self.connection_label.setText(wrap_text(f'Failed to connect to "{network_name}"', "Red"))
