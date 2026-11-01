# animatronic_eyes
Code to run animatronic eyes with the RPi. 

# Setup
## Configure I2C
Configure your Pi with I2C:

```powershell
sudo apt-get install python-smbus
sudo apt-get install i2c-tools
```

Scan to see if you have port 1 or port 0 on your pi:
``` powershell
sudo i2cdetect -y 0
or
sudo i2cdetect -y 1
```

## Configure servokit library
```
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install adafruit-circuitpython-servokit

python main.py

deactivate
```

## Configure INA228 library
```
pip install adafruit-circuitpython-ina228 
```

## Deploying onto RPi
For a dry run:
```bash
./deploy.sh --dry-run vicky eyepi.local /home/vicky/projects/eyes
```
For an actual copy: 
```bash
./deploy.sh vicky eyepi.local /home/vicky/projects/eyes
```

To run script on the pi, navigate to eyes folder.
then:
```bash
source .venv/bin/activate
```

```bash
python servo/servo.py
```
