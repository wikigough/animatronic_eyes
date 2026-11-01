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

        # load current servo limits.
        self.reset_servos()
        
        # calibrate servos
        # self.


    def reset_servos(self):
        self.kit.servo[self.EYES_UP_DOWN].angle = self.json_data["eyes"][self.EYES_UP_DOWN]["mid"]
        self.kit.servo[self.EYES_LEFT_RIGHT].angle = self.json_data["eyes"][self.EYES_LEFT_RIGHT]["mid"]
        self.kit.servo[self.RIGHT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["mid"]
        self.kit.servo[self.RIGHT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["mid"]
        self.kit.servo[self.LEFT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["mid"]
        self.kit.servo[self.LEFT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["mid"]

    def servo_to_angle(self, eye_id: int, angle: int):
        if 0 <= eye_id <= 5:
            if (angle < 180) and (angle > 0):
                self.kit.servo[eye_id].angle = angle

    def read_ina(self):
        print(f"Current: {self.ina228.current:.2f} mA")
        print(f"Bus Voltage: {self.ina228.bus_voltage:.2f} V")
        print(f"Shunt Voltage: {self.ina228.shunt_voltage*1000:.2f} mV")
        print(f"Power: {self.ina228.power:.2f} mW")
        print(f"Energy: {self.ina228.energy:.2f} J")
        print(f"Temperature: {self.ina228.die_temperature:.2f} °C")

    def read_json(self, json_file):
        f = open(json_file, 'r')
        return json.load(f)
        
    def blink(self):
        # close eyes
        self.kit.servo[self.RIGHT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["min"]
        self.kit.servo[self.RIGHT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["max"]
        self.kit.servo[self.LEFT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["max"]
        self.kit.servo[self.LEFT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["min"]

        time.sleep(1)
        # open eyes
        self.kit.servo[self.RIGHT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_UPPER_LID]["mid"]
        self.kit.servo[self.RIGHT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.RIGHT_EYE_LOWER_LID]["mid"]
        self.kit.servo[self.LEFT_EYE_UPPER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_UPPER_LID]["mid"]
        self.kit.servo[self.LEFT_EYE_LOWER_LID].angle = self.json_data["eyes"][self.LEFT_EYE_LOWER_LID]["mid"]

    def look_right(self):
        self.kit.servo[self.EYES_LEFT_RIGHT].angle = self.json_data["eyes"][self.EYES_LEFT_RIGHT]["min"]

    def look_left(self):
        self.kit.servo[self.EYES_LEFT_RIGHT].angle = self.json_data["eyes"][self.EYES_LEFT_RIGHT]["max"]

    def look_up(self):
        self.kit.servo[self.EYES_UP_DOWN].angle = self.json_data["eyes"][self.EYES_UP_DOWN]["max"]

    def look_down(self):
        self.kit.servo[self.EYES_UP_DOWN].angle = self.json_data["eyes"][self.EYES_UP_DOWN]["min"]



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

    try:
        while True:
            command = input("eyes> ").strip().lower()

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
                eyes.blink()
                continue

            if command == "lr":
                eyes.look_right()
                continue

            if command == "ll":
                eyes.look_left()
                continue

            if command == "lu":
                eyes.look_up()
                continue

            if command  == "ld":
                eyes.look_down()
                continue

            try:
                eye_id_text, angle_text = command.split()

                eye_id = int(eye_id_text)
                angle = int(angle_text)

                eyes.servo_to_angle(eye_id, angle)
                print(f"Servo {eye_id} moved to {angle} degrees")

            except ValueError:
                print("Enter: <servo_id> <angle>, for example: 0 70")

    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C")

    finally:
        eyes.reset_servos()
        time.sleep(1)




    



