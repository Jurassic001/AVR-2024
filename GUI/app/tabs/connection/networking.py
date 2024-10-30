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

        connect_btn = QtWidgets.QPushButton(text="Attempt to connect to WiFi Network [Backslash]")
        connect_btn.clicked.connect(lambda: self.network_connect())
        connect_btn.setShortcut("\\")
        network_layout.addWidget(connect_btn)

        self.connection_label = QtWidgets.QLabel("")
        network_layout.addWidget(self.connection_label)

        layout.addLayout(network_layout)

        self.single_network_check()

    def network_connect(self) -> None:
        """Attempt to connect to the specified network"""
        network_name = self.network_name_lnedit.text()
        subprocess.run(["netsh", "wlan", "connect", f"name={network_name}"], capture_output=True)
        self.network_check(5)

    def network_check(self, check_attempts: int) -> None:
        """Check the connection to the network (which is named in the line edit) for a set number of times

        Args:
            check_attempts (int): The number of times we check to see if we are connected. Each check takes roughly 150 to 300 milliseconds
        """
        network_name = self.network_name_lnedit.text()
        start_time = time.time()

        for _ in range(check_attempts):
            # check if we connected successfully
            check_network = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
            if network_name in check_network.stdout:
                # update the status label and network config on successful connection
                self.connection_label.setText(wrap_text(f'Successfully connected to "{network_name}" after {round(time.time() - start_time, 2)} seconds', "Green"))
                config.network_name = network_name
                return
            # if we haven't connected, wait for 50ms before trying again
            time.sleep(0.05)
        # if the connection cannot be established, then assume the connection attempt has failed
        self.connection_label.setText(wrap_text(f'Failed to connect to "{network_name}" after {round(time.time() - start_time, 2)} seconds', "Red"))

    def single_network_check(self) -> None:
        """Check the connection to the network (which is named in the line edit) once. Does not set the value of the network_name in the config. Only intended to be used for initial connection check"""
        network_name = self.network_name_lnedit.text()
        check_network = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True)
        if network_name in check_network.stdout:
            self.connection_label.setText(wrap_text(f'Connected to "{network_name}"', "Green"))
        else:
            self.connection_label.setText(wrap_text(f'Not connected to "{network_name}"', "Red"))
