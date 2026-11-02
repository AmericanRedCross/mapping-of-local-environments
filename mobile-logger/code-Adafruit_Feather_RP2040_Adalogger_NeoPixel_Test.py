import board # for gps, neopixel, sdcard, sht45
import time # for code, gps, neopixel
import neopixel # for neopixel

# Define our colors.
COLOR_NONE = [0,0,0]
COLOR_WAIT = [84,39,143]
# Configure the NeoPixel.
pixels = neopixel.NeoPixel(board.D9, 1, brightness=0.1, auto_write=False)
pixels.fill(COLOR_NONE)
pixels.show()

pixel_on = False
while True:
    if pixel_on:
        pixels[0] = COLOR_NONE
        pixels.show()
        pixel_on = False
    else:
        pixels[0] = COLOR_WAIT
        pixels.show()
        pixel_on = True
    time.sleep(2)