import json, base64, cv2, time
import numpy as np
from threading import Thread
from scipy import ndimage
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from loguru import logger


class Sandbox(MQTTModule):
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            'avr/thermal/reading': self.handle_thermal,
            'avr/fcm/status': self.handle_status,
            'avr/autonomous/building/drop': self.handle_drop,
            'avr/autonomous/enable': self.handle_autonomous,
            }
        
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.status_loop: bool = False
        
        self.is_armed: bool = False
        self.building_drops: dict  = {'Building 1': False, 'Building 2': False, 'Building 3': False, 'Building 4': False, 'Building 5': False, 'Building 6': False}
        self.thermal_pixel_matrix = [[0]*8]*8
        
        self.water_servo_pin = 5
        self.building_loc = {'Building 1': (404, 120), 'Building 2': (404, 45), 'Building 3': (356, 177), 'Building 4': (356, 53), 'Building 5': (310, 125), 'Building 6': (310, 50)}

    def handle_thermal(self, payload: AvrThermalReadingPayload) -> None:
        data = json.loads(payload)['data']
        base64_decoded = data.encode('utf-8')
        as_bytes = base64.b64decode(base64_decoded)
        thermal_pixel_ints = list(bytearray(as_bytes))
        i = 0
        for row in range(len(self.thermal_pixel_matrix[0])):
            for col in range(len(self.thermal_pixel_matrix)):
                self.thermal_pixel_matrix[row][col] = thermal_pixel_ints[i]
                i += 1
        
    def handle_status(self, payload: AvrFcmStatusPayload) -> None:
        armed = payload['armed']
        self.is_armed = armed
        
    def handle_drop(self, payload: AvrAutonomousBuildingDropPayload) -> None:
        self.building_drops[self.building_drops.keys()[payload['id']]] = payload['enabled']
    
    def handle_autonomous(self, payload: AvrAutonomousEnablePayload) -> None:
        self.autonomous = payload['enabled']
        
    def fire_cannon(self) -> None:
        self.send_message(
            'avr/pcm/fire_laser',
            AvrPcmFireLaserPayload()
        )
        
        
    def targeting(self) -> None:
        turret_angles = [275, 275]
        for i, id in enumerate(range(3, 5)):
            self.send_message(
                        "avr/pcm/set_servo_open_abs",
                        AvrPcmSetServoAbsPayload(servo= id, absolute= turret_angles[i])
                    )
        while self.auto_target:
            thermal_image = np.asarray(self.thermal_pixel_matrix, dtype=np.uint8)
            
            lowerb = np.array([0, 0, 150], np.uint8)
            upperb = np.array([90, 90, 255], np.uint8)

            frame = cv2.inRange(thermal_image, lowerb, upperb)
            blobs = frame > 100
            labels, nlabels = ndimage.label(blobs)
            # find the center of mass of each label
            t = ndimage.center_of_mass(frame, labels, np.arange(nlabels) + 1 )
            # calc sum of each label, this gives the number of pixels belonging to the blob
            s  = ndimage.sum(blobs, labels,  np.arange(nlabels) + 1 )
            # print the center of mass of the largest blob
            heat_center = [int(x) for x in t[s.argmax()][::-1]]
            print(heat_center)
            
            if heat_center[0] > frame.shape[0]/2:
                turret_angles[0] += 5
                self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= 3, absolute= turret_angles[0])
                )
            elif heat_center[0] < frame.shape[0]/2:
                turret_angles[0] -= 5
                self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= 3, absolute= turret_angles[0])
                )
            if heat_center[1] > frame.shape[1]/2:
                turret_angles[1] += 5
                self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= 4, absolute= turret_angles[1])
                )
            elif heat_center[1] < frame.shape[1]/2:
                turret_angles[1] -= 5
                self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= 4, absolute= turret_angles[1])
                )
            
    
    def status(self) -> None:
        while self.status_loop:
            pass
    
    def Autonomous(self):
        while self.autonomous:
            if max(self.building_drops):
                building = self.building_drops[list(self.building_drops.values()).index(True)]
                logger.debug(f'Moveing to building: {building}')
                if self.move(self.building_loc[building]):
                    self.send_message(
                        "avr/pcm/set_servo_open_close",
                        AvrPcmSetServoOpenClosePayload()
                    )
                    time.sleep(3)
                    self.send_message(
                        "avr/pcm/set_servo_open_close",
                        AvrPcmSetServoOpenClosePayload()
                    )
                
                
    
    def move(self, pos: tuple) -> bool:
        """ Moves to postion on field. Returns True when at location. """
        pass
        


if __name__ == '__main__':
    box = Sandbox()
    
    #Create Threads
    targeting_thread = Thread(target=box.targeting)
    targeting_thread.setDaemon(True)
    targeting_thread.start()
    
    status_thread = Thread(target=box.status)
    status_thread.setDaemon(True)
    status_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous)
    autonomous_thread.setDaemon(True)
    autonomous_thread.start()
    
    box.run()
