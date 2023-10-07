from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from loguru import logger

class Sandbox(MQTTModule):
    def __init__(self) -> None:
        super().__init__()
        print('test')
        logger.debug('test')


test = Sandbox()
        
        