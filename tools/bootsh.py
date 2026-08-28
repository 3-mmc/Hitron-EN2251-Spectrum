#!/usr/bin/env python3
"""Set XARGS=init=/bin/sh (RAM-only) and replay BOLT's STARTUP to get a root shell.
Non-persistent: a power cycle reverts everything. Logs raw to logs/rootshell-*.log."""
import serial, sys, time, os

PORT, BAUD = '/dev/serial0', 115200
SETENV = b'setenv XARGS "init=/bin/sh"\r'
# STARTUP replayed verbatim; BOLT expands $DT_ADDRESS/$DT_IDX/$XARGS etc.
BOOT = (b'load -nz -raw -addr=$DT_ADDRESS -max=0x10000 flash0.devtree$DT_IDX;'
        b'$PREBOOT;boot flash0.kernel$KL_IDX "ubi.mtd=flash0.rg$RG_IDX '
        b'ubi.block=0,rootfs rootfstype=squashfs root=/dev/ubiblock0_0 ro '
        b'platformboot ubifs_data coherent_pool=1M $XARGS"\r')

ser = serial.Serial(PORT, BAUD, timeout=0.1)
log = open(os.path.expanduser(time.strftime('~/hitron/logs/rootshell-%Y%m%d-%H%M%S.log')), 'wb')

def drain(secs):
    end = time.time() + secs
    while time.time() < end:
        d = ser.read(4096)
        if d:
            log.write(d); log.flush()
            sys.stdout.buffer.write(d); sys.stdout.flush()

ser.reset_input_buffer()
ser.write(b'\r'); drain(1)
ser.write(SETENV); drain(2)
ser.write(BOOT)
drain(40)                      # wait through kernel boot to the shell
# nudge the shell and prove we're root
for cmd in (b'\r', b'id\r', b'uname -a\r', b'cat /proc/version\r'):
    ser.write(cmd); drain(2)
ser.close(); log.close()
