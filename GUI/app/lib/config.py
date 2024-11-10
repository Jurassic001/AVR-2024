import json
import os
import re
import sys
from typing import Any

if getattr(sys, "frozen", False):
    DATA_DIR = sys._MEIPASS  # type: ignore
    ROOT_DIR = os.path.dirname(sys.executable)
else:
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
    ROOT_DIR = DATA_DIR

# root dir is the directory of the main entrypoint
ROOT_DIR = os.path.abspath(ROOT_DIR)
# data dir is the root directory within the application itself
DATA_DIR = os.path.abspath(DATA_DIR)
# directory that contains images
IMG_DIR = os.path.join(DATA_DIR, "assets", "img")


class _Config:
    config_file = os.path.join(ROOT_DIR, "settings.json")
    default_config_file = os.path.join(ROOT_DIR, "default-settings.json")

    def __read(self) -> dict:
        if not os.path.isfile(self.config_file):
            if os.path.isfile(self.default_config_file):
                print("settings.json not found, creating one from default-settings.json")
                with open(self.default_config_file) as fp:
                    default_data = json.loads(self.__remove_comments(fp.read()))
                self.__write(default_data)
                return default_data
            return {}

        try:
            with open(self.config_file) as fp:
                return json.loads(self.__remove_comments(fp.read()))
        except json.JSONDecodeError:
            # on invalid files, just delete it
            os.remove(self.config_file)
            return {}

    def __remove_comments(self, json_str: str) -> str:
        pattern = re.compile(r"//.*?$|/\*.*?\*/", re.DOTALL | re.MULTILINE)
        return re.sub(pattern, "", json_str)

    def __write(self, data: dict) -> None:
        with open(self.config_file, "w") as fp:
            json.dump(data, fp, indent=4)

    def __get(self, key: str, default: Any = None) -> Any:
        data = self.__read()
        if key in data:
            return data[key]

        # if we have a set default value that is not None, write it out
        if default is not None:
            self.__set(key, default)

        return default

    def __set(self, key: str, value: Any) -> None:
        data = self.__read()
        data[key] = value
        self.__write(data)

    @property
    def temp_range(self) -> tuple:
        return eval(self.__get("temp_range", ""))

    @temp_range.setter
    def temp_range(self, value: tuple):
        return self.__set("temp_range", str(value))

    @property
    def mqtt_host(self) -> str:
        return self.__get("mqtt_host", "")

    @mqtt_host.setter
    def mqtt_host(self, value: str) -> None:
        return self.__set("mqtt_host", value)

    @property
    def mqtt_port(self) -> int:
        return self.__get("mqtt_port", 18830)

    @mqtt_port.setter
    def mqtt_port(self, value: int) -> None:
        return self.__set("mqtt_port", value)

    @property
    def serial_port(self) -> str:
        return self.__get("serial_port", "")

    @serial_port.setter
    def serial_port(self, value: str) -> None:
        return self.__set("serial_port", value)

    @property
    def serial_baud_rate(self) -> int:
        return self.__get("serial_baud_rate", 115200)

    @serial_baud_rate.setter
    def serial_baud_rate(self, value: int) -> None:
        return self.__set("serial_baud_rate", value)

    @property
    def mavlink_host(self) -> str:
        return self.__get("mavlink_host", "")

    @mavlink_host.setter
    def mavlink_host(self, value: str) -> None:
        return self.__set("mavlink_host", value)

    @property
    def mavlink_port(self) -> int:
        return self.__get("mavlink_port", 5670)

    @mavlink_port.setter
    def mavlink_port(self, value: int) -> None:
        return self.__set("mavlink_port", value)

    @property
    def log_file_directory(self) -> str:
        return self.__get("log_file_directory", os.path.join(ROOT_DIR, "logs"))

    @log_file_directory.setter
    def log_file_directory(self, value: str) -> None:
        return self.__set("log_file_directory", value)

    @property
    def joystick_inverted(self) -> bool:
        return self.__get("joystick_inverted", False)

    @joystick_inverted.setter
    def joystick_inverted(self, value: bool) -> None:
        return self.__set("joystick_inverted", value)

    @property
    def num_servos(self) -> int:
        return self.__get("num_servos", 8)

    @num_servos.setter
    def num_servos(self, value: int) -> None:
        return self.__set("num_servos", value)

    @property
    def network_name(self) -> str:
        return self.__get("network_name", "Varsity Bells")

    @network_name.setter
    def network_name(self, value: str) -> None:
        return self.__set("network_name", value)

    @property
    def mqtt_logger_auto_start(self) -> bool:
        return self.__get("mqtt_logger_auto_start", False)

    @mqtt_logger_auto_start.setter
    def mqtt_logger_auto_start(self, value: bool) -> None:
        self.__set("mqtt_logger_auto_start", value)


config = _Config()
