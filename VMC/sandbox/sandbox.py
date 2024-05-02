import base64, cv2, time, asyncio
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

        self.is_armed: bool = False
        self.pause: bool = False
        self.autonomous: bool = False
        self.auto_target: bool = False
        self.CIC_loop: bool = True
        self.show_status: bool = True
        self.recon: bool = False
        self.fcm_init: bool = False

        self.thermalAutoAim: bool = False # Since there is no application for the thermal targeting thread, this boolean prevents it from starting
        
        self.position: list = [0, 0, 0]
        self.start_pos: tuple = (180, 50, 0)
        
        self.building_loc: dict[str, tuple[int, int, int]] = {'Building 0': (404, 120, 55), 'Building 1': (404, 45, 55), 'Building 2': (356, 177, 69), 'Building 3': (356, 53, 69), 'Building 4': (310, 125, 121), 'Building 5': (310, 50, 121)}
        self.landing_pads: dict[str, tuple[int, int, int]] = {'ground': (180, 50, 12), 'building': (231, 85, 42)}

        self.building_drops: dict[int, bool] = {0: False, 1: False, 2: False, 3: False, 4: False, 6: False}
        
        self.thermal_grid: list[list[int]] = [[0 for _ in range(8)] for _ in range(8)]
        self.target_range: tuple[int, int] = (30, 40)
        self.targeting_step: int = 7
        self.laser_on: bool = False

        self.flightState: str = "UNKNOWN"
  
        self.sanity: str = 'Gone'
        self.do_pathfinding: bool = False
        self.col_test = collision_dectector((472, 170, 200), 17.3622)
        self.waiting_events = ContextVar('test', default={'landed_state_in_air_event': asyncio.Event(), 'landed_state_on_ground_event': asyncio.Event(), 'goto_complete_event': asyncio.Event()})
        
        self.april_tags: list = []
        self.tag_flashing: bool = False
        self.normal_color: tuple[int, int, int, int] = [255, 78, 205, 196] # wrgb
        self.flash_color: tuple[int, int, int, int] = [255, 255, 0, 0] # wrgb
        
        self.threads: dict
        
        # Only turn on if using home field
        homefield_test: bool = False
        if homefield_test:
            self.start_pos = (231, 85, 52)
            self.building_loc = {building: tuple(list(loc)[2]*.75) for building, loc in self.building_loc.items()}
        
        
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
        
    def handle_user_in(self, payload: dict) -> None:
        try:
            self.pause = payload['pause']
        except:
            pass
        
    def handle_thermal_tracker(self, payload: dict) -> None:
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
    
    def handle_thermal_range(self, payload: dict) -> None:
        self.target_range = payload['range'][0:2]
        logger.debug(self.target_range)
        self.targeting_step = int(payload['range'][2])
        
    def handle_pos(self, payload: AvrFusionPositionNedPayload):
        # NOTE Check if direction is based on drone start or global
        self.position = [payload['n'], payload['e'], payload['d']]
        
    def handle_dev(self, payload: dict):
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
            self.sound_laptop("sound_1")
            
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
    def targeting(self) -> None: # Currently useless as there is no application for it, still works though.
        logger.debug('Thermal Tracking Thread: Online')
        turret_angles = [1450, 1450]
        while True:
            if not self.auto_target:
                if self.laser_on:
                    self.set_laser(False)
                continue
            if not self.laser_on:
                self.set_laser(True)
                
            # Create mask of pixels above thermal threshold
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
            heat_center = [float(x) for x in t[s.argmax()][::-1]]
            move_range = [15, -15]
            m = interp1d([0, 8], move_range)
            logger.debug(heat_center)
            
            # Couldn't figure out the math to move the gimbal to the right position
            # so this justs moves reactily in small steps, it also sucks ass.
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
        logger.debug('Command, Information, & Control Thread: Online')
        status_thread = Thread(target=self.status)
        status_thread.daemon = True
        status_thread.start()
        light_init = False
        has_gotten_hot = False
        found_high_tag = False
        while True:
            if not self.CIC_loop:
                continue
            
            # Turns lights on only after fcm has been initialized
            if self.fcm_init and not light_init:
                self.sound_laptop("startup",".mp3") # Play startup sound
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color))
                for i in range (5, 8):
                    self.send_message(
                    "avr/pcm/set_servo_open_close",
                    AvrPcmSetServoOpenClosePayload(servo= i, action= 'open')
                    )
                light_init = True
                
            # Flash lights if the april tag on the highbuilding during recon is found
            if not found_high_tag and next((tag for tag in self.april_tags if tag['id'] == 0), None):
                self.tag_flashing = True
                logger.debug('Tag found')
                for i in range(3):
                    #self.send_message('avr/pcm/set_temp_color', {'wrgb': self.flash_color, 'duration': 0.3})
                    self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.flash_color))
                    time.sleep(.3)
                    self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=[0]*4))
                self.tag_flashing = False
                found_high_tag = True
                self.send_message('avr/pcm/set_base_color', AvrPcmSetBaseColorPayload(wrgb=self.normal_color))
            
            # Warn pilot and flash lights if the hotspot is detected
            if not has_gotten_hot and np.any(np.array(self.thermal_grid) >= 27):
                for i in range(10):
                    logger.debug('HOT SPOT DETECTED. GO UP')
                self.sound_laptop("sound_1")
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
        """ Shows the stats of the threads.
        """
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
    
    def Autonomous(self): # What is this, headache city?
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

            # Look for april tag 1 and flash led if its found.
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
    # BEWARE! None of this works so proceed with caution
    
    def move(self, pos: tuple, heading: float = 0, pathing: bool = False) -> None:
        """ Move the AVR to a specified position on the field

        Args:
            pos (tuple): Absolute position on the field, in inches, as (x: fwd, y: right, z: up)
            heading (float, optional): Heading that the drone will face while moving (?) as a decimal (?). Defaults to 0.
            pathing (bool, optional): If the AVR will attempt to path around buildings (?). Defaults to False.
        """
        if not pathing or not self.col_test.path_check(self.position, pos):
            relative_pos = [0, 0, 0]
            for i in range(3):
                # Get the relative coords of the destination by adding the absolute position to the starting position
                relative_pos[i] = self.inchesToMeters(pos[i]) + self.start_pos[i]
            # Reverse the value of the Z coord since the MQTT syntax is <dis_down> for some reason
            relative_pos[2] *= -1
            # Report the destination (No clue where this prints to) and send the command
            logger.debug(f'NED: {relative_pos}')
            self.send_action('goto_location_ned', {'n': relative_pos[0], 'e': relative_pos[1], 'd': relative_pos[2], 'heading': heading})
        else: # Pathfinding process
            if self.do_pathfinding:
                # Paths points along the way to the target destination (?)
                pathed_positions = self.col_test.path_find(self.position, pos)
                for p_pos in pathed_positions:
                    self.move(self.position, p_pos)
                    time.sleep(.5)
            else: # Path obstructed (?)
                logger.debug(f'[({self.position})->({pos})] Path obstructed. Movment command canceled.')
                
        """ while not self.move_complete:
            logger.debug('Waiting for move confirm', self.move_complete)
        self.move_complete = False """
    
    def takeoff(self, alt: float = 39.3701) -> None:
        """ Tell the AVR to takeoff

        Args:
            alt (float, optional): Height that the AVR will takeoff to in inches. Defaults to 39.3701 (1 meter)
        """
        self.send_action('takeoff', {'alt': round(self.inchesToMeters(alt), 1)})
    
    def land(self) -> None:
        """ Land the AVR
        """
        #self.move(self.landing_pads[pad])
        self.send_action('land')


    # ================================
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

    def sound_laptop(self, fileName: str, ext: str = ".WAV", loops: int = 1):
        """Play a specified audio file from the <GUI/assets/sounds> directory on all connected laptops

        Args:
            fileName (str): The name of the file.
            ext (str): The extension of the file. Defaults to ".WAV"
            loops (int, optional): Number of loops. Currently has no effect. Defaults to 1.
        """
        # Plays the sound by publishing the sound topic with the file info as payload, which is processed & handled in autonomy.py
        self.send_message(
            'avr/autonomous/sound',
            {'fileName': fileName, 'ext': ext, 'loops': loops}
        )
    
    
    # ================================
    # Misc/Helper commands
    async def wait_for_event(self, event: str):
        logger.debug(f'Waiting for {event}')
        await self.waiting_events.get()[event].wait()
        logger.debug(f'Completed Event: {event}')
        self.waiting_events.set(self.waiting_events.get()[event].clear())
    
    # From Quentin: Bell gives us field dimensions in inches then programs the drone to use meters because fuck you
    def inchesToMeters(self, inches: float) -> float:
        """ Converts inches to meters
        
        Args:
            inches (float): Self explanatory, distance in inches

        Returns:
            float: Distance in meters
        """
        return inches/39.37
    

if __name__ == '__main__':
    box = Sandbox()
    
    # Create Threads
    targeting_thread = Thread(target=box.targeting, daemon=True)
    if box.thermalAutoAim: targeting_thread.start()
    
    CIC_thread = Thread(target=box.CIC, daemon=True)
    CIC_thread.start()
    
    autonomous_thread = Thread(target=box.Autonomous, daemon=True)
    autonomous_thread.start()
    
    box.set_threads({'thermal': targeting_thread, 'cic': CIC_thread, 'auto': autonomous_thread})
    
    box.run()
