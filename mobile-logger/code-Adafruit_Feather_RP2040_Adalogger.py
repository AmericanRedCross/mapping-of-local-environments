### logging code for the
### Adafruit Feather RP2040 Adalogger
# rename to code.py when copying to the board

## import library dependencies
import adafruit_displayio_sh1107 # for display
import adafruit_gps # for gps
import sdcardio # (a core module) for sdcard
import adafruit_sht4x # for sht45
import board # for display, gps, sdcard, sht45
import busio # for gps, sdcard
import digitalio # for display, sdcard
import displayio # for display
import storage  # for sdcard
import terminalio # for display
import time # for code, gps
import os #for display, sdcard
from adafruit_display_text import label # for display
from i2cdisplaybus import I2CDisplayBus # for display

## Setup the SD card
# Connect to the card and mount the filesystem.
sd_spi = busio.SPI(board.SD_CLK, board.SD_MOSI, board.SD_MISO)
sd = sdcardio.SDCard(sd_spi, board.SD_CS)
vfs = storage.VfsFat(sd)
storage.mount(vfs, "/sd")

# Use the filesystem as normal! Our files are under /sd

LOG_FILE = "/sd/log.csv" # Path to the file to log data.
LOG_MODE = "ab" # File more for opening the log file. 
# (Mode 'ab' means append or add new lines to the end
# of the file rather than erasing it and starting over.)


## Setup the display - Adafruit 128x64 OLED FeatherWing

displayio.release_displays()
# oled_reset = board.D9

# Use for I2C
i2c = board.I2C()  # uses board.SCL and board.SDA
display_bus = I2CDisplayBus(i2c, device_address=0x3C)

# SH1107 is vertically oriented 64x128
WIDTH = 128
HEIGHT = 64
BORDER = 2

display = adafruit_displayio_sh1107.SH1107(display_bus, width=WIDTH, height=HEIGHT)

# Make the display context
splash = displayio.Group()
display.root_group = splash

color_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)
color_palette = displayio.Palette(1)
color_palette[0] = 0x000000  # black

bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
splash.append(bg_sprite)

# Set up 4 lines of text
text_area1 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF, x=8, y=8) # fits 20 characters 
splash.append(text_area1)

text_area2 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF, x=8, y=24) # fits 20 characters 
splash.append(text_area2)

text_area3 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF, x=8, y=40) # fits 20 characters 
splash.append(text_area3)

text_area4 = label.Label(terminalio.FONT, text=" "*20, color=0xFFFFFF, x=8, y=56) # fits 20 characters 
splash.append(text_area4)

## Setup the SHT41/45 temperature and humidity sensor
sht = adafruit_sht4x.SHT4x(board.I2C())


## Setup the Adafruit Ultimate GPS
# Define RX and TX pins for the board's serial port connected to the GPS.
# These are the defaults you should use for the GPS FeatherWing.
RX = board.RX
TX = board.TX
 
# Create a serial connection for the GPS connection using default speed and
# a slightly higher timeout (GPS modules typically update once a second).
uart = busio.UART(TX, RX, baudrate=9600, timeout=10)

gps = adafruit_gps.GPS(uart)

# Turn on the basic GGA and RMC info
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

# Set update rate to once a second (1hz) which is what you typically want.
gps.send_command(b"PMTK220,1000")


## Main code loop that runs for-ev-er
last_print = time.monotonic()
while True:
    # Make sure to call gps.update() every loop iteration and at least twice
    # as fast as data comes from the GPS unit (usually every second).
    # This returns a bool that's true if it parsed new data (you can ignore it
    # though if you don't care and instead look at the has_fix property).
    gps.update()
    # Every second print out current location details if there's a fix.
    current = time.monotonic()
    if current - last_print >= 1.0:
        last_print = current
        if not gps.has_fix:
            # Try again if we don't have a fix yet.
            print("Waiting for fix...")
            LINEWAITING = "{} C, {} RH".format("{:.2f}".format(sht.temperature), "{:.2f}".format(sht.relative_humidity))
            text_area1.text = "Waiting for fix..."
            text_area2.text = "Clear view of sky?"
            text_area3.text = LINEWAITING
            text_area4.text = "Sleeves up."
            continue
        # We have a fix! (gps.has_fix is true)
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
        THISTEMP = "{:.2f}".format(sht.temperature)
        THISHUMI = "{:.2f}".format(sht.relative_humidity)

        # Combine our measurements into one line.
        LINELOG = "{},{},{},{}\r\n".format(THISTIME, THISSPOT, THISTEMP, THISHUMI)
        
        text_area1.text = "Recording!"
        text_area2.text = "{:.6f},".format(gps.latitude)
        text_area3.text = "{:.6f}".format(gps.longitude)
        text_area4.text = "{} C, {} RH".format(THISTEMP, THISHUMI)
        
        # open file and append a new data record
        with open(LOG_FILE, LOG_MODE) as f:
            print(LINELOG)
            f.write(LINELOG.encode('utf-8'))
