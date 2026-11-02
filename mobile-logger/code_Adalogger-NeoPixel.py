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
COLOR_NONE = [0,0,0]
COLOR_WAIT = [84,39,143]
COLOR_0 = [254,240,217]
COLOR_1 = [253,204,138]
COLOR_2 = [252,141,89]
COLOR_3 = [227,74,51]
COLOR_4 = [179,0,0]
# Configure the NeoPixel.
pixels = neopixel.NeoPixel(board.D9, 1, brightness=0.1, auto_write=False)
pixels.fill(COLOR_NONE)
pixels.show()
# Set our variables for blink rate.
# When waiting for GPS fix, on/off of the NeoPixel is fast.
PIXEL_GPS_WAIT_ON_DURATION = 0.5
PIXEL_GPS_WAIT_OFF_DURATION = 0.5
# When recording, the blink rate slows down.
PIXEL_RECORDING_ON_DURATION = 2.0
PIXEL_RECORDING_OFF_DURATION = 4.0
# Set our color function.
# When recording, the color changes based on the temperature measurement.
def color_for_temp_c(temp_c):
    if temp_c >= 40.0:
        return COLOR_4
    elif temp_c >= 35.0:
        return COLOR_3    
    elif temp_c >= 30.0:
        return COLOR_2
    elif temp_c >= 25.0:
        return COLOR_1    
    else:
        return COLOR_0 


## Setup the SD card
# Connect to the card and mount the filesystem.
sd_spi = busio.SPI(board.SD_CLK, board.SD_MOSI, board.SD_MISO)
sd = sdcardio.SDCard(sd_spi, board.SD_CS)
vfs = storage.VfsFat(sd)
storage.mount(vfs, "/sd")
# Configure logging variables.
LOG_FILE = "/sd/log.csv" # Path to the file to log data. We'll update it later.
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
# Create time counter and tracker for the indicator light.
last_pixel_toggle = time.monotonic()
pixel_on = False
new_session = True
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
                # Update the NeoPixel to blink waiting for fix status.
                if pixel_on:
                    if current - last_pixel_toggle >= PIXEL_GPS_WAIT_ON_DURATION:
                        pixels[0] = COLOR_NONE
                        pixels.show()
                        pixel_on = False
                        last_pixel_toggle = current
                else:
                    if current - last_pixel_toggle >= PIXEL_GPS_WAIT_OFF_DURATION:
                        pixels[0] = COLOR_WAIT
                        pixels.show()
                        pixel_on = True
                        last_pixel_toggle = current
                        # Free up the memory space from unused memory objects.
                        gc.collect() 
                # Go back to the top of the while loop.
                continue
            # We have a fix (gps.has_fix is true)!
            # Get SHT data with one sensor read action.
            CURRENTTEMP, CURRENTHUMI = sht.measurements
            # Create a variable for each thing we want to record.
            # Cache the struct_time object that holds the fix time.
            # Note you might not get all data like year, day, month!
            ts = gps.timestamp_utc
            # Format our time in ISO 8601.
            THISTIME = "{}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format( 
                ts.tm_year,
                ts.tm_mon,
                ts.tm_mday,
                ts.tm_hour,
                ts.tm_min,
                ts.tm_sec
            )
            THISSPOT = "{:.6f},{:.6f}".format(gps.latitude, gps.longitude)
            THISTEMP = "{:.2f}".format(CURRENTTEMP)
            THISHUMI = "{:.2f}".format(CURRENTHUMI)
            # Combine our measurements into one line.
            LINELOG = "{},{},{},{}\r\n".format(THISTIME, THISSPOT, THISTEMP, THISHUMI)
            # If this is the first log of this session, set a new filename
            if new_session:
                LOG_FILE = "/sd/{}-{:02}-{:02}T{:02}{:02}{:02}Z.csv".format(
                    ts.tm_year,
                    ts.tm_mon,
                    ts.tm_mday,
                    ts.tm_hour,
                    ts.tm_min,
                    ts.tm_sec
                )
                new_session = False
            # Open file and append a new data record.
            with open(LOG_FILE, LOG_MODE) as f:
                print(LINELOG)
                f.write(LINELOG)
            # Update the NeoPixel to show recording status.
            if pixel_on:
                if current - last_pixel_toggle >= PIXEL_RECORDING_ON_DURATION:
                    pixels[0] = COLOR_NONE
                    pixels.show()
                    pixel_on = False
                    last_pixel_toggle = current
            else:
                if current - last_pixel_toggle >= PIXEL_RECORDING_OFF_DURATION:
                    pixels[0] = color_for_temp_c(CURRENTTEMP)
                    pixels.show()
                    pixel_on = True
                    last_pixel_toggle = current                
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
