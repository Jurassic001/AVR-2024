import json, base64, cv2, time, math, keyboard, sys
import numpy as np
from threading import Thread
from scipy import ndimage
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from loguru import logger
from collision_avoidance import collision_dectector
sys.path.insert(1, 'Common_Data/')
HAZARD_LIST = None
from data import *

class Sandbox(MQTTModule):
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            'avr/thermal/reading': self.handle_thermal,
            'avr/fcm/status': self.handle_status,
            'avr/autonomous/building/drop': self.handle_drop,
            'avr/autonomous/enable': self.handle_autonomous,
            'avr/autonomous/recon': self.handle_recon,
            'avr/apriltags/visible': self.handle_apriltags,
            'avr/vio/position/ned': self.handle_vio_position,
            }
        height_is_75_scale = True
        
        self.pause: bool = False
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.status_loop: bool = False
        self.recon: bool = False
        self.april_tags: list = []
        
        self.is_armed: bool = False
        self.building_drops: dict  = {'Building 1': False, 'Building 2': False, 'Building 3': False, 'Building 4': False, 'Building 5': False, 'Building 6': False}
        self.thermal_pixel_matrix = [[0]*8]*8
        
        self.water_servo_pin = 5
        self.building_loc = {'Building 1': (404, 120, 55), 'Building 2': (404, 45, 55), 'Building 3': (356, 177, 69), 'Building 4': (356, 53, 69), 'Building 5': (310, 125, 121), 'Building 6': (310, 50, 121)}
        if height_is_75_scale:
            for i in range(len(self.building_loc)):
                self.building_loc[f'Building {i}'] = (self.building_loc[f'Building {i}'][0], self.building_loc[f'Building {i}'][1], self.building_loc[f'Building {i}'][2]*0.75)
        
        self.position = [0]*3
        self.landing_pads = {'ground': (180, 50, 12), 'building': (231, 85, 42)}
        
        self.col_test = collision_dectector((472, 170, 200), 17.3622, HAZARD_LIST)

    # ===============
    # Topic Handlers
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
        
    def handle_recon(self, payload) -> None:
        self.recon = payload['enabled']
                
    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None:
        self.april_tags = payload['tags']
    
    def handle_vio_position(self, payload: AvrVioPositionNedPayload) -> None:
        self.position = [payload['n'], # X
                         payload['e'], # Y
                         payload['d']] # Z
    # ===============
    # Threads
    def targeting(self) -> None:
        turret_angles = [275, 275]
        for i, id in enumerate(range(3, 5)):
            self.send_message(
                        "avr/pcm/set_servo_open_abs",
                        AvrPcmSetServoAbsPayload(servo= id, absolute= turret_angles[i])
                    )
        while not self.pause and self.auto_target:
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
                self.move_servo(3, turret_angles[0])
            elif heat_center[0] < frame.shape[0]/2:
                turret_angles[0] -= 5
                self.move_servo(3, turret_angles[0])
            if heat_center[1] > frame.shape[1]/2:
                turret_angles[1] += 5
                self.move_servo(4, turret_angles[1])
            elif heat_center[1] < frame.shape[1]/2:
                turret_angles[1] -= 5
                self.move_servo(4, turret_angles[1])
            
    def status(self) -> None:
        while not self.pause and self.status_loop:
            pass
    
    def Autonomous(self):
        current_building = 1
        found_recon_apriltag = False
        while not self.pause and self.autonomous:
            if not found_recon_apriltag and current_building != 6 and self.recon and not max(self.building_drops):
                apriltag_loc = tuple(np.add(self.april_tags['pos_rel'], self.position))
                building1_loc = self.building_loc['Building 1']
                if math.isclose(apriltag_loc[0], building1_loc[0]) and math.isclose(apriltag_loc[1], building1_loc[1]) and math.isclose(apriltag_loc[2], building1_loc[2]):
                    logger.debug(f'Found Building 1 April Tag. Id: {self.april_tags["id"]}')
                    self.move(self.building_loc['Building 1'])
                    time.sleep(1)
                    self.land('ground')
                    found_recon_apriltag = True
                else:
                    self.move(self.building_loc[f'Building {current_building}'])
                    current_building += 1
            if max(self.building_drops) and not self.recon:
                building = self.building_drops[list(self.building_drops.values()).index(True)]
                logger.debug(f'Moveing to building: {building}')
                while not self.move(self.building_loc[building]): pass
                self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload()
                )
                time.sleep(3)
                self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload()
                )
    # ===============
    # Drone Movment Comands
    def move(self, pos: tuple) -> None:
        """ Moves AVR to postion on field.\n\npos: (x, y, z)"""
        if self.col_test.path_check(self.position, pos):
            # Path clear. Free to move.
            self.send_action('goto_location_ned', {'n': pos[0], 'e': pos[1], 'd': pos[2]})
        else: 
            # Path obstructed. Pathfinding.
            pathed_positions = self.col_test.path_find(self.position, pos)
            for p_pos in pathed_positions:
                self.move(self.position, p_pos)
    def takeoff(self) -> None:
        """ AVR Takeoff. """
        self.send_action('takeoff')
    def land(self, pad: str) -> None:
        """ Move to specified landing pad then land.\n\npad = ground or buidling"""
        self.move(self.landing_pads[pad])
        self.send_action('land')
    # ===============
    # Send Message Commands
    def move_servo(self, id, angle) -> None:
        self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= id, absolute= angle)
                )
    def send_action(self, action, payload = ''):
        self.send_message(
            'avr/fcm/actions',
            {'action': action, 'payload': payload}
        )
    # ===============

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
    
    if keyboard.is_pressed('tab'):
        while not keyboard.is_pressed('space'):
            box.pause = True
        else:
            box.pause = False
    if keyboard.is_pressed('q'):
        exit()
