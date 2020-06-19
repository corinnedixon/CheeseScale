import serial
import sys
import threading
import multiprocessing
import datetime
import time
import os
import json
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text
from luma.core.legacy.font import proportional, LCD_FONT
from luma.led_matrix.device import max7219
import pyfireconnect

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
                print("b: " + str(b))
                b2 = b.decode("utf-8")
                print("b2: " + str(b2))
                if b2[0] == "W":
                  if b2[b2.find(":") + 1] == "-":
                    fac = -1
                  else:
                    fac = 1
                else:
                  pass

                b3 = b2[b2.find(":") + 2:b2.find(":") + 9].strip()
                print("b3: " + str(b3) +"\n")

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
    time.sleep(.2)

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
    
#Tare scale before start
serial_open()
tare()

while True:
  readWeight()
