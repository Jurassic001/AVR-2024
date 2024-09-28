import subprocess

from PySide6 import QtWidgets

from ...lib.color import wrap_text
from ...lib.config import config


class WIFIConnectionWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

    def build(self) -> None:
        """
        Build the GUI layout
        """
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

    def network_connect(self) -> None:
        network_name = self.network_name_lnedit.text()  # Take the value of the line edit
        connect_attempt = subprocess.run(["netsh", "wlan", "connect", f"name={network_name}"], capture_output=True)  # Attempt to connect
        config.network_name = network_name  # Set config as specified network
        self.connection_label.setText(wrap_text(f"Connection attempt result: {connect_attempt.stdout.decode()}", "DarkGoldenRod"))  # Display the result on the GUI
