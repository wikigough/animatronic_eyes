import cv2
from threading import Thread
import face_recognition
import numpy as np
import pickle
from eye_driver import EyeDriver
from pathlib import Path
import time

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
        self.picam2.configure(self.picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (1920, 1080)}))
        self.picam2.start()

        # initialise variables
        self.cv_scaler = 4
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.frame_count = 0
        self.start_time = time.time()
        self.fps = 0

    def _process_frame(self, frame):
        # Resize the frame using cv_scaler to increase performance (less pixels processed, less time spent)
        resized_frame = cv2.resize(frame, (0, 0), fx=(1/self.cv_scaler), fy=(1/self.cv_scaler))
        
        # Convert the image from BGR to RGB colour space, the facial recognition library uses RGB, OpenCV uses BGR
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
        
        # Find all the faces and face encodings in the current frame of video
        self.face_locations = face_recognition.face_locations(rgb_resized_frame)
        #self.face_encodings = face_recognition.face_encodings(rgb_resized_frame, self.face_locations, model='small')
        
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
        return frame

    def _draw_results(self, frame):
        # Display the results
        for (top, right, bottom, left), name in zip(self.face_locations, self.face_names):
            # Scale back up face locations since the frame we detected in was scaled
            top *= self.cv_scaler
            right *= self.cv_scaler
            bottom *= self.cv_scaler
            left *= self.cv_scaler
            
            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (244, 42, 3), 3)
            
            # Draw a label with a name below the face
            cv2.rectangle(frame, (left -3, top - 35), (right+3, top), (244, 42, 3), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, top - 6), font, 1.0, (255, 255, 255), 1)
        
        return frame

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
                frame = self.picam2.capture_array()

                processed_frame = self._process_frame(frame)
                print(self.face_locations)
                #print(self.face_encodings)
                #print(self.face_names)

                # Calculate and update FPS
                current_fps = self._calculate_fps()
                print(current_fps)
                    
                # Attach FPS counter to the text and boxes
                #cv2.putText(display_frame, f"FPS: {current_fps:.1f}", (display_frame.shape[1] - 150, 30), 
                #            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    
                # Display everything over the video feed.
                #cv2.imshow('Video', display_frame)
                    
                # Break the loop and stop the script if 'q' is pressed
                #if cv2.waitKey(1) == ord("q"):
                #    break
        except KeyboardInterrupt:
            # By breaking the loop we run this code here which closes everything
            self.picam2.stop()

if __name__ == "__main__":
    eyemech = EyeMech()
    eyemech.run()





        