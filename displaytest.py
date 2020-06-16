import time
import RPi.GPIO as GPIO
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.virtual import viewport
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, LCD_FONT
from luma.led_matrix.device import max7219

#LED matrix setup
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=4, block_orientation=-90)
  
weight = 15
pizza = 20

bars = int((32/pizza)*weight)
print(str(bars) + " bars lit")
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

print(str(weight) + " LBs lit")
msg = str(weight) + " LB"
with canvas(device) as draw:
    text(draw, (0, 0), msg, fill="white", font=proportional(LCD_FONT))
time.sleep(2)