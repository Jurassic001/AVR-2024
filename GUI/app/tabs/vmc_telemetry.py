from __future__ import annotations

import json
from typing import Dict

from bell.avr.mqtt.payloads import (
    AvrFcmAttitudeEulerPayload,
    AvrFcmBatteryPayload,
    AvrFcmGpsInfoPayload,
    AvrFcmLocationGlobalPayload,
    AvrFcmLocationLocalPayload,
    AvrFcmStatusPayload,
    AvrFcmVelocityPayload,
    AvrFusionPositionNedPayload,
    AvrVioPositionNedPayload,
)
from PySide6 import QtCore, QtWidgets

from ..lib.color import smear_color, wrap_text
from ..lib.widgets import DisplayLineEdit, StatusLabel
from .base import BaseTabWidget


class VMCTelemetryWidget(BaseTabWidget):
    # This widget provides a minimal QGroundControl-esque interface.
    # In our case, this operates over MQTT as all the relevant data
    # is already published there.

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

        self.setWindowTitle("VMC Telemetry")

        self.last_velo: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def build(self) -> None:
        """
        Build the GUI layout
        """
        layout = QtWidgets.QVBoxLayout(self)
        self.setLayout(layout)

        # top groupbox
        top_groupbox = QtWidgets.QGroupBox("FCC Status")
        top_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        top_layout = QtWidgets.QFormLayout()
        top_groupbox.setLayout(top_layout)

        # satellites row
        self.satellites_label = QtWidgets.QLabel("")
        top_layout.addRow(QtWidgets.QLabel("Satellites:"), self.satellites_label)

        # battery row
        battery_layout = QtWidgets.QHBoxLayout()

        self.battery_percent_bar = QtWidgets.QProgressBar()
        self.battery_percent_bar.setRange(0, 100)
        self.battery_percent_bar.setTextVisible(True)
        battery_layout.addWidget(self.battery_percent_bar)

        self.battery_voltage_label = QtWidgets.QLabel("")
        battery_layout.addWidget(self.battery_voltage_label)

        top_layout.addRow(QtWidgets.QLabel("Battery:"), battery_layout)

        # armed row
        armed_layout = QtWidgets.QHBoxLayout()

        self.armed_label = QtWidgets.QLabel("")
        armed_layout.addWidget(self.armed_label)

        """
        NOTE: None of these buttons work, this specific tab hates send_message commands for some reason

        arm_button = QtWidgets.QPushButton("Arm")
        arm_button.clicked.connect(lambda: self.send_message('avr/fcm/actions', {'action': "arm", 'payload': {}}))
        armed_layout.addWidget(arm_button)

        disarm_button = QtWidgets.QPushButton("Disarm")
        disarm_button.clicked.connect(lambda: self.send_message('avr/fcm/actions', {'action': "disarm", 'payload': {}}))
        armed_layout.addWidget(disarm_button)

        kill_button = QtWidgets.QPushButton("Kill")
        # kill_button.setStyleSheet("font: bold")
        kill_button.clicked.connect(lambda: self.send_message('avr/fcm/actions', {'action': "kill", 'payload': {}}))
        armed_layout.addWidget(kill_button)
        """

        top_layout.addRow(QtWidgets.QLabel("Armed Status:"), armed_layout)

        # flight mode row
        self.flight_mode_label = QtWidgets.QLabel("")
        top_layout.addRow(QtWidgets.QLabel("Flight Mode:"), self.flight_mode_label)

        layout.addWidget(top_groupbox)

        # bottom groupbox
        bottom_group = QtWidgets.QFrame()
        bottom_group.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        bottom_layout = QtWidgets.QHBoxLayout()
        bottom_group.setLayout(bottom_layout)

        # bottom-left quadrant
        bottom_left_groupbox = QtWidgets.QGroupBox("Location")
        bottom_left_layout = QtWidgets.QFormLayout()
        bottom_left_groupbox.setLayout(bottom_left_layout)

        # FCM xyz row
        loc_xyz_layout = QtWidgets.QHBoxLayout()

        self.fcm_x_line_edit = DisplayLineEdit("")
        loc_xyz_layout.addWidget(self.fcm_x_line_edit)

        self.fcm_y_line_edit = DisplayLineEdit("")
        loc_xyz_layout.addWidget(self.fcm_y_line_edit)

        self.fcm_z_line_edit = DisplayLineEdit("")
        loc_xyz_layout.addWidget(self.fcm_z_line_edit)

        bottom_left_layout.addRow(QtWidgets.QLabel("FCM Local (x, y, z):"), loc_xyz_layout)

        # FUS NED row
        fus_xyz_layout = QtWidgets.QHBoxLayout()

        self.fus_x_line_edit = DisplayLineEdit("")
        fus_xyz_layout.addWidget(self.fus_x_line_edit)

        self.fus_y_line_edit = DisplayLineEdit("")
        fus_xyz_layout.addWidget(self.fus_y_line_edit)

        self.fus_z_line_edit = DisplayLineEdit("")
        fus_xyz_layout.addWidget(self.fus_z_line_edit)

        bottom_left_layout.addRow(QtWidgets.QLabel("FUS Local (n, e, d):"), fus_xyz_layout)

        # VIO NED row
        vio_xyz_layout = QtWidgets.QHBoxLayout()

        self.vio_x_line_edit = DisplayLineEdit("")
        vio_xyz_layout.addWidget(self.vio_x_line_edit)

        self.vio_y_line_edit = DisplayLineEdit("")
        vio_xyz_layout.addWidget(self.vio_y_line_edit)

        self.vio_z_line_edit = DisplayLineEdit("")
        vio_xyz_layout.addWidget(self.vio_z_line_edit)

        bottom_left_layout.addRow(QtWidgets.QLabel("VIO Local (n, e, d):"), vio_xyz_layout)

        # lat, lon, alt row
        loc_lla_layout = QtWidgets.QHBoxLayout()

        self.glo_lat_line_edit = DisplayLineEdit("", round_digits=8)
        loc_lla_layout.addWidget(self.glo_lat_line_edit)

        self.glo_lon_line_edit = DisplayLineEdit("", round_digits=8)
        loc_lla_layout.addWidget(self.glo_lon_line_edit)

        self.glo_alt_line_edit = DisplayLineEdit("")
        loc_lla_layout.addWidget(self.glo_alt_line_edit)

        bottom_left_layout.addRow(QtWidgets.QLabel("Global (lat, lon, alt):"), loc_lla_layout)

        bottom_layout.addWidget(bottom_left_groupbox)

        # bottom-right quadrant
        bottom_right_groupbox = QtWidgets.QGroupBox("Velocity & Attitude")
        bottom_right_layout = QtWidgets.QFormLayout()
        bottom_right_groupbox.setLayout(bottom_right_layout)

        # euler row
        att_rpy_layout = QtWidgets.QHBoxLayout()

        self.att_p_line_edit = DisplayLineEdit("")
        att_rpy_layout.addWidget(self.att_p_line_edit)

        self.att_r_line_edit = DisplayLineEdit("")
        att_rpy_layout.addWidget(self.att_r_line_edit)

        self.att_y_line_edit = DisplayLineEdit("")
        att_rpy_layout.addWidget(self.att_y_line_edit)

        bottom_right_layout.addRow(QtWidgets.QLabel("Euler (pitch, roll, yaw)"), att_rpy_layout)

        # velocity row
        fcm_vel_layout = QtWidgets.QHBoxLayout()

        self.vel_x_line_edit = DisplayLineEdit("")
        fcm_vel_layout.addWidget(self.vel_x_line_edit)

        self.vel_y_line_edit = DisplayLineEdit("")
        fcm_vel_layout.addWidget(self.vel_y_line_edit)

        self.vel_z_line_edit = DisplayLineEdit("")
        fcm_vel_layout.addWidget(self.vel_z_line_edit)

        bottom_right_layout.addRow(QtWidgets.QLabel("Velocity (fwd, right, up)"), fcm_vel_layout)

        bottom_layout.addWidget(bottom_right_groupbox)

        layout.addWidget(bottom_group)

        # ==========================
        # Status
        module_status_groupbox = QtWidgets.QGroupBox("Module Status")
        module_status_groupbox.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        module_status_layout = QtWidgets.QHBoxLayout()
        module_status_groupbox.setLayout(module_status_layout)

        # data structure to hold the topic prefixes and the corresponding widget
        self.topic_status_map: Dict[str, StatusLabel] = {}
        # data structure to hold timers to reset services to unhealthy
        self.topic_timer: Dict[str, QtCore.QTimer] = {}

        fcc_status = StatusLabel("FCM")
        self.topic_status_map["avr/fcm"] = fcc_status
        module_status_layout.addWidget(fcc_status)

        pcc_status = StatusLabel("PCM")
        self.topic_status_map["avr/pcm"] = pcc_status
        module_status_layout.addWidget(pcc_status)

        vio_status = StatusLabel("VIO")
        self.topic_status_map["avr/vio"] = vio_status
        module_status_layout.addWidget(vio_status)

        therm_status = StatusLabel("THERMAL")
        self.topic_status_map["avr/thermal"] = therm_status
        module_status_layout.addWidget(therm_status)

        at_status = StatusLabel("AT")
        self.topic_status_map["avr/apriltag"] = at_status
        module_status_layout.addWidget(at_status)

        fus_status = StatusLabel("FUS")
        self.topic_status_map["avr/fusion"] = fus_status
        module_status_layout.addWidget(fus_status)

        layout.addWidget(module_status_groupbox)

    def clear(self) -> None:
        # status
        self.battery_percent_bar.setValue(0)
        self.battery_voltage_label.setText("")

        self.armed_label.setText("")
        self.flight_mode_label.setText("")

        # position
        self.fcm_x_line_edit.setText("")
        self.fcm_y_line_edit.setText("")
        self.fcm_z_line_edit.setText("")

        self.fus_x_line_edit.setText("")
        self.fus_y_line_edit.setText("")
        self.fus_z_line_edit.setText("")

        self.vio_x_line_edit.setText("")
        self.vio_y_line_edit.setText("")
        self.vio_z_line_edit.setText("")

        self.glo_lat_line_edit.setText("")
        self.glo_lon_line_edit.setText("")
        self.glo_alt_line_edit.setText("")

        self.att_r_line_edit.setText("")
        self.att_p_line_edit.setText("")
        self.att_y_line_edit.setText("")

        self.vel_x_line_edit.setText("")
        self.vel_y_line_edit.setText("")
        self.vel_z_line_edit.setText("")

    def update_satellites(self, payload: AvrFcmGpsInfoPayload) -> None:
        """
        Update satellites information
        """
        self.satellites_label.setText(f"{payload['num_satellites']} visible, {payload['fix_type']}")

    def update_battery(self, payload: AvrFcmBatteryPayload) -> None:
        """
        Update battery information
        """
        soc = payload["soc"]
        # prevent it from dropping below 0
        soc = max(soc, 0)
        # prevent it from going above 100
        soc = min(soc, 100)

        self.battery_percent_bar.setValue(int(soc))
        self.battery_voltage_label.setText(f"{round(payload['voltage'], 4)} Volts")

        # this is required to change the progress bar color as the value changes
        color = smear_color((135, 0, 16), (11, 135, 0), value=soc, min_value=0, max_value=100)

        stylesheet = f"""
            QProgressBar {{
                border: 1px solid grey;
                border-radius: 0px;
                text-align: center;
            }}

            QProgressBar::chunk {{
                background-color: rgb{color};
            }}
            """

        self.battery_percent_bar.setStyleSheet(stylesheet)

    def update_status(self, payload: AvrFcmStatusPayload) -> None:
        """
        Update status information
        """
        if payload["armed"]:
            color = "Red"
            text = "Armed & Dangerous"
        else:
            color = "Green"
            text = "Disarmed"

        self.armed_label.setText(wrap_text(text, color))
        self.flight_mode_label.setText(payload["mode"])

    def update_local_FCM_location(self, payload: AvrFcmLocationLocalPayload) -> None:
        """
        Update local location information reported by the Flight Control Module
        """
        self.fcm_x_line_edit.setText(str(payload["dX"]))
        self.fcm_y_line_edit.setText(str(payload["dY"]))
        self.fcm_z_line_edit.setText(str(payload["dZ"]))

    def update_local_FUS_location(self, payload: AvrFusionPositionNedPayload) -> None:
        """
        Update local location information reported by the Fusion module
        """
        self.fus_x_line_edit.setText(str(payload["n"]))
        self.fus_y_line_edit.setText(str(payload["e"]))
        self.fus_z_line_edit.setText(str(payload["d"]))

    def update_local_VIO_location(self, payload: AvrVioPositionNedPayload) -> None:
        """
        Update local location information reported by the Tracking camera
        """
        self.vio_x_line_edit.setText(str(payload["n"]))
        self.vio_y_line_edit.setText(str(payload["e"]))
        self.vio_z_line_edit.setText(str(payload["d"]))

    def update_global_location(self, payload: AvrFcmLocationGlobalPayload) -> None:
        """
        Update global location information
        """
        self.glo_lat_line_edit.setText(str(payload["lat"]))
        self.glo_lon_line_edit.setText(str(payload["lon"]))
        self.glo_alt_line_edit.setText(str(payload["alt"]))

    def update_euler_attitude(self, payload: AvrFcmAttitudeEulerPayload) -> None:
        """
        Update euler attitude information
        """
        self.att_p_line_edit.setText(str(payload["pitch"]))
        self.att_r_line_edit.setText(str(payload["roll"]))
        self.att_y_line_edit.setText(str(payload["yaw"]))

    def update_FCM_velocity(self, payload: AvrFcmVelocityPayload) -> None:
        """
        Update velocity information reported by the Flight Control Module
        """
        x_velo = payload["vX"]
        y_velo = payload["vY"]
        z_velo = payload["vZ"]

        self.vel_x_line_edit.setText(str(x_velo))
        self.vel_y_line_edit.setText(str(y_velo))
        self.vel_z_line_edit.setText(str(z_velo))

    def process_message(self, topic: str, payload: str) -> None:
        """
        Process an incoming message and update the appropriate component
        """
        topic_map = {
            "avr/fcm/gps_info": self.update_satellites,
            "avr/fcm/battery": self.update_battery,
            "avr/fcm/status": self.update_status,
            "avr/fcm/location/local": self.update_local_FCM_location,
            "avr/fusion/position/ned": self.update_local_FUS_location,
            "avr/vio/position/ned": self.update_local_VIO_location,
            "avr/fcm/location/global": self.update_global_location,
            "avr/fcm/attitude/euler": self.update_euler_attitude,
            "avr/fcm/velocity": self.update_FCM_velocity,
        }

        # discard topics we don't recognize
        if topic in topic_map:
            data = json.loads(payload)
            topic_map[topic](data)

        for status_prefix in self.topic_status_map.keys():
            if not topic.startswith(status_prefix):
                continue

            # set icon to healthy
            status_label = self.topic_status_map[status_prefix]
            status_label.set_health(True)

            # reset existing timer
            if status_prefix in self.topic_timer:
                timer = self.topic_timer[status_prefix]
                timer.stop()
                timer.deleteLater()

            # create a new timer
            # Can't do .singleShot on an exisiting QTimer as that
            # creates a new instance
            timer = QtCore.QTimer()
            timer.timeout.connect(lambda: status_label.set_health(False))  # type: ignore
            timer.setSingleShot(True)
            timer.start(2000)

            self.topic_timer[status_prefix] = timer
            break
