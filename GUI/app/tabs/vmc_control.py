from __future__ import annotations

import functools
from typing import List, Literal, Tuple

from bell.avr.mqtt.payloads import (
    AvrPcmSetBaseColorPayload,
    AvrPcmSetServoAbsPayload,
    AvrPcmSetServoOpenClosePayload,
    AvrPcmSetServoPctPayload,
    AvrPcmSetTempColorPayload,
)
from PySide6 import QtWidgets

from ..lib.color import wrap_text
from ..lib.config import config
from ..lib.widgets import IntLineEdit
from .base import BaseTabWidget


class VMCControlWidget(BaseTabWidget):
    # This is the primary control widget for the drone. This allows the user
    # to set LED color, open/close servos etc.

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        # region Init
        super().__init__(parent)

        self.setWindowTitle("VMC Control")

    def build(self) -> None:
        """
        Build the GUI layout
        """
        layout = QtWidgets.QGridLayout(self)
        self.setLayout(layout)

        self.changingLEDS: bool = False

        # region LEDs
        led_groupbox = QtWidgets.QGroupBox("LEDs")
        led_layout = QtWidgets.QVBoxLayout()
        led_groupbox.setLayout(led_layout)

        # Add buttons with stretch factors
        red_led_button = QtWidgets.QPushButton("Red")
        red_led_button.setStyleSheet("background-color: red")
        red_led_button.clicked.connect(lambda: self.set_led((255, 255, 0, 0)))  # type: ignore
        led_layout.addWidget(red_led_button)
        led_layout.addStretch(1)

        green_led_button = QtWidgets.QPushButton("Green")
        green_led_button.setStyleSheet("background-color: green")
        green_led_button.clicked.connect(lambda: self.set_led((255, 0, 255, 0)))  # type: ignore
        led_layout.addWidget(green_led_button)
        led_layout.addStretch(1)

        blue_led_button = QtWidgets.QPushButton("Blue")
        blue_led_button.setStyleSheet("background-color: blue; color: white")
        blue_led_button.clicked.connect(lambda: self.set_led((255, 0, 0, 255)))  # type: ignore
        led_layout.addWidget(blue_led_button)
        led_layout.addStretch(1)

        clear_led_button = QtWidgets.QPushButton("Clear")
        clear_led_button.setStyleSheet("background-color: white")
        clear_led_button.clicked.connect(lambda: self.set_led((0, 0, 0, 0)))  # type: ignore
        led_layout.addWidget(clear_led_button)
        led_layout.addStretch(1)

        # region _Custom colors
        custom_colors_layout = QtWidgets.QFormLayout()

        white_int_lnedit = IntLineEdit(0, 255)
        custom_colors_layout.addRow(QtWidgets.QLabel("White:"), white_int_lnedit)

        red_int_lnedit = IntLineEdit(0, 255)
        custom_colors_layout.addRow(QtWidgets.QLabel("Red:"), red_int_lnedit)

        green_int_lnedit = IntLineEdit(0, 255)
        custom_colors_layout.addRow(QtWidgets.QLabel("Green:"), green_int_lnedit)

        blue_int_lnedit = IntLineEdit(0, 255)
        custom_colors_layout.addRow(QtWidgets.QLabel("Blue:"), blue_int_lnedit)

        set_custom_colors_btn = QtWidgets.QPushButton("Set WRGB of LED strip")
        custom_colors_layout.addWidget(set_custom_colors_btn)
        set_custom_colors_btn.clicked.connect(lambda: self.set_led((white_int_lnedit.text_int(), red_int_lnedit.text_int(), green_int_lnedit.text_int(), blue_int_lnedit.text_int())))

        led_layout.addLayout(custom_colors_layout)

        led_groupbox.setMaximumWidth(200)
        layout.addWidget(led_groupbox, 0, 0, 3, 1)

        # region Servos
        self.servo_states: List[QtWidgets.QLabel] = []

        servos_groupbox = QtWidgets.QGroupBox("Servos")
        servos_layout = QtWidgets.QVBoxLayout()
        servos_groupbox.setLayout(servos_layout)

        servo_all_layout = QtWidgets.QHBoxLayout()

        servo_all_open_button = QtWidgets.QPushButton("Open all")
        servo_all_open_button.clicked.connect(lambda: self.set_servo_all("open"))  # type: ignore
        servo_all_layout.addWidget(servo_all_open_button)

        servo_all_close_button = QtWidgets.QPushButton("Close all")
        servo_all_close_button.clicked.connect(lambda: self.set_servo_all("close"))  # type: ignore
        servo_all_layout.addWidget(servo_all_close_button)

        servo_all_stop_button = QtWidgets.QPushButton("Stop all")
        servo_all_stop_button.clicked.connect(lambda: self.set_servo_all("stop"))  # type: ignore
        servo_all_layout.addWidget(servo_all_stop_button)

        servos_layout.addLayout(servo_all_layout)

        for i in range(config.num_servos):
            # region _Servo buttons
            servo_layout = QtWidgets.QHBoxLayout()

            # Servo name label
            servo_name = QtWidgets.QLabel(f"Servo {i+1}")
            servo_name.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            servo_layout.addWidget(servo_name)

            # Servo state label
            servo_state = QtWidgets.QLabel()
            servo_state.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed))
            servo_layout.addWidget(servo_state)
            self.servo_states.append(servo_state)

            # Open and close buttons
            servo_open_button = QtWidgets.QPushButton("Open")
            servo_open_button.clicked.connect(functools.partial(self.set_servo, i, "open"))  # type: ignore
            servo_layout.addWidget(servo_open_button)

            servo_close_button = QtWidgets.QPushButton("Close")
            servo_close_button.clicked.connect(functools.partial(self.set_servo, i, "close"))  # type: ignore
            servo_layout.addWidget(servo_close_button)

            servo_stop_button = QtWidgets.QPushButton("Stop")
            servo_stop_button.clicked.connect(functools.partial(self.set_servo, i, "stop"))  # type: ignore
            servo_layout.addWidget(servo_stop_button)

            # Add each row to the servo layout
            servos_layout.addLayout(servo_layout)

        layout.addWidget(servos_groupbox, 0, 1, 3, 3)

        # region Absolute cmds
        abs_servo_groupbox = QtWidgets.QGroupBox("Absolute Servo Command")
        abs_servo_form = QtWidgets.QFormLayout()
        abs_servo_groupbox.setLayout(abs_servo_form)

        abs_servo_number_lnedit = IntLineEdit(1, config.num_servos)
        abs_servo_form.addRow(QtWidgets.QLabel("Servo Number:"), abs_servo_number_lnedit)

        servo_abs_value_lnedit = IntLineEdit(0, 4096)
        abs_servo_form.addRow(QtWidgets.QLabel("Value:"), servo_abs_value_lnedit)

        # Value preset buttons
        servo_abs_val_presets = {"Regular On": 425, "Regular Off": 150, "Continuous Go": 1070, "Continuous Stop": 1472}
        value_pres = QtWidgets.QHBoxLayout()

        for key in servo_abs_val_presets:
            preset_btn = QtWidgets.QPushButton(key)
            preset_btn.clicked.connect(functools.partial(servo_abs_value_lnedit.setText, str(servo_abs_val_presets[key])))
            value_pres.addWidget(preset_btn)
        abs_servo_form.addRow(QtWidgets.QLabel("Value Presets:"), value_pres)

        abs_activate_servo_btn = QtWidgets.QPushButton("Execute Absolute Servo Command")
        abs_servo_form.addWidget(abs_activate_servo_btn)
        abs_activate_servo_btn.clicked.connect(
            lambda: self.send_message("avr/pcm/set_servo_abs", AvrPcmSetServoAbsPayload(servo=abs_servo_number_lnedit.text_int(), absolute=servo_abs_value_lnedit.text_int()))
        )

        layout.addWidget(abs_servo_groupbox, 3, 0, 1, 2)

        # region Percentage cmds
        pct_servo_groupbox = QtWidgets.QGroupBox("Percentage Servo Command")
        pct_servo_form = QtWidgets.QFormLayout()
        pct_servo_groupbox.setLayout(pct_servo_form)

        pct_servo_number_lnedit = IntLineEdit(1, config.num_servos)
        pct_servo_form.addRow(QtWidgets.QLabel("Servo Number:"), pct_servo_number_lnedit)

        servo_pct_value_lnedit = IntLineEdit(0, 100)
        pct_servo_form.addRow(QtWidgets.QLabel("Percentage:"), servo_pct_value_lnedit)

        pct_activate_servo_btn = QtWidgets.QPushButton("Execute Percentage Servo Command")
        pct_servo_form.addWidget(pct_activate_servo_btn)
        pct_activate_servo_btn.clicked.connect(
            lambda: self.send_message("avr/pcm/set_servo_pct", AvrPcmSetServoPctPayload(servo=pct_servo_number_lnedit.text_int(), percent=servo_pct_value_lnedit.text_int()))
        )

        layout.addWidget(pct_servo_groupbox, 3, 2, 1, 2)

    # region Messengers
    def set_servo(self, number: int, action: Literal["open", "close", "stop"]) -> None:
        """Set a servos state"""
        if action == "stop":
            self.send_message(
                "avr/pcm/set_servo_abs",
                AvrPcmSetServoAbsPayload(servo=number, absolute=0),
            )
        else:
            self.send_message(
                "avr/pcm/set_servo_open_close",
                AvrPcmSetServoOpenClosePayload(servo=number, action=action),
            )

        if action == "open":
            text = "Opened"
            color = "blue"
        elif action == "close":
            text = "Closed"
            color = "chocolate"
        elif action == "stop":
            text = "Stopped"
            color = "red"
        else:
            text = "Action Not Recognized"
            color = "black"

        self.servo_states[number].setText(wrap_text(text, color))

    def set_servo_all(self, action: Literal["open", "close", "stop"]) -> None:
        """
        Set all servos to the same state
        """
        for i in range(config.num_servos):
            self.set_servo(i, action)

    def set_led(self, color1: Tuple[int, int, int, int], dur: float = -1) -> None:
        """Set the LED strip to one solid color for a given duration or until changed

        Args:
            color1 (Tuple[int, int, int, int]): WRGB value to set the LED strip as
            dur (float, optional): Duration of the temporary color. Leave blank to set color until changed
        """
        if dur != -1:
            self.send_message("avr/pcm/set_temp_color", AvrPcmSetTempColorPayload(wrgb=color1, time=dur))
        else:
            self.send_message("avr/pcm/set_base_color", AvrPcmSetBaseColorPayload(wrgb=color1))
