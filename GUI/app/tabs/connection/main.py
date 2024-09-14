from PySide6 import QtGui, QtWidgets

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

    def build(self, app: QtWidgets.QWidget) -> None:
        """
        Build the GUI layout
        """
        # Create connection page layout
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        """
        # Create the Button and Label Examples box
        example_groupbox = QtWidgets.QGroupBox("Button and Label Examples")
        example_layout = QtWidgets.QVBoxLayout()
        example_groupbox.setLayout(example_layout)

        # Create the top button layout
        topBtns_layout = QtWidgets.QHBoxLayout()

        topBtns_text = QtWidgets.QLabel("Scaling text label:")
        topBtns_text.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
        topBtns_layout.addWidget(topBtns_text)

        top1_btn = QtWidgets.QPushButton("Top Row Button One")
        top1_btn.clicked.connect(lambda: " Put button action here ")
        topBtns_layout.addWidget(top1_btn)
        
        top2_btn = QtWidgets.QPushButton("Top Row Button Two")
        top2_btn.clicked.connect(lambda: " Put button action here ")
        topBtns_layout.addWidget(top2_btn)

        # Create the bottom button layout
        bottomBtns_layout = QtWidgets.QHBoxLayout()

        bottom1_btn = QtWidgets.QPushButton("Button Row Button")
        bottomBtns_layout.addWidget(bottom1_btn)

        # Add button layouts to the Options layout
        example_layout.addLayout(topBtns_layout)
        example_layout.addLayout(bottomBtns_layout)

        # Set Button and Label Examples box size policies
        example_groupbox.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed
        )
        layout.addWidget(example_groupbox)
        """

        # ===================================
        # Create the MQTT connections box
        mqtt_groupbox = QtWidgets.QGroupBox("MQTT")
        mqtt_layout = QtWidgets.QVBoxLayout()
        mqtt_groupbox.setLayout(mqtt_layout)

        self.mqtt_connection_widget = MQTTConnectionWidget(self)
        self.mqtt_connection_widget.build(app)
        mqtt_layout.addWidget(self.mqtt_connection_widget)

        mqtt_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(mqtt_groupbox)

        # ======================================================
        # Create the serial connections box (cereal box hehe)
        serial_groupbox = QtWidgets.QGroupBox("Serial")
        serial_layout = QtWidgets.QVBoxLayout()
        serial_groupbox.setLayout(serial_layout)

        self.serial_connection_widget = SerialConnectionWidget(self)
        self.serial_connection_widget.build()
        serial_layout.addWidget(self.serial_connection_widget)

        serial_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        layout.addWidget(serial_groupbox)
