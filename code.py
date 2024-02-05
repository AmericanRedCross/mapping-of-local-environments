# SPDX-FileCopyrightText: 2024 Dan Joseph
# SPDX-License-Identifier: MIT
# Includes text from example code 
# by ladyada for Adafruit Industries (licensed MIT)

import os
import digitalio
import time
import board
import busio
import storage
import adafruit_sdcard
import adafruit_gps
import adafruit_pct2075

## Set variables

LOG_FILE = "/sd/log.txt" # Path to the file to log data.
LOG_MODE = "ab" # File more for opening the log file. 
# (Mode 'ab' means append or add new lines to the end
# of the file rather than erasing it and starting over.)

## Setup the sd card

# The SD_CS pin is the chip select line.
SD_CS = board.SD_CS

# Connect to the card and mount the filesystem.
cs = digitalio.DigitalInOut(SD_CS)
sdcard = adafruit_sdcard.SDCard(board.SPI(), cs)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, "/sd")

# Use the filesystem as normal! Our files are under `/sd`.

## Setup the temperature sensor
i2c = board.I2C()
pct = adafruit_pct2075.PCT2075(i2c)

## Setup the GPS

# Create a serial connection for the GPS connection using default speed and
# a slightly higher timeout (GPS modules typically update once a second).
# These are the defaults you should use for the GPS FeatherWing.
# For other boards set RX = GPS module TX, and TX = GPS module RX pins.
uart = busio.UART(board.D0, board.D1, baudrate=9600, timeout=10)

# Create a GPS module instance.
gps = adafruit_gps.GPS(uart, debug=False)  # Use UART/pyserial

# Turn on the basic GGA and RMC info
gps.send_command(b"PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0")

# Set update rate to once a second (1hz) which is what you typically want.
gps.send_command(b"PMTK220,1000")

## Main loop that runs for-ev-er
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
            continue
        # We have a fix! (gps.has_fix is true)
        # Create a variable for each thing we want to record.
        thistime = "{}-{:02}-{:02}T{:02}:{:02}:{:02}Z".format( # Formatting in ISO 8601.
            gps.timestamp_utc.tm_year,  # Grab parts of the time from the
            gps.timestamp_utc.tm_mon,  # struct_time object that holds
            gps.timestamp_utc.tm_mday,  # the fix time.  Note you might
            gps.timestamp_utc.tm_hour,  # not get all data like year, day, month!
            gps.timestamp_utc.tm_min, 
            gps.timestamp_utc.tm_sec
        )
        thisspot = "{:.6f},{:.6f}".format(gps.latitude, gps.longitude)
        thistemp = "{:.2f}".format(pct.temperature)
        # Combine our measurements into one line.
        line = "{},{},{}\r\n".format(thistime, thisspot, thistemp)
        # Save the line to the log file.
        with open(LOG_FILE, LOG_MODE) as f:
            print(line)
            f.write(line.encode('utf-8'))
