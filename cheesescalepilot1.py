import os
import sys
import json
import time
import serial
import datetime
import threading
import pyfireconnect
import urllib.request
import multiprocessing
import RPi.GPIO as GPIO
from luma.core.legacy import text
from luma.core.render import canvas
from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.legacy.font import proportional, LCD_FONT

#MULTIPROCESSIZNG NOTE !!!!
#https://stackoverflow.com/questions/18864859/python-executing-multiple-functions-simultaneously/18865028

#Check for internet connection
def checkInternet():
  internet = True
  try:
    urllib.request.urlopen('https://google.com')
  except:
    internet = False
  return internet

hasInternet = checkInternet()

#Set timezone
os.environ['TZ'] = 'US/Eastern'
time.tzset()

#pyfire set up if internet is connected
if(hasInternet):
  config = {
    "apiKey" : "AIzaSyCwL-B0X1dx9canmLWcctpvrzqB64hub8s",
    "authDomain" : "cheese-scale-7b32f.firebaseapp.com",
    "databaseURL" : "https://cheese-scale-7b32f.firebaseio.com/",
    "storageBucket" : "cheese-scale-7b32f.appspot.com"
  }

  firebase = pyfireconnect.initialize(config)
  db = firebase.database()

#Board set up
GPIO.setmode(GPIO.BOARD)

#Input pins for each button
button7 = 11
button10 = 12
button12 = 8
button14 = 10

#Input pins for switches
onOff = 36
cheeseToggle = 21
pepToggle = 31

#Set up for these pins as inputs
GPIO.setwarnings(False)
GPIO.setup(button7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button12, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button14, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#Set up 3 position switch at IO pins and on/off switch
GPIO.setup(cheeseToggle,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(pepToggle,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(onOff,GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#Set up these pins to output high to buttons and on/off switch
GPIO.setup(3,GPIO.OUT)
GPIO.output(3,1)
GPIO.setup(5,GPIO.OUT)
GPIO.output(5,1)
GPIO.setup(7,GPIO.OUT)
GPIO.output(7,1)
GPIO.setup(33,GPIO.OUT)
GPIO.output(33,1)
GPIO.setup(35,GPIO.OUT)
GPIO.output(35,1)

#LED matrix setup
sr = spi(port=0, device=0, gpio=noop())
device = max7219(sr, cascaded=4, block_orientation=-90)
  
#Class for pretop pizza, holds cheese and pepperoni weights in pounds
class PretopPizza:
    def __init__(self,cW,pW):
        self.cheeseWeight = cW
        self.pepWeight = pW

#Pizza dictionary for pretop weights
Pizzas = {
        "7":PretopPizza(0.1,0.06),
        "10":PretopPizza(0.16,0.15),
        "12":PretopPizza(0.32,0.22),
        "14":PretopPizza(0.44,0.3)
        }

#Function for light bar display
def updateLightBar(currentWeight, toppingWeight):
  bars = int(currentWeight/toppingWeight*32)
  if bars < 32:
    with canvas(device) as draw:
      draw.rectangle((0, 0, bars, 8), outline="white", fill="white")
  else:
    if bars >= 36:
      with canvas(device) as draw:
        text(draw, (0, 0), "Over", fill="white", font=proportional(LCD_FONT))
      time.sleep(0.1)
      with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
    else:
      with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="white")
      time.sleep(0.25)
      with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
      time.sleep(0.05)

#Function for numeric display
def updateNumbers(lbs):
  msg = str(lbs)
  with canvas(device) as draw:
    text(draw, (0, 0), msg, fill="white", font=proportional(LCD_FONT))

#Function for button press
def buttonPressed(pizzaSize):
  if pizzaData["Weight (lbs)"] > 0:
    pizzaData["Total Time (s)"] = round(time.time() - pizzaData["Total Time (s)"], 3)
    if(hasInternet):
      db.push(pizzaData)
  
  tare()
  time.sleep(.05)
  pizzaData["Weight (lbs)"] = 0
  pizzaData["Size"] = pizzaSize
  pizzaData["Time of Day"] = time.asctime(time.localtime())
  pizzaData["Total Time (s)"] = time.time()
  
#Function that returns current mode
def currentMode():
  mode = "Normal"
  if GPIO.input(cheeseToggle) == GPIO.HIGH:
      mode = "Cheese"
  elif GPIO.input(pepToggle) == GPIO.HIGH:
      mode = "Pepperoni"
  return mode

#Mutable double class for keeping track of weight
class MutableDouble(float):
    def __init__(self, val = 0):
        self.num = val
    def set(self, val):
        self.num = val
    def get(self):
      return self.num
        
#Scale functions from saucer.py
ser = serial.Serial()
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600
scaleWeight = MutableDouble()

#Updates the weight on the scale screen
def readWeight():
    if ser.isOpen():
        try:
            if ser.in_waiting >= 9:
                b = ser.read_all()
                b2 = b.decode("utf-8")
                if b2[0] == "W":
                    if b2[b2.find(":") + 1] == "-":
                        fac = -1
                    else:
                        fac = 1

                    b3 = b2[b2.find(":") + 2:b2.find(":") + 9].strip()

                    try:
                        x = round(float(b3) * fac * 2.20462,2)
                        scaleWeight.set(x)
                    except ValueError:
                        pass
            else:
                pass
        except serial.serialutil.SerialException:
            serial_open()
        except UnicodeDecodeError:
          pass
    else:
        serial_open()
    time.sleep(.01)

#Opens the serial port and starts recieving data from scale
def serial_open():
    try:
        ser.open()
        ser.flush()
    except serial.serialutil.SerialException:
       pass

#Tares the scale to zero when you press the button
def tare():
    ser.write(b'TK\n')

while True:
  #Dictionary of variables for data collection
  pizzaData = { 
      "Weight (lbs)" : -513, 
      "Time of Day" : time.asctime(time.localtime()), 
      "Size" : 14, 
      "Total Time (s)" : time.time(),
      "Mode" : "Normal"
    }
  
  while (GPIO.input(onOff) == GPIO.LOW):
    time.sleep(0.05)
    #LEDS off
    with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")

  #Tare scale before start
  serial_open()
  tare()
  
  #Check for internet again
  hasInternet = hasInternet and checkInternet()

  #mainloop run while switch is on
  while (GPIO.input(onOff) == GPIO.HIGH):
    #Update weight from scale
    readWeight()
    time.sleep(.01)
    #check for weight to be -513 so that random data is not recorded at start
    if(scaleWeight.get() > pizzaData["Weight (lbs)"] and pizzaData["Weight (lbs)"] != -513):
      pizzaData["Weight (lbs)"] = scaleWeight.get()
      pizzaData["Mode"] = currentMode()
      
    #Update display corresponding to mode
    if GPIO.input(cheeseToggle) == GPIO.HIGH:
      updateLightBar(scaleWeight.get(), Pizzas[str(pizzaData["Size"])].cheeseWeight)
    elif GPIO.input(pepToggle) == GPIO.HIGH:
      updateLightBar(scaleWeight.get(), Pizzas[str(pizzaData["Size"])].pepWeight)
    else:
      updateNumbers(scaleWeight.get())
    
    #Button check for size
    if GPIO.input(button7) == GPIO.HIGH:
      buttonPressed(7)
    elif GPIO.input(button10) == GPIO.HIGH:
      buttonPressed(10)
    elif GPIO.input(button12) == GPIO.HIGH:
      buttonPressed(12)
    elif GPIO.input(button14) == GPIO.HIGH:
      buttonPressed(14)
  
  #Save last pizza before exiting
  buttonPressed(0)
