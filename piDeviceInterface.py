
#!/usr/bin/env python3.9

# Version 1.0.0

from time import sleep
import cv2

try:
    import RPi.GPIO as GPIO
    RPi_GPIO_present = True
except ImportError:
    RPi_GPIO_present = False
    
# Stepper motor settings
DIR = 27   # Direction GPIO Pin
STEP = 22  # Step GPIO Pin
CW = 1     # Clockwise Rotation
CCW = 0    # Counterclockwise Rotation
STEPON = 0  # pin to turn on/off the stepper

# buttons
btn_left = 13
btn_right = 19
btn_start = 16
btn_stop = 26
btn_rewind = 20

photoint = 21  # photointeruptor

ledon = 12  # pin for LED
pin_forward = 6  # motor pin (spool)
pin_backward = 5

delay = .001  # delay inbetween steps
tolstep = 2 // 2  # defines how many steps are done for correction
steps = 0


step_minus = 0  # counter for stepper corrections
step_plus = 0
rewind = 0

pwm = None
    
def initGpio() :
    global pwm
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DIR, GPIO.OUT)
    GPIO.setup(STEP, GPIO.OUT)
    GPIO.setup(STEPON, GPIO.OUT)
    GPIO.setup(ledon, GPIO.OUT)
    GPIO.setup(pin_forward, GPIO.OUT)
    GPIO.setup(pin_backward, GPIO.OUT)
    GPIO.setup(btn_right, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_left, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_start, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_stop, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(btn_rewind, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(photoint, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup((18, 15, 14), GPIO.OUT)

    pwm = GPIO.PWM(6, 40)  # set PWM channel, hz
    print("GPIO setup")
    
def spoolStart():
    pint = GPIO.input(photoint)
    if pint:
        pwm.start(10)
    else:
        pwm.ChangeDutyCycle(0)

def spoolStop():
    pwm.ChangeDutyCycle(0)
    GPIO.output(pin_forward, GPIO.LOW)
    GPIO.output(pin_backward, GPIO.LOW)
    GPIO.output(STEPON, GPIO.LOW)

def rewind():
    pwm.ChangeDutyCycle(50)
    GPIO.output(pin_forward, GPIO.HIGH)
    GPIO.output(pin_backward, GPIO.LOW)
    

def stepCw(steps):
    for x in range(steps):
        GPIO.output(DIR, CW)
        GPIO.output(STEP, GPIO.HIGH)
        sleep(delay)
        GPIO.output(STEP, GPIO.LOW)
        sleep(delay)


def stepCcw(steps):
    for x in range(steps):
        GPIO.output(DIR, CCW)
        GPIO.output(STEP, GPIO.HIGH)
        sleep(delay)
        GPIO.output(STEP, GPIO.LOW)
        sleep(delay)

def stopScanner():
    spoolStop()
    GPIO.output(ledon, GPIO.LOW)
    GPIO.output(STEPON, GPIO.LOW)

def startScanner():
    GPIO.output((18, 15, 14), (1, 1, 0))
    GPIO.output(ledon, GPIO.HIGH)  # turn on LED
    GPIO.output(STEPON, GPIO.HIGH)
    sleep(0.5)

def cleanup():
    stopScanner()
    GPIO.cleanup()
 
