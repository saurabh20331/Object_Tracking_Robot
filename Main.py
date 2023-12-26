from picamera.array import PiRGBArray
from picamera import PiCamera
import cv2
import time
import numpy as np

defaultSpeed = 50
windowCenter = 320
centerBuffer = 10
pwmBound = float(50)
cameraBound = float(320)
kp = pwmBound / cameraBound
leftBound = int(windowCenter - centerBuffer)
rightBound = int(windowCenter + centerBuffer)

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.8
COLOR = (0, 0, 0)
FONT_THICKNESS = 1

error = 0
ballPixel = 0

#GPIO
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
#Pin definitions
rightFwd = 13
rightRev = 15
leftFwd = 11
leftRev = 7

#GPIO initialization
GPIO.setup(leftFwd, GPIO.OUT)
GPIO.setup(leftRev, GPIO.OUT)
GPIO.setup(rightFwd, GPIO.OUT)
GPIO.setup(rightRev, GPIO.OUT)

#Disable movement at startup
GPIO.output(leftFwd, False)
GPIO.output(leftRev, False)
GPIO.output(rightFwd, False)
GPIO.output(rightRev, False)

#PWM Initialization

rightMotorFwd = GPIO.PWM(rightFwd, 50)
leftMotorFwd = GPIO.PWM(leftFwd, 50)
rightMotorRev = GPIO.PWM(rightRev, 50)
leftMotorRev = GPIO.PWM(leftRev, 50)
rightMotorFwd.start(defaultSpeed)
leftMotorFwd.start(defaultSpeed)
leftMotorRev.start(defaultSpeed)
rightMotorRev.start(defaultSpeed)
def updatePwm(rightPwm, leftPwm):
	rightMotorFwd.ChangeDutyCycle(rightPwm)
	leftMotorFwd.ChangeDutyCycle(leftPwm)

def pwmStop():
	rightMotorFwd.ChangeDutyCycle(0)
	rightMotorRev.ChangeDutyCycle(0)
	leftMotorFwd.ChangeDutyCycle(0)
	leftMotorRev.ChangeDutyCycle(0)

# Camera setup
camera = PiCamera()
camera.resolution = (640, 480)
camera.framerate = 15
rawCapture = PiRGBArray(camera, size = (640, 480))

time.sleep(0.1)

lower_yellow = np.array([0, 98, 66])
upper_yellow = np.array([20, 255, 255])

cap = cv2.VideoCapture(0)
# Check if the camera opened successfully
if not cap.isOpened():
	print("Error: Could not open camera.")
	exit()
ret, image = cap.read()
centre_x, centre_y = image.shape[1]/2, image.shape[0]/2

# for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
while True:
	ret, image = cap.read()

	# Check if the frame was read successfully
	if not ret:
		print("Error: Could not read frame.")
		break

	output = image.copy()
	hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
	
	mask = cv2.inRange(hsv, lower_yellow, upper_yellow)
	mask = cv2.erode(mask, None, iterations=2)
	mask = cv2.dilate(mask, None, iterations=2)
	output = cv2.bitwise_and(output, output, mask=mask)
	output = cv2.dilate(output, None, iterations=2)
	output = cv2.erode(output, None, iterations=2)
	gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)
	_, binary = cv2.threshold(gray, 1, 255, cv2. THRESH_BINARY)
	circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 3, 500, minRadius = 10, maxRadius = 200, param1 = 100,  param2 = 60)
	cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
	ballPixel = 0
	
	if circles is not None:
		circles = np.round(circles[0, :]).astype("int")
		for (x, y, radius) in circles:

			cv2.circle(image, (x, y), radius, (0, 255, 0), 4)
			cv2.rectangle(output, (x - 5, y - 5), (x + 5, y + 5), (0, 128, 255), -1)	
		
			if radius > 10:	
				ballPixel = x
			else:
				ballPixel = 0

	leftMotorSpeed = -1
	rightMotorSpeed = -1

	rawCapture.truncate(0)
	
	#Proportional controller
	if ballPixel == 0:
		rightMotorSpeed, leftMotorSpeed = 0, 0
		error = 0
		pwmStop()
	elif (ballPixel < leftBound) or (ballPixel > rightBound):
		error = windowCenter - ballPixel
		pwmOut = abs(error * kp) 
		turnPwm = pwmOut + defaultSpeed
		if  ballPixel < (leftBound):
			if radius > 50 and ballPixel < 110:
				rightMotorSpeed, leftMotorSpeed = defaultSpeed, 20
				updatePwm(defaultSpeed, 20)
				GPIO.output(11,True)
				GPIO.output(7,False)
				GPIO.output(13,False)
				GPIO.output(15,False)
			else:
				rightMotorSpeed, leftMotorSpeed = turnPwm, defaultSpeed
				updatePwm(turnPwm, defaultSpeed)
		elif ballPixel > (rightBound):
			if radius > 50 and ballPixel > 540:
				rightMotorSpeed, leftMotorSpeed = 20, defaultSpeed
				updatePwm(20, defaultSpeed)
				GPIO.output(13,True)
				GPIO.output(11,False)
				GPIO.output(7,False)
				GPIO.output(15,False)
			else:
				rightMotorSpeed, leftMotorSpeed = defaultSpeed, turnPwm
				updatePwm(defaultSpeed, turnPwm)
	else:	
		if (radius < 40):
			rightMotorSpeed, leftMotorSpeed = defaultSpeed, defaultSpeed
			updatePwm(defaultSpeed, defaultSpeed)
		else:
			rightMotorSpeed, leftMotorSpeed = 0, 0
			pwmStop()

	cv2.rectangle(image, (0, int(centre_y)*2-30), (int(centre_x)*2, int(centre_y)*2), (255, 255, 255), -1)
	cv2.putText(image, f"Left Motor: {leftMotorSpeed}", (10, int(centre_y)*2-5), FONT, FONT_SCALE, COLOR, FONT_THICKNESS) 
	cv2.putText(image, f"Right Motor: {rightMotorSpeed}", (int(centre_x), int(centre_y)*2-5), FONT, FONT_SCALE, COLOR, FONT_THICKNESS)
	cv2.imshow("output", image)
	key = cv2.waitKey(1) & 0xFF
	if key == ord('q'):
		break

cv2.destroyAllWindows()
camera.close()
pwmStop()
GPIO.cleanup()