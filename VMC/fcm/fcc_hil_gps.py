import threading
import time

from bell.avr.mqtt.payloads import AvrFcmHilGpsStatsPayload, AvrFusionHilGpsPayload
from bell.avr.utils.decorators import try_except
from bell.avr.utils.timing import rate_limit
from fcc_mqtt import FCMMQTTModule
from loguru import logger
from pymavlink import mavutil


class HILGPSManager(FCMMQTTModule):
    def __init__(self) -> None:
        super().__init__()

        self.topic_map = {
            "avr/fusion/hil_gps": self.hilgps_msg_handler,
        }

        self.num_frames = 0

    @try_except()
    def heartbeat(self) -> None:
        while True:
            self.mavcon.mav.heartbeat_send(
                mavutil.mavlink.MAV_TYPE_ONBOARD_CONTROLLER,
                mavutil.mavlink.MAV_AUTOPILOT_INVALID,
                0,
                0,
                0,
            )
            time.sleep(1)

    @try_except()
    def run_non_blocking(self) -> None:
        """
        Set up a mavlink connection and kick off any tasks
        """

        # this NEEDS to be using UDP, TCP proved extremely unreliable
        self.mavcon: mavutil.mavudp = mavutil.mavlink_connection(
            "udpout:127.0.0.1:14541",
            source_system=143,
            source_component=190,
            dialect="bell",
        )

        heartbeat_thread = threading.Thread(target=self.heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        logger.debug("HIL_GPS: Waiting for Mavlink heartbeat")

        self.mavcon.wait_heartbeat()

        logger.success("HIL_GPS: Mavlink heartbeat received")

        rc_control_thread = threading.Thread(target=self.RC_magnet_control)
        rc_control_thread.daemon = True
        rc_control_thread.start()

        super().run_non_blocking()

    @try_except(reraise=True)
    def hilgps_msg_handler(self, payload: AvrFusionHilGpsPayload) -> None:
        """
        Handle a HIL_GPS message.
        """
        msg = self.mavcon.mav.hil_gps_heading_encode(  # type: ignore
            payload["time_usec"],
            payload["fix_type"],
            payload["lat"],
            payload["lon"],
            payload["alt"],
            payload["eph"],
            payload["epv"],
            payload["vel"],
            payload["vn"],
            payload["ve"],
            payload["vd"],
            payload["cog"],
            payload["satellites_visible"],
            payload["heading"],
        )
        # logger.debug(msg)
        self.mavcon.mav.send(msg)  # type: ignore
        self.num_frames += 1

        # publish stats every second
        rate_limit(
            lambda: self.send_message(
                "avr/fcm/hil_gps_stats",
                AvrFcmHilGpsStatsPayload(num_frames=self.num_frames),
            ),  # type: ignore
            frequency=1,
        )

    def RC_magnet_control(self):
        """Monitors RC channel 6 (currently bound to VrB, or the right knob)
        for significant changes and performs actions based on the channel value.

        This method continuously listens for RC_CHANNELS messages and monitors the value of channel 6.
        If the value changes significantly from the last logged value, it logs the new value.
        Additionally, it enables or disables a magnet based on the channel value relative to a default value.
        """
        DEFAULT_VAL = 1514  # value that the channel broadcasts when the knob is not being actuated (estimated)
        last_val = 0
        log_val_thres = 30
        action_val_thres = 100
        logger.info("Monitoring RC input in fcc_hil_gps.py")
        while True:
            # wait for a message
            msg = self.mavcon.recv_match(type="RC_CHANNELS", blocking=True)

            # if the message is not None, then we have a value for channel 6
            if msg:
                cur_value = msg.chan6_raw
            else:
                continue

            # log the value if it has changed significantly
            if cur_value > last_val + log_val_thres or cur_value < last_val - log_val_thres:
                logger.debug(f"Channel 6: {cur_value}")
                last_val = cur_value

            # if the value is above or below a certain threshold, then either enable or disable the magnet
            if cur_value > DEFAULT_VAL + action_val_thres:
                self.send_message("avr/pcm/set_magnet", {"enabled": True})
            elif cur_value < DEFAULT_VAL - action_val_thres:
                self.send_message("avr/pcm/set_magnet", {"enabled": False})


if __name__ == "__main__":
    gps = HILGPSManager()
    gps.run_non_blocking()
    while True:
        time.sleep(0.1)
