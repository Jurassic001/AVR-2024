from bell.avr.serial.pcc import PeripheralControlComputer
from loguru import logger

import serial


class Zephyrus_PeripheralControlComputer(PeripheralControlComputer):
    def __init__(self, Z_ser: serial.Serial):
        super().__init__(Z_ser)
        self.Z_serial = Z_ser
    
        self.commands = {
            "SET_SERVO_OPEN_CLOSE": 0,
            "SET_SERVO_MIN": 1,
            "SET_SERVO_MAX": 2,
            "SET_SERVO_PCT": 3,
            "SET_SERVO_ABS": 4,
            "SET_BASE_COLOR": 5,
            "SET_TEMP_COLOR": 6,
            "FIRE_LASER": 7,
            "SET_LASER_ON": 8,
            "SET_LASER_OFF": 9,
            "RESET_AVR_PERIPH": 10,
            "CHECK_SERVO_CONTROLLER": 11,
            "SET_MAGNET_ON": 13,
            "SET_MAGNET_OFF": 14,
        }
    
    def set_magnet_on(self):
        # sourcery skip: class-extract-method
        command = self.commands["SET_MAGNET_ON"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the magnet on: {data}")
        self.Z_serial.write(data)

    def set_magnet_off(self):
        command = self.commands["SET_MAGNET_OFF"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the magnet off: {data}")
        self.Z_serial.write(data)