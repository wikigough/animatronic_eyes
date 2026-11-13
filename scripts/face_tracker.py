import cv2
import face_recognition
import numpy as np
import pickle
from eye_driver import EyeDriver
from pathlib import Path
import time
import math

from picamera2 import Picamera2

class FaceTracker():#
    '''
        top left origin in frame.
        (top, right, bottom, left)
         
        (0,0)
         
         +------------------------------+  → x
         |   +---top----+               |
         |   |          |               |
         |  left        right           |
         |   |          |               |
         |   +--bottom--+               |
         |                              |
         +------------------------------+
         
         ↓ y

        note output of face_recognition: 
            faces = face_recognition.face_locations(..)
            faces = [ (face_bounding_box0), (face_bounding_box1), (face_bounding_box2) ...]
            faces[n] = (top, right, bottom, left)
        
        output of yn detector:
            _, faces = self.yn_detector.detect(rgb_resized_frame)
            faces = [ [face0_data], [face1_data], ...]
            faces[n] = [
                left, top, right-left, bottom-top,   # Bounding box
                x, y,                                # Right eye centre
                x, y,                                # Left eye centre
                x, y,                                # Nose
                x, y,                                # Right mouth corner
                x, y,                                # Left mouth corner
                fraction                             # Confidence
            ]


    '''
    def __init__(self):

        # init camera
        self.picam2 = Picamera2()
        self.raw_frame_width = 1920 # orig = 1920
        self.raw_frame_height = 1080 # orig = 1080
        self.picam2.configure(self.picam2.create_video_configuration(main={"format": 'XRGB8888', "size": (self.raw_frame_width, self.raw_frame_height)}))
        self.picam2.start()

        # initialise variables
        self.cv_scaler = 2 # default = 2
        self.face_location_x_max = int(self.raw_frame_width / self.cv_scaler)
        self.face_location_y_max = int(self.raw_frame_height / self.cv_scaler)
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        self.fov = math.pi * 120/180

        # test only - YuNet
        SCRIPT_PATH = Path(__file__).resolve().parent
        MODEL_PATH = SCRIPT_PATH.parent / "tools" /  "face_detection_yunet_2023mar.onnx"
        self.yn_detector = cv2.FaceDetectorYN.create(
            str(MODEL_PATH),
            "",
            (int(self.raw_frame_width / self.cv_scaler), int(self.raw_frame_height / self.cv_scaler)),
            score_threshold=0.65, # default = 65
            nms_threshold=0.3,
            top_k=500,
        )

    def _process_frame(self, frame):
        # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
        resized_frame = cv2.resize(frame, (0, 0), fx=(1/self.cv_scaler), fy=(1/self.cv_scaler))

        # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

        # Find all the faces in the current frame of video
        # self.face_locations = face_recognition.face_locations(rgb_resized_frame, number_of_times_to_upsample=0, model="hog")

        # Find all the faces - using FaceDetectorYN as a test - dont return just yet
        _, faces = self.yn_detector.detect(rgb_resized_frame)

        # convert to face_recognition.face_locations() friendly output, as rest of code was written given this
        self.face_locations = []
        if faces is not None:
            for face in faces:
                # convert: [left, top, right-left, bottom-top] ->  (top, right, bottom, left)  # Bounding box
                left = round(face[0])
                top = round(face[1])
                right = round(face[2] + face[0])
                bottom = round(face [3] + face[1])
                self.face_locations.append( (top, right, bottom, left) )
                #print((top, right, bottom, left, face[14]))

        return rgb_resized_frame

    def _get_centres(self):
        # top left origin in frame.
        # (top, right, bottom, left)
        # 
        # (0,0)
        # 
        # +------------------------------+  → x
        # |   +---top----+               |
        # |   |          |               |
        # |  left        right           |
        # |   |          |               |
        # |   +--bottom--+               |
        # |                              |
        # +------------------------------+
        # 
        # ↓ y

        centres = []
        for face_location in self.face_locations:
            x = (face_location[1] - face_location[3])/2 + face_location[3]
            y = (face_location[2] - face_location[0])/2 + face_location[0]
            centres.append((x*self.cv_scaler, y*self.cv_scaler))

        return centres
    
    def _get_face_sizes(self):
        # top left origin in frame.
        # (top, right, bottom, left)
        # 
        # (0,0)
        # 
        # +------------------------------+  → x
        # |   +---top----+               |
        # |   |          |               |
        # |  left        right           |
        # |   |          |               |
        # |   +--bottom--+               |
        # |                              |
        # +------------------------------+
        # 
        # ↓ y

        face_sizes = []
        for face_location in self.face_locations:
            x_size = (face_location[1] - face_location[3])*self.cv_scaler
            y_size = (face_location[2] - face_location[0])*self.cv_scaler
            face_sizes.append(x_size * y_size)

        return face_sizes

    def _get_spherical_coords(self, centres, face_sizes):
        """
            See notes for derivation
        """
        sph_coords = []
        for i in range(0, len(self.face_locations)):
            x_c, y_c = centres[i] # pixel location 

            # depth
            face_area_pixels = face_sizes[i] # pixels^2
            face_area_cm2 = 300 # rough face bounding box area in cm2
            fx = self.raw_frame_width / (2 * math.tan(self.fov / 2))
            depth = fx * math.sqrt(face_area_cm2 / face_area_pixels)

            # r
            fy = fx # square pixels
            nx = (x_c - self.raw_frame_width / 2) / fx # normalised
            ny = (y_c - self.raw_frame_height / 2) / fy # normalised
            x_cm = depth * nx
            y_cm = depth * ny
            r = math.sqrt(depth*depth + x_cm*x_cm + y_cm*y_cm)

            # theta
            theta = math.degrees(math.atan2(x_cm, depth))

            # phi
            phi = math.degrees(math.atan2(-y_cm, math.hypot(x_cm, depth)))

            sph_coords.append( (r, theta, phi) )

        return sph_coords


    def _calculate_fps(self):
        self.frame_count += 1
        elapsed_time = time.time() - self.start_time
        if elapsed_time > 1:
            self.fps = self.frame_count / elapsed_time
            self.frame_count = 0
            self.start_time = time.time()
        return self.fps

    def run_single_track(self, ud_curr, lr_curr):
        # set default return values - same as the ones inputted
        ud = ud_curr
        lr = lr_curr

        # capture an image using picam2
        frame = self.picam2.capture_array()

        # process frame - this bit takes a while
        processed_frame = self._process_frame(frame)

        # get spherical coordinates of all the faces
        centres = self._get_centres()
        face_sizes = self._get_face_sizes()
        sph_coords = self._get_spherical_coords(centres, face_sizes)

        # TODO: run face path tracker

        # optional: get current fps
        current_fps = self._calculate_fps()

        if sph_coords:
            # Just use the first one on the list - TODO: update with facial recogntiion results
            r, theta, phi = sph_coords[0]

            # desired angles
            lr = 180 - (theta + 90)
            ud = ud_curr + phi

        return ud, lr, processed_frame, sph_coords


if __name__ == "__main__":
    face_tracker = FaceTracker()





        