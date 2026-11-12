# servo.py
from adafruit_servokit import ServoKit
from adafruit_ina228 import INA228
import time
import json
import board
from busio import I2C

class EyeDriver():

    # eye definitions
    EYES_UP_DOWN            = 0
    EYES_LEFT_RIGHT         = 1
    RIGHT_EYE_UPPER_LID     = 2
    RIGHT_EYE_LOWER_LID     = 3
    LEFT_EYE_UPPER_LID      = 4
    LEFT_EYE_LOWER_LID      = 5

    _eyes = {
        EYES_UP_DOWN,
        EYES_LEFT_RIGHT,
        RIGHT_EYE_UPPER_LID,
        RIGHT_EYE_LOWER_LID,
        LEFT_EYE_UPPER_LID,
        LEFT_EYE_LOWER_LID
    }


    def __init__(self, json_file = "limits.json"):
        # assign i2c
        self.i2c = board.I2C()

        # initialise ServoKit instance
        self.kit = ServoKit(channels=16, i2c = self.i2c, address = 0x40, frequency=50)

        # initialise ina228 for calibration purposes.
        self.ina228 = INA228(self.i2c, address = 0x41)

        # load json file
        self.json_data = self.read_json(json_file)

        # store current servo state - fill with dummy values for now
        self.servo_current_angle = [90, 90, 90, 90, 90, 90]

        # storing desired angles - filled with dummy values for now
        self.servo_desired_angle = [90, 90, 90, 90, 90, 90]

        # load current servo limits.
        self.reset_servos()
        
        # define pid constants and trackers
        self.kp = 0.4
        self.ki = 0.05
        self.kd = 0.0
        self.servo_integral = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.servo_previous_error = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.servo_last_time = [None, None, None, None, None, None]

    @staticmethod
    def read_json(json_file):
        f = open(json_file, 'r')
        return json.load(f)
    
    def reset_servos(self):

        self.servo_to_angle(self.EYES_UP_DOWN, self.json_data["eyes"][self.EYES_UP_DOWN]["mid"])
        self.servo_to_angle(self.EYES_LEFT_RIGHT, self.json_data["eyes"][self.EYES_LEFT_RIGHT]["mid"])
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["mid"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["mid"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["mid"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["mid"])

    def get_min_angle(self, eye_id):
        return self.json_data["eyes"][eye_id]["min"]
 
    def get_mid_angle(self, eye_id):
        return self.json_data["eyes"][eye_id]["mid"]

    def get_max_angle(self, eye_id):
        return self.json_data["eyes"][eye_id]["max"]

    def get_eyelid_closed_angles(self):
        re_ul = self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["min"]
        re_ll = self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["max"]
        le_ul = self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["max"]
        le_ll = self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["min"]
        return re_ul, re_ll, le_ul, le_ll

    def get_eyelid_angles_from_up_down(self, up_down_angle):
        re_ul = up_down_angle
        re_ll = up_down_angle
        le_ul = 180 - up_down_angle
        le_ll = 180 - up_down_angle
        return re_ul, re_ll, le_ul, le_ll

   
    def move_eyes_left_right(self, angle: int):
        self.servo_to_angle(self.EYES_LEFT_RIGHT, angle)

    def move_eyes_up_down(self, angle: int):
        self.servo_to_angle(self.EYES_UP_DOWN, angle)
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, angle)
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, angle)
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, 180-angle)
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, 180-angle)

    
    def servo_to_angle(self, eye_id: int, angle: int):
        '''
            Simple function without PID control, just moving the servo to a desired angle straight away.
            Used for testing and debugging and within the PID loop.
        '''
        if 0 <= eye_id <= 5:
            if (angle <= self.json_data["eyes"][eye_id]["max"]) and (angle >= self.json_data["eyes"][eye_id]["min"]):
                self.kit.servo[eye_id].angle = angle
                self.servo_current_angle[eye_id] = angle

    def servo_to_angle_pid(self, eye_id: int, target_angle: int) -> bool:
        # call this function repeatedly! 
        # Returns true when target is reached.

        # firstly check if correct eye_id has been entered
        if 0 <= eye_id <= 5:

            # make sure the target angle is bound between min and max of the eye_ids before continuing further
            target_angle = max(self.json_data["eyes"][eye_id]["min"], min(self.json_data["eyes"][eye_id]["max"], target_angle))

            # get error value
            current_angle = self.servo_current_angle[eye_id]
            error = target_angle - current_angle

            # get time and update time tracker
            now = time.monotonic()
            last_time = self.servo_last_time[eye_id]
            self.servo_last_time[eye_id] = now

            # if we just started, skip the rest of the loop and return when we can calculate a dt value.
            if last_time is None:
                self.servo_previous_error[eye_id] = error
                return False

            # get dt - also limit unusually large time gaps from errors etc
            dt = min(now - last_time, 0.1)
            if dt <= 0:
                return False


            # Stop close to the target and clear accumulated integral.
            if abs(error) < 0.5:
                # reset
                self.servo_integral[eye_id] = 0.0
                self.servo_last_time[eye_id] = None
                self.servo_previous_error[eye_id] = 0.0
                return True

             # Integral term with anti-windup.
            integral = self.servo_integral[eye_id] + error * dt
            integral = max(-30.0, min(30.0, integral))
            self.servo_integral[eye_id] = integral

            # Derivative: rate at which the error is changing.
            previous_error = self.servo_previous_error[eye_id]
            derivative = (error - previous_error) / dt
            self.servo_previous_error[eye_id] = error

            correction = self.kp * error + self.ki * integral +self.kd * derivative

            # Limit how far the servo can move per update.
            correction = max(-10.0, min(10.0, correction))
            commanded_angle = current_angle + correction
            commanded_angle = max(self.json_data["eyes"][eye_id]["min"], min(self.json_data["eyes"][eye_id]["max"], commanded_angle))
        
            # update current angle - this updates the current angle too. 
            self.servo_to_angle(eye_id, commanded_angle)

            return False

    def all_servos_to_desired_angles(self):
        # TODO: add timeout

        done_ud    = self.servo_to_angle_pid(self.EYES_UP_DOWN, self.servo_desired_angle[self.EYES_UP_DOWN])
        done_lr    = self.servo_to_angle_pid(self.EYES_LEFT_RIGHT, self.servo_desired_angle[self.EYES_LEFT_RIGHT])
        done_re_ul = self.servo_to_angle_pid(self.RIGHT_EYE_UPPER_LID, self.servo_desired_angle[self.RIGHT_EYE_UPPER_LID])
        done_re_ll = self.servo_to_angle_pid(self.RIGHT_EYE_LOWER_LID, self.servo_desired_angle[self.RIGHT_EYE_LOWER_LID])
        done_le_ul = self.servo_to_angle_pid(self.LEFT_EYE_UPPER_LID, self.servo_desired_angle[self.LEFT_EYE_UPPER_LID])
        done_le_ll = self.servo_to_angle_pid(self.LEFT_EYE_LOWER_LID, self.servo_desired_angle[self.LEFT_EYE_LOWER_LID])

        done = done_ud and done_lr and done_re_ul and done_re_ll and done_le_ul and done_le_ll

        return done

    def get_current_angles(self):
        return self.servo_current_angle

    def update_desired_angles(self, desired_angles: list):
        self.servo_desired_angle = desired_angles

    def read_ina(self):
        print(f"Current: {self.ina228.current:.2f} mA")
        print(f"Bus Voltage: {self.ina228.bus_voltage:.2f} V")
        print(f"Shunt Voltage: {self.ina228.shunt_voltage*1000:.2f} mV")
        print(f"Power: {self.ina228.power:.2f} mW")
        print(f"Energy: {self.ina228.energy:.2f} J")
        print(f"Temperature: {self.ina228.die_temperature:.2f} °C")

    ## TEST FUNCTIONS
    def test_blink2(self):
        # get the current position of the eyelids - for safekeeping
        re_ul_open = self.servo_current_angle[self.RIGHT_EYE_UPPER_LID]
        re_ll_open = self.servo_current_angle[self.RIGHT_EYE_LOWER_LID]
        le_ul_open = self.servo_current_angle[self.LEFT_EYE_UPPER_LID]
        le_ll_open = self.servo_current_angle[self.LEFT_EYE_LOWER_LID]

        # closing movement commence! Note that eyes just blink to the midpoint...
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["min"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["min"])

        time.sleep(0.15)

        # opening - commence!
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, re_ul_open)
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, re_ll_open)
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, le_ul_open)
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, le_ll_open)

    def test_blink(self):
        # close eyes
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["min"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["min"])

        time.sleep(0.15)
        # open eyes
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["mid"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["mid"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["mid"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["mid"])

    def test_look_right(self):
        self.servo_to_angle(self.EYES_LEFT_RIGHT, self.json_data["eyes"][self.EYES_LEFT_RIGHT]["min"])

    def test_look_left(self):
        self.servo_to_angle(self.EYES_LEFT_RIGHT, self.json_data["eyes"][self.EYES_LEFT_RIGHT]["max"])

    def test_look_up(self):

        self.servo_to_angle(self.EYES_UP_DOWN, self.json_data["eyes"][self.EYES_UP_DOWN]["max"])
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["max"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["min"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["min"])
    
    def test_look_down(self):

        self.servo_to_angle(self.EYES_UP_DOWN, self.json_data["eyes"][self.EYES_UP_DOWN]["min"])
        self.servo_to_angle(self.RIGHT_EYE_UPPER_LID, self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["min"])
        self.servo_to_angle(self.RIGHT_EYE_LOWER_LID, self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["min"])
        self.servo_to_angle(self.LEFT_EYE_UPPER_LID, self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["max"])
        self.servo_to_angle(self.LEFT_EYE_LOWER_LID, self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["max"])
            


if __name__ == "__main__":
    eyes = EyeDriver()
    print("Welcome to EYEBALLS. Commands:")
    print("  <servo_id> <angle>   Example: 0 70")
    print("  reset")
    print("  quit")
    print("  ina")
    print("  blink")
    print("  lr")
    print("  ll")
    print("  lu")
    print("  ld")
    print("  angles")
    print("  all")

    
    

    try:
        blink_time_tracker = time.monotonic() # in seconds (float)
        eyes.servo_desired_angle = [50, 50, 50, 50, 50, 50]

        while True:

            if time.monotonic() - blink_time_tracker > 3.0:
                blink_time_tracker = time.monotonic()
                eyes.test_blink2()

            command = input("eyes> ").strip().lower() # blocking

            if command in ("quit", "exit"):
                break

            if command == "reset":
                eyes.reset_servos()
                print("Servos reset to 90 degrees")
                continue

            if command == "ina":
                eyes.read_ina()
                continue

            if command == "blink":
                eyes.test_blink2()
                continue

            if command == "lr":
                eyes.test_look_right()
                continue

            if command == "ll":
                eyes.test_look_left()
                continue

            if command == "lu":
                eyes.test_look_up()
                continue

            if command  == "ld":
                eyes.test_look_down()
                continue

            if command  == "angles":
                print(eyes.get_current_angles())
                continue

            if command  == "all":
                eyes.all_servos_to_desired_angles()
                continue

            try:
                eye_id_text, angle_text = command.split()

                eye_id = int(eye_id_text)
                angle = int(angle_text)

                done = False
                while not done:
                    done = eyes.servo_to_angle_pid(eye_id, angle)
                    time.sleep(0.01)
                    

                print(f"Servo {eye_id} moved to {angle} degrees")

            except ValueError:
                print("Enter: <servo_id> <angle>, for example: 0 70")

    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C")

    finally:
        eyes.reset_servos()
        time.sleep(1)




    



