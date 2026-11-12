import multiprocessing
from queue import Empty, Full
import time
from face_tracker import FaceTracker


def tracker_worker(current_angles, desired_angles, recognition_requests, recognition_results, stop_event):
    try:

        # init ft
        ft = FaceTracker()

        print("tracker init successful")

        while not stop_event.is_set():
            # run this as fast as possible
            print("tracker  good")
            
            # get current positions
            with current_angles.get_lock():
                ud_curr, lr_curr = desired_angles[:]

            # now input this into per frame processing
            ud_desired, lr_desired = ft.run_single_track(ud_curr, lr_curr)

            # push to desired coordinates
            with desired_angles.get_lock():
                desired_angles[0] = ud_desired
                desired_angles[1] = lr_desired

    except Exception as e: 
        print(e)
            

    finally:
        print("Tracker worker closing.")
        ft.picam2.stop()