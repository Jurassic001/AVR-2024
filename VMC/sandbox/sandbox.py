import json, base64, cv2, time, math, keyboard, sys, asyncio
import numpy as np
from threading import Thread
from scipy import ndimage
from scipy.interpolate import interp1d
from bell.avr.mqtt.client import MQTTModule
from bell.avr.mqtt.payloads import *
from bell.avr.utils import decorators
from loguru import logger
from collision_avoidance import collision_dectector
from contextvars import ContextVar

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
            'avr/fusion/position/ned': self.handle_pos,
            'avr/sandbox/dev': self.handle_dev,
            'avr/fcm/events': self.handle_events,
            }
        height_is_75_scale = True
        self.target_range = (30, 40)
        self.targeting_step = 7
        
        self.pause: bool = False
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.recon: bool = False
        self.april_tags: list = []
        
        self.do_pathfinding = False
        self.position = [0, 0, 0]
        
        self.start_pos = (180, 50, 0)
        #self.start_pos = (231, 85, 52) # Only use on homefield firehouse start
        
        self.normal_color = [0, 255, 0, 0]
        self.flash_color = [0, 255, 255, 0]
        
        self.action_queue = []
        
        self.is_armed: bool = False
        self.building_drops: dict  = {0: False, 1: False, 2: False, 3: False, 4: False, 6: False}
        self.thermal_grid = [[0 for _ in range(8)] for _ in range(8)]
        self.sanity = 'Gone'
        self.laser_on = False
        
        self.water_servo_pin = 5
        self.building_loc = {'Building 0': (404, 120, 55), 'Building 1': (404, 45, 55), 'Building 2': (356, 177, 69), 'Building 3': (356, 53, 69), 'Building 4': (310, 125, 121), 'Building 5': (310, 50, 121)}
        if height_is_75_scale:
            for i in range(len(self.building_loc)):
                self.building_loc[f'Building {i}'] = (self.building_loc[f'Building {i}'][0], self.building_loc[f'Building {i}'][1], self.building_loc[f'Building {i}'][2]*0.75)
        
        self.position = (0, 0, 0)
        self.landing_pads = {'ground': (180, 50, 12), 'building': (231, 85, 42)}
        
        self.col_test = collision_dectector((472, 170, 200), 17.3622)
        self.threads: dict
        self.invert = 1
        
        self.tag_flashing = False
        
        self.takeoff_complete = False
        self.move_complete = False
        self.land_complete = False
        
        self.fcm_init = False
        self.latest_dev = None
        
        self.waiting_events = ContextVar('test', default={'landed_state_in_air_event': asyncio.Event(), 'landed_state_on_ground_event': asyncio.Event(), 'goto_complete_event': asyncio.Event()})
        
        
    def set_threads(self, threads: dict):
        self.threads: dict = threads
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
        self.fcm_init = True
        
    def handle_drop(self, payload: AvrAutonomousBuildingDropPayload) -> None:
        self.building_drops[list(self.building_drops.keys())[payload['id']]] = payload['enabled']
    
    def handle_autonomous(self, payload: AvrAutonomousEnablePayload) -> None:
        self.autonomous = payload['enabled']
        
    def handle_recon(self, payload) -> None:
        self.recon = payload['enabled']
                
    def handle_apriltags(self, payload: AvrApriltagsVisiblePayload) -> None:
        if self.tag_flashing:
            return
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
        self.target_range = payload['range'][0:2]
        logger.debug(self.target_range)
        self.targeting_step = int(payload['range'][2])
        
    def handle_pos(self, payload: AvrFusionPositionNedPayload):
        # NOTE Check if direction is based on drone start or global
        self.position[0] = payload['n']
        self.position[1] = payload['e']
        self.position[2] = payload['d']
        
    def handle_dev(self, payload):
        self.latest_dev = payload
        if payload == 'test_flight':
            async def tester():
                logger.debug('Test Flight Starting...')
                self.send_message('avr/fcm/capture_home', {}) # Zero NED pos
                logger.debug('Home Captured')
                asyncio.create_task(self.takeoff())
                await self.wait_for_event('landed_state_in_air_event')
                logger.debug('Takeoff Done')
                asyncio.create_task(self.land())
                await self.wait_for_event('landed_state_on_ground_event')
                logger.debug('Landed')
            asyncio.run(tester())

        elif payload == 'sound_test':
            logger.debug('Playing sound file: sound_1.WAV')
            self.sound_laptop(1)
            
    def handle_events(self, payload: AvrFcmEventsPayload):
        """ `AvrFcmEventsPayload`:\n\n`name`: event name,\n\n`payload`: event payload"""
        action = payload['name']
        try:
            if action in self.waiting_events.get().keys():
                self.waiting_events.set(self.waiting_events.get()[action].set())
        except Exception as e:
            logger.error(e)
            
        if action == 'landed_state_in_air_event':
            self.in_air = True
            self.on_ground = False
        elif action == 'landed_state_on_ground_event':
            self.on_ground = True
            self.in_air = False
        
    # ===============
    # Threads
    def targeting(self) -> None:
        logger.debug('Thermal Tracking Thread: Online')
        turret_angles = [1450, 1450]
        while True:
            if not self.auto_target:
                if self.laser_on:
                    self.set_laser(False)
                continue
            if not self.laser_on:
                self.set_laser(True)
            img = np.array(self.thermal_grid)
            lowerb = np.array(self.target_range[0], np.uint8)
            upperb = np.array(self.target_range[1], np.uint8)
            mask = cv2.inRange(img, lowerb, upperb)
            logger.debug(f'\n{mask}')
            if np.all(np.array(mask) == 0):
                continue
            blobs = mask > 100
            labels, nlabels = ndimage.label(blobs)
            # find the center of mass of each label
            t = ndimage.center_of_mass(mask, labels, np.arange(nlabels) + 1 )
            # calc sum of each label, this gives the number of pixels belonging to the blob
            s  = ndimage.sum(blobs, labels,  np.arange(nlabels) + 1 )
            heat_center = [float(x) * self.invert for x in t[s.argmax()][::-1]]
            move_range = [15, -15]
            m = interp1d([0, 8], move_range)
            move_val = ()
            logger.debug(heat_center)
            if heat_center[0] > 4:
                turret_angles[0] += self.targeting_step
                self.move_servo(2, turret_angles[0])
            elif heat_center[0] < 4:
                turret_angles[0] -= self.targeting_step
                self.move_servo(2, turret_angles[0])
            if heat_center[1] < 4:
                turret_angles[1] += self.targeting_step
                self.move_servo(3, turret_angles[1])
            elif heat_center[1] > 4:
                turret_angles[1] -= self.targeting_step
                self.move_servo(3, turret_angles[1])
                
    def CIC(self) -> None:
        logger.debug('CIC Thread: Online')
        status_thread = Thread(target=self.status)
        status_thread.daemon = True
        status_thread.start()
        light_init = False
        has_gotten_hot = False
        found_high_tag = False
        while True:
            if not self.CIC_loop:
                continue
            if self.fcm_init and not light_init:
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color))
                for i in range (5, 8):
                    self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload(servo= i, action= 'open')
                    )
                light_init = True
                
            if not found_high_tag and next((tag for tag in self.april_tags if tag['id'] == 0), None):
                self.tag_flashing = True
                logger.debug('Tag found')
                for i in range(3):
                    #self.send_message('avr/pcm/set_temp_color', {'wrgb': self.flash_color, 'duration': 0.3})
                    self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.flash_color))
                    time.sleep(.3)
                    self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=[0]*4))
                self.tag_flashing = False
                found_high_tag = False
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color))
                
            if not has_gotten_hot and np.any(np.array(self.thermal_grid) >= 27):
                for i in range(10):
                    logger.debug('HOT SPOT DETECTED. GO UP')
                self.sound_laptop(1)
                has_gotten_hot = True
                self.tag_flashing = True
                if next((tag for tag in self.april_tags if tag['id'] in range(4, 7)), None):
                    for i in range(3):
                        self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.flash_color))
                        time.sleep(.3)
                        self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=[0]*4))
                self.tag_flashing = False
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color))
                
            if self.position == (42, 42, 42):
                self.sanity = "Here"
            else:
                self.sanity = 'Gone'

    def status(self):
        logger.debug('Status Sub-Thread: Online')
        onoffline = {True: 'Online', False: 'Offline'}
        onoff = {True: 'On', False: 'Off'}
        while True:
            if self.show_status:
                time.sleep(0.5)
                self.send_message(
                    'avr/sandbox/CIC',
                    {'Thermal Targeting': onoffline[self.threads['thermal'].is_alive()], 'CIC': onoffline[self.threads['cic'].is_alive()], 'Autonomous': onoffline[self.threads['auto'].is_alive()], 'Recon': onoff[self.recon], 'Sanity': self.sanity, 'Laser': onoff[self.laser_on]}
                )
           
    def Autonomous(self):
        logger.debug('Autonomous Thread: Online')
        while True:
            if not self.autonomous:
                continue
            
            """ tag:dict = next((tag for tag in self.april_tags if str(tag['id']) in building[0] for building in self.building_drops.items() if building[1]))
            if tag:
                n, e, d = tag['pos'].values() """
                
            
            if not self.recon:
                continue
            
            self.send_message('avr/fcm/capture_home', {}) # Zero NED pos
            time.sleep(.5)
            
            self.takeoff()
            self.wait_for_event('landed_state_in_air_event')
            
            self.move((310, 125, 60*.75)) # Building 5
            self.wait_for_event('goto_complete_event')
            
            self.move((356, 53, 85*.75)) # Building 4
            self.wait_for_event('goto_complete_event')
            
            self.move((404, 120, 126*.75)) # Building 1
            self.wait_for_event('goto_complete_event')
            # Look for april tag 1 and flash led if found.
            if next((tag for tag in self.april_tags if tag['id'] == 0), None):
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=[0, 255, 0, 0]))
                time.sleep(.5)
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=[0, 0, 0, 255]))
            time.sleep(1)
            
            self.move((231, 85, 52*.75)) # Fire house
            self.wait_for_event('goto_complete_event')
            
            self.land()
            self.recon = False
            
    # ===============
    # Drone Control Comands
    async def move(self, pos: tuple, heading: float = 0, pathing: bool = False) -> None:
        """ Moves AVR to postion on field.\n\npos(inches): (x, y, z) """
        if not pathing or not self.col_test.path_check(self.position, pos):
            relative_pos = [0, 0, 0]
            for i in range(3):
                relative_pos[i] = self.inch_to_m(pos[i]) + self.start_pos[i] * self.invert
            relative_pos[2] *= -1
            logger.debug(f'NED: {relative_pos}')
            self.send_action('goto_location_ned', {'n': relative_pos[0], 'e': relative_pos[1], 'd': relative_pos[2], 'heading': heading})
        else:
            # Path obstructed.
            if self.do_pathfinding:
                # Pathfinding.
                pathed_positions = self.col_test.path_find(self.position, pos)
                for p_pos in pathed_positions:
                    self.move(self.position, p_pos)
                    time.sleep(.5)
            else:
                logger.debug(f'[({self.position})->({pos})] Path obstructed. Movment command canceled.')
                
        """ while not self.move_complete:
            logger.debug('Waiting for move confirm', self.move_complete)
        self.move_complete = False """
    
    async def takeoff(self, alt = 39.3701) -> None:
        """ AVR Takeoff. \n\nAlt in inches. Defult 1 meter."""
        self.send_action('takeoff', {'alt': round(self.inch_to_m(alt), 1)})
    async def land(self) -> None:
        """ AVR Land"""
        #self.move(self.landing_pads[pad])
        self.send_action('land')

    # ===============
    # Send Message Commands
    def move_servo(self, id, angle) -> None:
        self.send_message(
                    "avr/pcm/set_servo_abs",
                    AvrPcmSetServoAbsPayload(servo= id, absolute= angle)
                )

    def send_action(self, action, payload = {}):
        self.send_message(
            'avr/fcm/actions',
            {'action': action, 'payload': payload}
        )
    def set_laser(self, state: bool) -> None:
        self.laser_on = state
        if state:
            topic = "avr/pcm/set_laser_on"
            payload = AvrPcmSetLaserOnPayload()
        else:
            topic = "avr/pcm/set_laser_off"
            payload = AvrPcmSetLaserOffPayload()
        self.send_message(topic, payload)

    def sound_laptop(self, id: int, loops: int = 1):
        self.send_message(
            'avr/autonomous/sound',
            {'id': id, 'loops': loops}
        )
    # ===============
    # Misc/Helper
    async def wait_for_event(self, event: str):
        logger.debug(f'Waiting for {event}')
        await self.waiting_events.get()[event].wait()
        logger.debug(f'Completed Event: {event}')
        self.waiting_events.set(self.waiting_events.get()[event].clear())
    
    def inch_to_m(self, num):
        return num/39.37
    

if __name__ == '__main__':
    box = Sandbox()
    
    #Create Threads
    targeting_thread = Thread(target=box.targeting)
    targeting_thread.daemon = True
    targeting_thread.start()
    
    CIC_thread = Thread(target=box.CIC)
    CIC_thread.daemon = True
    CIC_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous)
    autonomous_thread.daemon = True
    autonomous_thread.start()
    
    box.set_threads({'thermal': targeting_thread, 'cic': CIC_thread, 'auto': autonomous_thread})
    
    box.run()
