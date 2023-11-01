import json, base64, cv2, time, math, keyboard, sys
import numpy as np
from threading import Thread
from scipy import ndimage
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from bell.avr.utils import decorators
from loguru import logger
from collision_avoidance import collision_dectector

class Sandbox(MQTTModule):
    def __init__(self) -> None:
        super().__init__()
        self.topic_map = {
            'avr/thermal/reading': self.handle_thermal,
            'avr/fcm/status': self.handle_status,
            'avr/autonomous/building/drop': self.handle_drop,
            'avr/autonomous/enable': self.handle_autonomous,
            'avr/autonomous/recon': self.handle_recon,
            'avr/autonomous/thermal_range': self.handle_thermal_range,
            'avr/autonomous/thermal_targeting': self.handle_thermal_tracker,
            'avr/apriltags/visible': self.handle_apriltags,
            'avr/vio/position/ned': self.handle_vio_position,
            'avr/sandbox/user_in': self.handle_user_in,
            }
        height_is_75_scale = True
        self.target_range = (25, 40)
        
        self.pause: bool = False
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.recon: bool = False
        self.april_tags: list = []
        
        self.is_armed: bool = False
        self.building_drops: dict  = {'Building 0': False, 'Building 1': False, 'Building 2': False, 'Building 3': False, 'Building 4': False, 'Building 5': False}
        self.thermal_grid = [[0 for _ in range(8)] for _ in range(8)]
        self.sanity = 'Gone'
        
        self.water_servo_pin = 5
        self.building_loc = {'Building 0': (404, 120, 55), 'Building 1': (404, 45, 55), 'Building 2': (356, 177, 69), 'Building 3': (356, 53, 69), 'Building 4': (310, 125, 121), 'Building 5': (310, 50, 121)}
        if height_is_75_scale:
            for i in range(len(self.building_loc)):
                self.building_loc[f'Building {i}'] = (self.building_loc[f'Building {i}'][0], self.building_loc[f'Building {i}'][1], self.building_loc[f'Building {i}'][2]*0.75)
        
        self.position = (0, 0, 0)
        self.landing_pads = {'ground': (180, 50, 12), 'building': (231, 85, 42)}
        
        self.col_test = collision_dectector((472, 170, 200), 17.3622)
        self.threads: dict

    def set_threads(self, threads):
        self.threads = threads
    # ===============
    # Topic Handlers
    def handle_thermal(self, payload: AvrThermalReadingPayload) -> None:
        data = payload['data']
        # decode the payload
        base64Decoded = data.encode("utf-8")
        asbytes = base64.b64decode(base64Decoded)
        pixel_ints = list(bytearray(asbytes))
        k = 0
        for i in range(len(self.thermal_grid)):
            for j in range(len(self.thermal_grid[0])):
                self.thermal_grid[j][i] = pixel_ints[k]
                k+=1
        
    def handle_status(self, payload: AvrFcmStatusPayload) -> None:
        armed = payload['armed']
        self.is_armed = armed
        
    def handle_drop(self, payload: AvrAutonomousBuildingDropPayload) -> None:
        self.building_drops[list(self.building_drops.keys())[payload['id']]] = payload['enabled']
    
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
        
    def handle_user_in(self, payload) -> None:
        try:
            self.pause = payload['pause']
        except:
            pass
        
    def handle_thermal_tracker(self, payload) -> None:
        self.auto_target = payload['enabled']
        if self.auto_target:
            turret_angles = [1450, 1450]
            self.send_message(
                        "avr/pcm/set_servo_abs",
                        AvrPcmSetServoAbsPayload(servo= 2, absolute= turret_angles[0])
                    )
            self.send_message(
                        "avr/pcm/set_servo_abs",
                        AvrPcmSetServoAbsPayload(servo= 3, absolute= turret_angles[1])
                    )
    
    def handle_thermal_range(self, payload) -> None:
        self.target_range = payload['range']
    
    # ===============
    # Threads
    def targeting(self) -> None:
        logger.debug('Thermal Tracking Thread: Online')
        turret_angles = [1450, 1450]
        while True:
            if not self.auto_target:
                continue
            img = np.array(self.thermal_grid)
            lowerb = np.array(self.target_range[0], np.uint8)
            upperb = np.array(self.target_range[1], np.uint8)
            mask = cv2.inRange(img, lowerb, upperb)
            logger.debug(mask)
            print(mask)
            if np.all(np.array(mask) == 0):
                continue
            blobs = mask > 100
            labels, nlabels = ndimage.label(blobs)
            # find the center of mass of each label
            t = ndimage.center_of_mass(mask, labels, np.arange(nlabels) + 1 )
            # calc sum of each label, this gives the number of pixels belonging to the blob
            s  = ndimage.sum(blobs, labels,  np.arange(nlabels) + 1 )
            heat_center = [int(x) for x in t[s.argmax()][::-1]]
            print(heat_center)
            logger.debug(heat_center)
            
            if heat_center[0] > mask.shape[0]/2:
                turret_angles[0] += 10
                self.move_servo(2, turret_angles[0])
            elif heat_center[0] < mask.shape[0]/2:
                turret_angles[0] -= 10
                self.move_servo(2, turret_angles[0])
            if heat_center[1] < mask.shape[1]/2:
                turret_angles[1] += 10
                self.move_servo(3, turret_angles[1])
            elif heat_center[1] > mask.shape[1]/2:
                turret_angles[1] -= 10
                self.move_servo(3, turret_angles[1])
        logger.debug('Thermal Tracking Thread: Offline')
    
    def CIC(self) -> None:
        logger.debug('CIC Thread: Online')
        status_thread = Thread(target=self.status)
        status_thread.daemon = True
        #status_thread.setDaemon(True)
        status_thread.start()
        while True:
            if not self.CIC_loop:
                continue
            if self.position == (42, 42, 42):
                self.sanity = "Here"
        logger.debug('CIC Thread: Offline')
    def status(self):
        onoff = {True: 'Online', False: 'Offline'}
        while True:
            if self.show_status:
                time.sleep(0.5)
                self.send_message(
                    'avr/sandbox/CIC',
                    {'Thermal Targeting': onoff[self.threads['thermal'].is_alive()], 'CIC': onoff[self.threads['cic'].is_alive()], 'Autonomous': onoff[self.threads['auto'].is_alive()], 'Recon': self.recon, 'Sanity': self.sanity}
                )
        logger.debug('Status CIC Sub-Thread: Offline')
           
    def Autonomous(self):
        logger.debug('Autonomous Thread: Online')
        current_building = 1
        found_recon_apriltag = False
        while True:
            if not self.autonomous:
                continue
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
            if bool(max(self.building_drops)) and not self.recon:
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
        logger.debug('Autonomous Thread: Offline')
    # ===============
    # Drone Movment Comands
    def move(self, pos: tuple) -> None:
        """ Moves AVR to postion on field.\n\npos: (x, y, z)"""
        if not self.col_test.path_check(self.position, pos):
            # Path clear. Free to move.
            self.send_action('goto_location_ned', {'n': pos[0], 'e': pos[1], 'd': pos[2]})
        else:
            # Path obstructed. Pathfinding.
            pathed_positions = self.col_test.path_find(self.position, pos)
            for p_pos in pathed_positions:
                self.move(self.position, p_pos)
    def takeoff(self) -> None:
        """ AVR Takeoff. """
        self.send_action('takeoff', {'alt': 2})
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
    targeting_thread.daemon = True
    #targeting_thread.setDaemon(True)
    targeting_thread.start()
    
    CIC_thread = Thread(target=box.CIC)
    CIC_thread.daemon = True
    #CIC_thread.setDaemon(True)
    CIC_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous)
    autonomous_thread.daemon = True
    #autonomous_thread.setDaemon(True)
    autonomous_thread.start()
    
    box.set_threads({'thermal': targeting_thread, 'cic': CIC_thread, 'auto': autonomous_thread})
    
    box.run()
