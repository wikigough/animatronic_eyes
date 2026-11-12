import pickle
import face_recognition
import numpy as np
from pathlib import Path
from queue import Empty, Full

def recognition_worker(recognition_requests, recognition_results, stop_event):
    try:
        # load facial recognition data
        ENCODINGS_PICKLE_PATH = Path("..") / "face_recognition" / "encodings.pickle"
        with open(ENCODINGS_PICKLE_PATH, "rb") as f:
            data = pickle.loads(f.read())

        known_face_encodings = data["encodings"]
        known_face_names = data["names"]

        print("recognition init successful")

        while not stop_event.is_set():
            # wait for some data to some through
            try:
                processed_frame = recognition_requests.get(timeout=0.1)
            except Empty:
                continue

            print("Got data!")
            # Find all the faces and face encodings in the frame of video that has been sent through
            face_locations = face_recognition.face_locations(processed_frame, number_of_times_to_upsample=0, model="hog")
            face_encodings = face_recognition.face_encodings(processed_frame, face_locations, model='small')

            # now compare with known faces
            face_names = []
            for face_encoding in face_encodings:
                # See if the face is a match for the known face(s)
                matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
                name = "Unknown"
                
                # Use the known face with the smallest distance to the new face
                face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
                face_names.append(name)

            # dump names into the queue
            recognition_results.put(face_names)
    
    finally:
        print("Recognition worker closing.")
        