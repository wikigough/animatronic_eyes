import multiprocessing
from servo_worker import servo_worker
from tracker_worker import tracker_worker
from recognition_worker import recognition_worker


class EyeBalls():

    def __init__(self):
        self.ctx = multiprocessing.get_context("spawn")

        # general stop event for all workers
        self.stop_event = self.ctx.Event()
        self.stop_event.clear()

        # desired angles from tracker -> servo worker
        """
            "d" = double precision float

            example use of writing: 

            with desired_angles.get_lock():
                desired_angles[0] = new_up_down
                desired_angles[1] = new_left_right

            example use of reading: 

            with desired_angles.get_lock():
                up_down, left_right = desired_angles[:]

        """
        self.desired_angles = self.ctx.Array("d", [90.0, 90.0], lock=True) # [up_down, left_right]
        self.current_angles = self.ctx.Array("d", [90.0, 90.0], lock=True) # [up_down, left_right] - no need for eyelids.
        self.face_detected = self.ctx.Event() # for telling various processes that there has been a face detected
        self.face_detected.clear()

        # define queues for recognition
        self.recognition_requests = self.ctx.Queue(maxsize=1)
        self.recognition_results = self.ctx.Queue(maxsize=5) # max five people allowed

        self.servo = self.ctx.Process(
            target=servo_worker,
            args=(self.current_angles, self.desired_angles, self.face_detected, self.stop_event),
        )

        self.tracker = self.ctx.Process(
            target=tracker_worker,
            args=(self.current_angles, self.desired_angles, self.recognition_requests, self.recognition_results, self.face_detected, self.stop_event),
        )

        self.recognizer = self.ctx.Process(
            target=recognition_worker,
            args=(self.recognition_requests, self.recognition_results, self.stop_event),
        )

    def run(self):
        try: 
            print("initalising all the workers...")
            self.servo.start()
            self.tracker.start()
            self.recognizer.start()
            while not self.stop_event.is_set():
                pass

        except KeyboardInterrupt:
            print("Stopping eyeballs.")

        finally:
            # sending "please stop!" to all the workers
            self.stop_event.set()

            # Join back to main process - Wait til the workers stop
            self.servo.join(timeout=5.0)
            self.tracker.join(timeout=5.0)
            self.recognizer.join(timeout=5.0)

            # last resort for hung process
            if self.servo.is_alive(): self.servo.terminate()
            if self.tracker.is_alive(): self.tracker.terminate()
            if self.recognizer.is_alive(): self.recognizer.terminate()

            # wait for forced termination to complete (if was necessary)
            self.servo.join()
            self.tracker.join()
            self.recognizer.join()

            # closing = no more values will be added frm this process
            self.recognition_requests.close()
            self.recognition_results.close()

            # Wait until the queue’s feeder thread has flushed its buffered values and exited.
            self.recognition_requests.join_thread()
            self.recognition_results.join_thread()



if __name__ == "__main__":
    eb = EyeBalls()
    eb.run() 