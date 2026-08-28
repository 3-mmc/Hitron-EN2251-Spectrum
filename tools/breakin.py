#!/usr/bin/env python3
"""Try to interrupt the Broadcom BOLT bootloader autoboot.

Run this, THEN power-cycle the board. It floods interrupt characters
(Ctrl-C, ESC, Enter) during the boot window while logging everything,
then falls quiet so you can see if a BOLT '>' prompt appeared.
"""
import serial, sys, time, os

PORT, BAUD = '/dev/serial0', 115200
FLOOD_SECS = 22          # spam interrupts for this long after first byte
INTR = b'\x03'           # Ctrl-C aborts BOLT's STARTUP script

ser = serial.Serial(PORT, BAUD, timeout=0.05)
ser.reset_input_buffer()
logpath = os.path.expanduser(time.strftime('~/hitron/logs/breakin-%Y%m%d-%H%M%S.log'))
log = open(logpath, 'wb')
print(f'Waiting for boot... power-cycle the board now. (log: {logpath})', file=sys.stderr)

seen = False
t0 = None
last = 0
try:
    while True:
        data = ser.read(4096)
        if data:
            if not seen:
                seen = True; t0 = time.time()
                print('--- traffic detected, flooding Ctrl-C ---', file=sys.stderr)
            log.write(data); log.flush()
            sys.stdout.buffer.write(data); sys.stdout.flush()
        now = time.time()
        if seen and now - t0 < FLOOD_SECS:
            if now - last > 0.02:
                ser.write(INTR)      # hammer Ctrl-C
                last = now
        if seen and now - t0 > FLOOD_SECS + 8:
            break
except KeyboardInterrupt:
    pass
finally:
    ser.close(); log.close()
    print(f'\n--- done, saved {logpath} ---', file=sys.stderr)
