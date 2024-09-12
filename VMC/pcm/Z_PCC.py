import ctypes, time, serial
from struct import pack
from typing import Any, List, Literal, Optional, Union
from loguru import logger


class Zephyrus_PeripheralControlComputer:
    def __init__(self, ser: serial.Serial) -> None:
        # region __init__
        self.ser = ser

        self.PREAMBLE = (0x24, 0x50)

        self.HEADER_OUTGOING = (*self.PREAMBLE, 0x3C)
        self.HEADER_INCOMING = (*self.PREAMBLE, 0x3E)
 
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
            "SET_MAGNET_ON": 12,
            "SET_MAGNET_OFF": 13,
        }

        self.shutdown: bool = False

    # region set_base_color
    def set_base_color(self, wrgb: List[int]) -> None:
        command = self.commands["SET_BASE_COLOR"]

        # wrgb + code = 5
        if len(wrgb) != 4:
            wrgb = [0, 0, 0, 0]

        for i, color in enumerate(wrgb):
            if not isinstance(color, int) or color > 255 or color < 0:
                wrgb[i] = 0

        data = self._construct_payload(command, 1 + len(wrgb), wrgb)

        logger.debug(f"Setting base color: {data}")
        self.ser.write(data)

    # region set_temp_color
    def set_temp_color(self, wrgb: List[int], time: float = 0.5) -> None:
        command = self.commands["SET_TEMP_COLOR"]

        # wrgb + code = 5
        if len(wrgb) != 4:
            wrgb = [0, 0, 0, 0]

        for i, color in enumerate(wrgb):
            if not isinstance(color, int) or color > 255 or color < 0:
                wrgb[i] = 0

        time_bytes = self.list_pack("<f", time)
        data = self._construct_payload(
            command, 1 + len(wrgb) + len(time_bytes), wrgb + time_bytes
        )

        logger.debug(f"Setting temp color: {data}")
        self.ser.write(data)

    # region set_servo_open_close
    def set_servo_open_close(
        self, servo: int, action: Literal["open", "close"]
    ) -> None:
        valid_command = False

        command = self.commands["SET_SERVO_OPEN_CLOSE"]
        data = []

        # 128 is inflection point, over 128 == open; under 128 == close

        if action == "close":
            data = [servo, 100]
            valid_command = True

        elif action == "open":
            data = [servo, 150]
            valid_command = True

        if not valid_command:
            return

        length = 3
        data = self._construct_payload(command, length, data)

        logger.debug(f"Setting servo open/close: {data}")
        self.ser.write(data)

    # region set_servo_min
    def set_servo_min(self, servo: int, minimum: float) -> None:
        valid_command = False

        command = self.commands["SET_SERVO_MIN"]
        data = []

        if isinstance(minimum, (float, int)) and minimum < 1000 and minimum > 0:
            valid_command = True
            data = [servo, minimum]

        if not valid_command:
            return

        length = 3
        data = self._construct_payload(command, length, data)

        logger.debug(f"Setting servo min: {data}")
        self.ser.write(data)

    # region set_servo_max
    def set_servo_max(self, servo: int, maximum: float) -> None:
        valid_command = False

        command = self.commands["SET_SERVO_MAX"]
        data = []

        if isinstance(maximum, (float, int)) and maximum < 1000 and maximum > 0:
            valid_command = True
            data = [servo, maximum]

        if not valid_command:
            return

        length = 3
        data = self._construct_payload(command, length, data)

        logger.debug(f"Setting servo max: {data}")
        self.ser.write(data)

    # region set_servo_pct
    def set_servo_pct(self, servo: int, pct: int) -> None:
        valid_command = False

        command = self.commands["SET_SERVO_PCT"]
        data = []

        if isinstance(pct, (float, int)) and pct <= 100 and pct >= 0:
            valid_command = True
            data = [servo, pct]

        if not valid_command:
            return

        length = 3
        data = self._construct_payload(command, length, data)

        logger.debug(f"Setting servo percent: {data}")
        self.ser.write(data)

    # region set_servo_abs
    def set_servo_abs(self, servo: int, absolute: int) -> None:
        valid_command = False

        command = self.commands["SET_SERVO_ABS"]
        data = []

        if isinstance(absolute, int):
            uint16_absolute = ctypes.c_uint16(absolute).value
            uint8_absolute_high = (uint16_absolute >> 8) & 0xFF
            uint8_absolute_low = uint16_absolute & 0xFF
            valid_command = True
            data = [servo, int(uint8_absolute_high), int(uint8_absolute_low)]

        if not valid_command:
            return

        length = 4
        data = self._construct_payload(command, length, data)

        logger.debug(f"Setting servo absolute: {data}")
        self.ser.write(data)

    # region fire_laser
    def fire_laser(self) -> None:
        # sourcery skip: class-extract-method
        command = self.commands["FIRE_LASER"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the laser on: {data}")
        self.ser.write(data)

    # region set_laser_on
    def set_laser_on(self) -> None:
        command = self.commands["SET_LASER_ON"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the laser on: {data}")
        self.ser.write(data)

    # region set_laser_off
    def set_laser_off(self) -> None:
        command = self.commands["SET_LASER_OFF"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the laser off: {data}")
        self.ser.write(data)

    # region reset_avr_peripheral
    def reset_avr_peripheral(self) -> None:
        command = self.commands["RESET_AVR_PERIPH"]

        length = 1  # just the reset command
        data = self._construct_payload(command, length)

        logger.debug(f"Resetting the PCC: {data}")
        self.ser.write(data)

        self.ser.close()
        time.sleep(5)
        self.ser.open()

    # region check_servo_controller
    def check_servo_controller(self) -> None:
        command = self.commands["CHECK_SERVO_CONTROLLER"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Checking servo controller: {data}")
        self.ser.write(data)
    
    # region set_magnet_on
    def set_magnet_on(self):
        command = self.commands["SET_MAGNET_ON"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the magnet on: {data}")
        self.ser.write(data)

    # region set_magnet_off
    def set_magnet_off(self):
        command = self.commands["SET_MAGNET_OFF"]

        length = 1
        data = self._construct_payload(command, length)

        logger.debug(f"Setting the magnet off: {data}")
        self.ser.write(data)

    # region _construct_payload
    def _construct_payload(
        self, code: int, size: int = 0, data: Optional[list] = None
    ) -> bytes:
        # [$][P][>][LENGTH-HI][LENGTH-LOW][DATA][CRC]
        payload = bytes()

        if data is None:
            data = []

        new_data = (
            ("<3b", self.HEADER_OUTGOING),
            (">H", [size]),
            ("<B", [code]),
            ("<%dB" % len(data), data),
        )

        for section in new_data:
            payload += pack(section[0], *section[1])

        crc = self.calc_crc(payload, len(payload))

        payload += pack("<B", crc)

        return payload

    # region list_pack
    def list_pack(self, bit_format: Union[str, bytes], value: Any) -> List[int]:
        return list(pack(bit_format, value))

    # region crc8_dvb_s2
    def crc8_dvb_s2(self, crc: int, a: int) -> int:
        # https://stackoverflow.com/a/52997726
        crc ^= a
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) % 256 if crc & 0x80 else (crc << 1) % 256
        return crc

    # region calc_crc
    def calc_crc(self, string: bytes, length: int) -> int:
        crc = 0
        for i in range(length):
            crc = self.crc8_dvb_s2(crc, string[i])
        return crc
