import multiprocessing
from queue import Empty, Full
import time
from face_tracker import FaceTracker
from system_states import EyelidState


def tracker_worker(current_angles, desired_angles, recognition_requests, recognition_results, face_detected, stop_event):
    try:

        # init ft
        ft = FaceTracker()

        print("tracker init successful")

        while not stop_event.is_set():
            # run this as fast as possible

            # get current positions
            with current_angles.get_lock():
                ud_curr, lr_curr = desired_angles[:]

            # now input this into per frame processing
            ud_desired, lr_desired, processed_frame, sph_coords = ft.run_single_track(ud_curr, lr_curr)

            # push to desired coordinates
            with desired_angles.get_lock():
                desired_angles[0] = ud_desired
                desired_angles[1] = lr_desired

            # initiate request for recognition
            if sph_coords:
                try:
                    recognition_requests.put_nowait(processed_frame)
                except Full:
                    # Drop this frame; recognition is already behind.
                    pass

            # if faces found, open eyes, otherwise close
            if sph_coords:
                face_detected.set()
            else:
                face_detected.clear()
            
            # check recognition results
            if not recognition_results.empty():
                face_names = recognition_results.get()
                for face_name in face_names:
                    print("Hello ", face_name, "!")

    except Exception as e: 
        print(e)
            

    finally:
        print("Tracker worker closing.")
        ft.picam2.stop()