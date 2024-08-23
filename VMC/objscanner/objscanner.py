import cv2, os, time

from bell.avr.mqtt.client import MQTTModule
from loguru import logger


class ObjectScanner(MQTTModule):
    def __init__(self) -> None:
        super().__init__()

        self.topic_map = {
            'avr/objscanner/params': self.handle_params
        }

        self.threshold: float = 0.5 # Minimum scanning confidence required to report the target and its location
        self.scales: list[float] = [.5, .4, .3, .2, .1] # All scales that will be searched on
        self.scanning_state: int = 0 # Value determines the state of the object scanner. 0 is no scanning, 1 is scan for objects and report relevant data, 2 is automatically move towards detected objects

        logger.info("objscanner initialized")

    def handle_params(self, payload: dict):
        """Handle parameter update messages
        """
        if "state" in payload.keys():
            self.scanning_state = payload["state"]
            logger.debug(f"objscanner params updated || scanning_state: {self.scanning_state}")

    def load_images_from_directory(self, directory_path) -> tuple[list, list]:
        image_files = []
        image_names = []
        for filename in os.listdir(directory_path):
            if filename.endswith(".jpg") or filename.endswith(".png"):
                img = cv2.imread(os.path.join(directory_path, filename))
                if img is not None:
                    image_files.append(img)
                    image_names.append(filename)
        return image_files, image_names

    def match_target_in_frame(self, frame, target_images):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        best_match = None
        best_confidence = 0
        best_scale = 1.0
        best_image_name = None

        for target_image, image_name in target_images:
            gray_target = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)

            for scale in self.scales:
                resized_target = cv2.resize(gray_target, (0, 0), fx=scale, fy=scale)
                res = cv2.matchTemplate(gray_frame, resized_target, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if max_val > best_confidence and max_val >= self.threshold:
                    best_match = max_loc
                    best_confidence = max_val
                    best_scale = scale
                    best_image_name = image_name

        if best_match is not None:
            return best_match, best_confidence, best_scale, best_image_name
        return None, None, None, None

    def estimate_distances(self, frame, target_position, scale, focal_length=800, real_target_width=10, real_target_height=10) -> tuple[int, int]:
        # Frame center coordinates
        frame_center_x = frame.shape[1] // 2
        frame_center_y = frame.shape[0] // 2

        # Target center coordinates
        target_center_x = int(target_position[0] + (real_target_width * scale / 2))
        target_center_y = int(target_position[1] + (real_target_height * scale / 2))

        # Horizontal distance (right direction)
        horizontal_distance = (target_center_x - frame_center_x) * (real_target_width / focal_length)

        # Vertical distance (forward direction)
        vertical_distance = (frame_center_y - target_center_y) * (real_target_height / focal_length)

        return horizontal_distance, vertical_distance

    def cap_process(self, use_main_pipeline: bool = True):
        """Capture, process, report, and act on data from the CSI camera. Basically the main method of the object scanner.

        NOTE: This function is blocking, assuming the VideoCapture object initialized successfully and the initial frame is captured successfully
        """
        capture_confirmed: bool = False

        # GStreamer pipeline for the camera
        pipeline = "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720,format=NV12, framerate=15/1 ! nvvidconv ! video/x-raw,format=BGRx !  videoconvert ! videorate ! video/x-raw,format=BGR,framerate=5/1 ! appsink"
        alt_pipeline = "nvarguscamerasrc ! video/x-raw(memory:NVMM), width=1280, height=720,format=NV12, framerate=60/1 ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! videorate ! video/x-raw,format=BGR,framerate=30/1,width=1280,height=720 ! appsink"
        
        if use_main_pipeline:
            capture = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        else:
            capture = cv2.VideoCapture(alt_pipeline)

        logger.debug("VideoCapture initialized successfully")

        # Load all target images from a directory (e.g., multiple helipads)
        target_images, image_names = self.load_images_from_directory("targets")
        target_images_with_names = list(zip(target_images, image_names))

        # Read an initial test frame
        ret, frame = capture.read()
        if not ret:
            logger.error("Failed to capture initial frame, pipeline might be incorrect")
            capture.release()
            return
        logger.debug("Initial frame captured successfully")

        while capture.isOpened():
            ret, frame = capture.read()
            if not ret:
                logger.error("Could not read capture from CSI camera... Retrying")
                time.sleep(5)
                continue
            elif not capture_confirmed:
                logger.debug("CSI Camera capture confirmed")
                capture_confirmed = True

            if self.scanning_state == 0:
                continue

            # Find the best matching target in the frame
            target_position, match_confidence, best_scale, best_image_name = self.match_target_in_frame(frame, target_images_with_names)
            if target_position is not None:
                # Estimate horizontal distance
                x, y = self.estimate_distances(frame, target_position, best_scale)

                logger.debug(f"Best match found: {best_image_name} with confidence {match_confidence:.2f} at scale {best_scale:.2f}")
                logger.debug(f"Estimated horizontal distance from the target: ({x:.2f}, {y:.2f}) units")
                
                self.send_message('avr/objscanner/scan_report', {"name": best_image_name, "X": x, "Y":y})

                if self.scanning_state == 2:
                    self.send_message('avr/fcm/actions', {'action':  "goto_location_ned", 'payload': {'n': x, 'e': y, 'd': 0, 'heading': 0, 'rel': True}})

                time.sleep(1)

        logger.error("VideoCapture initialization failed")
        capture.release()

    def run(self) -> None:
        super().run_non_blocking()
        self.cap_process()
        logger.error("Capture Process error, trying again with alternate pipeline...")
        self.cap_process(False)
        logger.error("Capture Process error, this container will now exit & restart")


if __name__ == "__main__":
    try:
        objscanner = ObjectScanner()
        objscanner.run()
    except Exception as e:
        logger.exception(e)