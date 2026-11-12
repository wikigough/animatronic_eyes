import cv2
from threading import Thread, Event
from queue import Queue, Empty, Full
import face_recognition
import numpy as np
import pickle
from eye_driver import EyeDriver
from pathlib import Path
import time
import math

from picamera2 import Picamera2

ENCODINGS_PICKLE_PATH = Path("..") / "face_recognition" / "encodings.pickle"

class EyeMech():
    def __init__(self, pickle_path = ENCODINGS_PICKLE_PATH):
        print("initialising eyemech...")
        # load pre-trained encodings 
        print("[INFO] loading encodings...")
        with open(pickle_path, "rb") as f:
            data = pickle.loads(f.read())
        self.known_face_encodings = data["encodings"]
        self.known_face_names = data["names"]

        # init camera
        self.picam2 = Picamera2()
        self.raw_frame_width = 1920 # orig = 1920
        self.raw_frame_height = 1080 # orig = 1080
        self.picam2.configure(self.picam2.create_video_configuration(main={"format": 'XRGB8888', "size": (self.raw_frame_width, self.raw_frame_height)}))
        self.picam2.start()

        # initialise variables
        self.cv_scaler = 2
        self.face_location_x_max = int(self.raw_frame_width / self.cv_scaler)
        self.face_location_y_max = int(self.raw_frame_height / self.cv_scaler)
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0
        self.fov = math.pi * 120/180

        # init eyedriver
        self.eye_driver = EyeDriver()

        self._eye_driver_worker = 


    def _process_frame(self, frame):
        # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
        resized_frame = cv2.resize(frame, (0, 0), fx=(1/self.cv_scaler), fy=(1/self.cv_scaler))
        
        # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

        # Find all the faces and face encodings in the current frame of video
        self.face_locations = face_recognition.face_locations(rgb_resized_frame, number_of_times_to_upsample=0, model="hog")
        # self.face_encodings = face_recognition.face_encodings(rgb_resized_frame, self.face_locations, model='small')
        
        self.face_names = []
        """
        for face_encoding in self.face_encodings:
            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
            name = "Unknown"
            
            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self.known_face_names[best_match_index]
            self.face_names.append(name)

        """
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


    def run(self):
        try:
            while True:
                t0 = time.perf_counter()

                frame = self.picam2.capture_array()

                t1 = time.perf_counter()
                processed_frame = self._process_frame(frame)

                # push processed frame to face recognition if worker ready
                if self.recognition_ready.full():
                    self.recognition_ready.get()


                # print(self.face_names)
                t2 = time.perf_counter()

                centres = self._get_centres()
                face_sizes = self._get_face_sizes()
                # print(centres, face_sizes)
                sph_coords = self._get_spherical_coords(centres, face_sizes)

                t3 = time.perf_counter()

                # Calculate and update FPS
                current_fps = self._calculate_fps()
                print(current_fps)

                t4 = time.perf_counter()

                # move eyes left and right only for now
                if sph_coords:
                    r, theta, phi = sph_coords[0]
                    self.eye_driver.move_eyes_left_right(180 - (theta + 90) )
                    curr_up_down_angle = self.eye_driver.get_current_angles()[EyeDriver.EYES_UP_DOWN]
                    if abs(phi) > 10:
                        self.eye_driver.move_eyes_up_down(curr_up_down_angle + phi)

                t5 = time.perf_counter()

                print(
                    f"capture={(t1-t0)*1000:.0f} ms | "
                    f"vision={(t2-t1)*1000:.0f} ms | "
                    f"geometry={(t3-t2)*1000:.1f} ms | "
                    f"fps={(t4-t3)*1000:.0f} ms | "
                    f"motors={(t5-t4)*1000:.0f} ms"
                )
                    
        except KeyboardInterrupt:
            self.picam2.stop()


if __name__ == "__main__":
    eyemech = EyeMech()
    eyemech.run()





        