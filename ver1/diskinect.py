import cv2
import random
import time
from threading import Thread
from pynput.keyboard import Key, Controller


"""
    Camera object
    Setting downsized resolution to 160x120 for optimization when analysing image
"""
cap = cv2.VideoCapture(0)
cap.set(3,640)
cap.set(4,480)
comprWidth = 160
comprHeight = 120

"""
    Keyboard Controller
     To simulate keypressed for output

     Section numbers will trigger that respective indexed key

    Reads from diskinect.cfg - uses default values if that fails
"""
keyboard = Controller()
outputKeys = ["a", "i", "b", "j", None, "l", Key.enter, "k", Key.space]
try:
    config = open("diskinect.cfg")
    for line in config:
        if len(line) > 0:
            if line[0].isdigit() and line[0] != "9":
                keyConfig = line.split()
                keySection = keyConfig[0]
except:
    print("Config file not found - using default keyset")

"""
    Frame format:
    2D array of RBG value groupings
    len(frame) = image height / y-axis
    len(frame[i]) = image width / x-axis
    frame[i][0-2] = RGB values in B G R order
"""
frame = []
lastFrame = []

# Section ID where the most motion was detected in, used to draw box and output control
section = -1
# Boolean to tell other threads to quit when program ends
quitting = False

"""
    Change Threshold: 0-255
    How much one of the RGB values should have changed by to qualify as change
"""
changeThreshold = 100

class CameraDisplayThread(Thread):
    """
        Thread class for displaying the input video stream
    """
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        # Delegating global variable
        global quitting
        while True:
            # Reads input from camera
            ret, frame = cap.read()
            # Draws box around segment where motion is detected
            defineSegment(frame, len(frame), len(frame[0]), section)
            # Draws image in window
            cv2.imshow('Video Controller',frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        # Quitting program
        quitting = True
        cap.release()
        cv2.destroyAllWindows()

class MotionDetectionThread(Thread):
    """
        Thread class for finding which segment of the input video stream has the most movement in it
         Outputs the segment to the global 'section' variable
        Segment ID Chart:
         .-----------.
         [ 0 | 1 | 2 ]
         [---+---+---]
         [ 3 | 4 | 5 ]
         [---+---+---]
         [ 6 | 7 | 8 ]
         ^-----------^
        Analyzes a grayscale version of the image to reduce computing time
    """
    def __init__(self):
        Thread.__init__(self)
        self

    def run(self):
        # Delegating which variables are globally used
        global section
        global quitting

        # Started boolean used for gathering information from inital frame
        started = False
        # Quitting boolean set in video display thread
        while not quitting:
            if started:
                # Create array for how many pixel in each section have changed (been altered from the last frame past the change threshold)
                changeScores = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

                # Reads input from the camera and turns the frame into grayscale (for optimization)
                ret, cframe = cap.read()
                cframe = cv2.resize(cframe, (comprWidth, comprHeight))
                cframe = cv2.cvtColor(cframe, cv2.COLOR_BGR2GRAY)

                # Setting height and width variables to reduce len() calls
                height = len(cframe)
                width = len(cframe[0])

                # Loop through each pixel to check if it's been changed
                for y in range(height):
                    for x in range(width):
                        # Pixel values changed to ints to avoid int8 overflow/underflow
                        pixel = int(cframe[y][x])
                        lastPixel = int(lastFrame[y][x])
                        # Increments the change score for the appropriate section if the difference is greated than or equal to the threshold
                        if abs(pixel - lastPixel) >= changeThreshold:
                            changeIndex = 0
                            if y > height/3:
                                changeIndex += 3
                            if y > 2*height/3:
                                changeIndex += 3
                            if x > width/3:
                                changeIndex += 1
                            if x > 2*width/3:
                                changeIndex += 1
                            changeScores[changeIndex] += 1
                # Largest index initialized to -1 to represent no changes
                largestIndex = -1
                # Find largest change score
                for index in range(9):
                    if (largestIndex == -1 and changeScores[index] > 0) or (changeScores[index] > changeScores[largestIndex]):
                        largestIndex = index
                # Set global section to the correct value and update the last frame for the next loop
                section = largestIndex
                lastFrame = cframe
                # Trigger the correct keypress
                outputKey(section)
            else:
                # Setting the last frame value so that it is not empty at the first loop
                ret, lastFrame = cap.read()
                lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
                # Loop has been started
                started = True

def defineSegment(frame, height, width, segment):
    """
        Takes an input image and draws a red box around the specified segment
    """
    if segment < 0:
        return
    # Finding the x-axes of the left and right sides of the box
    if segment % 3 == 0:
        xmin = 0
        xmax = int(width/3)
    elif segment % 3 == 1:
        xmin = int(width/3)
        xmax = int(2*width/3)
    else:
        xmin = int(2*width/3)
        xmax = width - 1
    # Finding the y-axes of the top and bottom sides of the box
    if segment / 3 < 1:
        ymin = 0
        ymax = int(height/3)
    elif segment / 3 < 2:
        ymin = int(height/3)
        ymax = int(2*height/3)
    else:
        ymin = int(2*height/3)
        ymax = height - 1
    # Defining the color of the box
    red = [0, 0, 255]
    # Loop through the pixels on the box and setting them to the border color
    for y in range(ymin, ymax):
        frame[y][xmin] = red
        frame[y][xmax] = red
    for x in range(xmin, xmax):
        frame[ymin][x] = red
        frame[ymax][x] = red

def outputKey(index):
    try:
        key = outputKeys[index]
        while key == None:
            key = outputKeys[random.randint(0,8)]
        keyboard.press(key)
        time.sleep(0.05)
        keyboard.release(key)
        print("Pressed",key)
    except:
        return

# Creating and starting camera and motion detection threads
camera = CameraDisplayThread()
camera.start()
motion = MotionDetectionThread()
motion.start()

