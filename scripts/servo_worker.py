from eye_driver import EyeDriver
import multiprocessing
from queue import Empty, Full
import time
from system_states import EyelidState

# define blink time bits
BLINK_TIME_THRESHOLD = 6.0 # seconds
BLINK_LENGTH = 0.2 # seconds
blink_time_tracker = time.monotonic()
blink_state = False

OPEN_LID_TIMEOUT = 20.0 # seconds
eyes_open_time_tracker = time.monotonic()

# other states - wide or squint - TODO
# wide_state = False
# squint_state = False


def _servo_eyelid_positions(eye_driver, ud, face_detected_bool):
    global blink_state, blink_time_tracker, eyes_open_time_tracker
    
    # default values for the eyelids.
    re_ul, re_ll, le_ul, le_ll = eye_driver.get_eyelid_angles_from_up_down(ud)

    if face_detected_bool:
        # reset eyes_open_time_tracker
        eyes_open_time_tracker = time.monotonic()

    if (time.monotonic() - eyes_open_time_tracker) <= OPEN_LID_TIMEOUT:

        # check if it's blink time and ovewrite default values if necessary
        if not blink_state:
            if (time.monotonic() - blink_time_tracker > BLINK_TIME_THRESHOLD):
                # yes it is - reset time tracker - kick off blinking
                blink_time_tracker = time.monotonic()
                blink_state = True

        if blink_state:
            
            if (time.monotonic() - blink_time_tracker > BLINK_LENGTH):
                # yes it is - reset time tracker - kick off blinking
                blink_time_tracker = time.monotonic()
                blink_state = False
            else:
                # get blink desired angles
                re_ul, re_ll, le_ul, le_ll = eye_driver.get_eyelid_closed_angles()
    else:
        re_ul, re_ll, le_ul, le_ll = eye_driver.get_eyelid_closed_angles()

    return re_ul, re_ll, le_ul, le_ll


def servo_worker(current_angles, desired_angles, face_detected, stop_event):
    
    eye_driver = None

    try:
        # define the EyeDriver class
        '''
            # eye definitions
            EYES_UP_DOWN            = 0
            EYES_LEFT_RIGHT         = 1
            RIGHT_EYE_UPPER_LID     = 2
            RIGHT_EYE_LOWER_LID     = 3
            LEFT_EYE_UPPER_LID      = 4
            LEFT_EYE_LOWER_LID      = 5
        '''
        eye_driver = EyeDriver()



        # wait for servos to move to their initial position
        time.sleep(0.1)

        print("servo init successful")

        # now let's enter the while loop! 
        while not stop_event.is_set():

            # push current angles into queue
            ud_curr, lr_curr, _, _, _, _ = eye_driver.get_current_angles()
            with current_angles.get_lock():
                current_angles[0] = ud_curr
                current_angles[1] = lr_curr

            # get desired locations for up/down and left/right only.
            with desired_angles.get_lock():
                ud, lr = desired_angles[:]

            # get eyelid positions
            re_ul, re_ll, le_ul, le_ll = _servo_eyelid_positions(eye_driver, ud, face_detected.is_set())

            # update desired angles
            eye_driver.update_desired_angles([ud, lr, re_ul, re_ll, le_ul, le_ll])

            # run pid loop
            eye_driver.all_servos_to_desired_angles()

            # set PID loop frequency
            time.sleep(0.02)

    except Exception as e: 
        print(e) 
        stop_event.set()
        raise


    finally: 
        eye_driver.reset_servos()
        print("servo worker closed.")


                

            


