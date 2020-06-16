import serial
import sys
import threading
import multiprocessing
import datetime
import time
import json
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text
from luma.core.legacy.font import proportional, LCD_FONT
from luma.led_matrix.device import max7219

#Board set up
GPIO.setmode(GPIO.BOARD)

#Input pins for each button
button7 = 8
button10 = 10
button12 = 11
button14 = 12

#Set up for these pins as inputs
GPIO.setup(button7, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button12, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(button14, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#Set up 3 position switch at IO pins
GPIO.setup(13,GPIO.IN)
GPIO.setup(15,GPIO.IN)

#[firebase instead of json?]

#Dictionary of variables for data collection
pizzaData = { 
    "Weight" : 0, 
    "Time of Day" : time.localtime(), 
    "Size" : 14, 
    "Total Time" : 0
  } 

#MODES: 0 - regular, 1 - cheese, 2 - pepperoni
mode = 0

#LED matrix setup
sr = spi(port=0, device=0, gpio=noop())
device = max7219(sr)
  
#Class for pretop pizza, holds cheese and pepperoni weights in pounds
class PretopPizza:
    def __init__(self,cW,pW):
        self.cheeseWeight = cW
        self.pepWeight = pW

#Pizza dictionary for pretop weights
Pizzas = {
        "7":PretopPizza(0.1,0.06),
        "10":PretopPizza(0.22,0.15),
        "12":PretopPizza(0.32,0.22),
        "14":PretopPizza(0.44,0.3)
        }

#Function for light bar display
def updateLightBar(currentWeight, toppingWeight):
  bars = int(toppingWeight/32*currentWeight)
  if bars < 32:
    with canvas(device) as draw:
      draw.rectangle((0, 0, bars, 8), outline="white", fill="white")
    time.sleep(2)
  else:
    for i in range(5):
      with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="white", fill="white")
      time.sleep(0.2)
      with canvas(device) as draw:
        draw.rectangle(device.bounding_box, outline="black", fill="black")
      time.sleep(0.2)
      

#Function for numeric display
def updateNumbers(lbs):
  msg = str(lbs)
  with canvas(device) as draw:
    text(draw, (0, 0), msg, fill="white", font=proportional(LCD_FONT))
  time.sleep(2)

#Function for adding to JSON file
def appendToJson(obj, fileName):
  try:
    data = json.load(open(fileName, "r"))

    obj.update(data)

    with open(fileName, "a+") as file:
      json.dump(data, file)
  except:
    with open(fileName, "a+") as file:
      json.dump(obj, file)

#Function for button press
def buttonPressed(pizzaSize):
  if pizzaData["Weight"] !=0:
    pizzaData["Total Time"] = time.time() - pizzaData["Total Time"]
    appendToJson(pizzaData, "pizzadata.json") 
  
  tare()
  pizzaData["Weight"] = 0
  pizzaData["Size"] = pizzaSize
  pizzaData["Time of Day"] = time.localtime().asctime()
  pizzaData["Total Time"] = time.time()

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
    else:
        serial_open()

#Opens the serial port and starts recieving data from scale
def serial_open():
    try:
        ser.open()
        ser.flush()
    except serial.serialutil.SerialException:
       pass

#Tares the scale to zero when you press the button
def tare():
    ser.write(b'TK\n') #????

#mainloop
while True:
  #Update weight from scale
  readWeight()
  pizzaData["Weight"] = scaleWeight.get()
  
  #Update display corresponding to mode
  if GPIO.input(13) == GPIO.HIGH:
    updateLightBar(pizzaData["Weight"], Pizzas[str(pizzaData["Size"])].cheeseWeight)
  elif GPIO.input(15) == GPIO.HIGH:
    updateLightBar(pizzaData["Weight"], Pizzas[str(pizzaData["Size"])].pepWeight)
  else:
    updateNumbers(pizzaData["Weight"])
    
  #Button check for size
  if GPIO.input(button7) == GPIO.HIGH:
    buttonPressed(7)
  elif GPIO.input(button10) == GPIO.HIGH:
    buttonPressed(10)
  elif GPIO.input(button12) == GPIO.HIGH:
    buttonPressed(12)
  elif GPIO.input(button14) == GPIO.HIGH:
    buttonPressed(14)
