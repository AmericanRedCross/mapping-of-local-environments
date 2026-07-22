### Logging code for the
### Adafruit Feather RP2040 Adalogger 
### + NeoPixel
### (Rename to code.py when copying to the board.)

## Import core library dependencies
import sdcardio # for sdcard
import board # for gps, neopixel, sdcard, sht45
import busio # for gps, sdcard
import digitalio # for sdcard
import gc # for memory maintenance
import storage  # for sdcard
import time # for code, gps, neopixel
import traceback # for error logging
from microcontroller import watchdog as w # for watchdog
from watchdog import WatchDogMode # for watchdog
## Import library dependencies
import adafruit_gps # for gps
import adafruit_sht4x # for sht45
import neopixel # for neopixel

## Configure watchdog for restarting the system in event of a crash
w.timeout = 6.0
w.mode = WatchDogMode.RESET

## Setup the board's NeoPixel
# Define our colors.
COLOR_RED = [215,25,28]
COLOR_ORANGE = [253,174,97]
COLOR_YELLOW = [255,255,191]
COLOR_BLUE_LGT = [171,217,233]
COLOR_BLUE_DRK = [44,123,182]
COLOR_PURPLE = [94,60,153]
COLOR_NONE = [0,0,0]
# Configure the NeoPixels
pixels = neopixel.NeoPixel(board.D9, 2, brightness=0.2, auto_write=False)
pixels.fill(COLOR_NONE)
pixels.show()
# Set our variables for blink rate and colors.
PIXEL_GPS_WAIT_ON_DURATION = 1.0
PIXEL_GPS_WAIT_OFF_DURATION = 1.0
PIXEL_GPS_ON_DURATION = 2.0
PIXEL_GPS_OFF_DURATION = 8.0
PIXEL_TEMP_ON_DURATION = 2.0
PIXEL_TEMP_OFF_DURATION = 4.0
def color_for_temp_c(temp_c):
    if temp_c >= 35.0:
        return COLOR_RED
    elif temp_c >= 30.0:
        return COLOR_ORANGE    
    elif temp_c >= 25.0:
        return COLOR_YELLOW
    elif temp_c >= 20.0:
        return COLOR_BLUE_LGT    
    else:
        return COLOR_BLUE_DRK  


## Setup the SD card
# Connect to the card and mount the filesystem.
sd_spi = busio.SPI(board.SD_CLK, board.SD_MOSI, board.SD_MISO)
sd = sdcardio.SDCard(sd_spi, board.SD_CS)
vfs = storage.VfsFat(sd)
storage.mount(vfs, "/sd")
# Configure logging variables.
LOG_FILE = "/sd/log.csv" # Path to the file to log data.
LOG_MODE = "a" # Mode for opening the log file. 
# (Mode 'a' means append or add new lines to the end
# of the file rather than erasing it and starting over.)


## Setup the SHT41/45 temperature and humidity sensor
sht = adafruit_sht4x.SHT4x(board.I2C())


## Setup the Adafruit Mini GPS
# Create an I2C interface to talk to using default pins.
i2c = board.STEMMA_I2C() 
# Create a GPS module instance.
gps = adafruit_gps.GPS_GtopI2C(i2c, debug=False) # Use I2C interface.
# Turn on the basic GGA and RMC info.
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")
# Set update rate to once a second (1hz) which is what you typically want.
gps.send_command(b"PMTK220,1000")


## Main code loop that runs for-ev-er
# Create time counter for logging.
last_log = time.monotonic()
# Create time counter and tracker for the temperature indicator light.
last_temp_toggle = time.monotonic()
pixel_temp_on = False
# Create time counter and tracker for the GPS indicator light.
last_gps_toggle = time.monotonic()
pixel_gps_on = False
# Let's go!
while True:
    # Feed the watchdog to prevent it expiring and resetting the system.
    w.feed() 
    try:
        time.sleep(0.1) # A very slight delay to cut CPU usage and battery draw.
        # Make sure to call gps.update() every loop iteration and at least twice
        # as fast as data comes from the GPS unit (set above to once a second).
        # This returns a bool that's true if it parsed new data.
        gps.update()
        current = time.monotonic()
        # Wait at least a second before running logging process.
        if current - last_log >= 1.0: 
            last_log = current   
            # Check for a location fix.
            if not gps.has_fix:
                # We don't have a fix yet.
                # Log to serial console in Mu Editor.
                print("Waiting for fix...")
                # Update the NeoPixel showing GPS status.
                if pixel_gps_on:
                    if current - last_gps_toggle >= PIXEL_GPS_WAIT_ON_DURATION:
                        pixels[0] = COLOR_NONE
                        pixels.show()
                        pixel_gps_on = False
                        last_gps_toggle = current
                else:
                    if current - last_gps_toggle >= PIXEL_GPS_WAIT_OFF_DURATION:
                        pixels[0] = COLOR_BLUE_LGT
                        pixels.show()
                        pixel_gps_on = True
                        last_gps_toggle = current
                        # Free up the memory space from unused memory objects.
                        gc.collect() 
                # Go back to the top of the while loop.
                continue
            # We have a fix (gps.has_fix is true)!
            # Get SHT data with one sensor read action.
            CURRENTTEMP, CURRENTHUMI = sht.measurements
            # Update the NeoPixel showing temperature.
            if pixel_temp_on:
                if current - last_temp_toggle >= PIXEL_TEMP_ON_DURATION:
                    pixels[1] = COLOR_NONE
                    pixels.show()
                    pixel_temp_on = False
                    last_temp_toggle = current
            else:
                if current - last_temp_toggle >= PIXEL_TEMP_OFF_DURATION:
                    pixels[1] = color_for_temp_c(CURRENTTEMP)
                    pixels.show()
                    pixel_temp_on = True
                    last_temp_toggle = current
            # Update the NeoPixel showing GPS status.
            if pixel_gps_on:
                if current - last_gps_toggle >= PIXEL_GPS_ON_DURATION:
                    pixels[0] = COLOR_NONE
                    pixels.show()
                    pixel_gps_on = False
                    last_gps_toggle = current
            else:
                if current - last_gps_toggle >= PIXEL_GPS_OFF_DURATION:
                    pixels[0] = COLOR_BLUE_DRK
                    pixels.show()
                    pixel_gps_on = True
                    last_gps_toggle = current     
            # Create a variable for each thing we want to record.
            THISTIME = "{}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format( # Formatting in ISO 8601.
                gps.timestamp_utc.tm_year,  # Grab parts of the time from the
                gps.timestamp_utc.tm_mon,  # struct_time object that holds
                gps.timestamp_utc.tm_mday,  # the fix time.  Note you might
                gps.timestamp_utc.tm_hour,  # not get all data like year, day, month!
                gps.timestamp_utc.tm_min, 
                gps.timestamp_utc.tm_sec
            )
            THISSPOT = "{:.6f},{:.6f}".format(gps.latitude, gps.longitude)
            THISTEMP = "{:.2f}".format(CURRENTTEMP)
            THISHUMI = "{:.2f}".format(CURRENTHUMI)
            # Combine our measurements into one line.
            LINELOG = "{},{},{},{}\r\n".format(THISTIME, THISSPOT, THISTEMP, THISHUMI)
            # Open file and append a new data record.
            with open(LOG_FILE, LOG_MODE) as f:
                print(LINELOG)
                f.write(LINELOG)
            # Free up the memory space from unused memory objects.
            gc.collect() 
    # Catch errors that cause the loop to exit unexpectedly.
    except Exception as e:
        # Log the error, appending it to a file.
        with open("/sd/error.txt", "a") as f:
            traceback.print_exception(e, e, e.__traceback__, file=f)
        # Free up the memory space from unused memory objects.
        gc.collect() 
        # Wait a second before trying everything again.
        time.sleep(1)    
