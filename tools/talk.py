#!/usr/bin/env python3
"""Send lines to the serial console and print whatever comes back.

Usage:  talk.py [-b baud] [--wait S] "line1" "line2" ...
Each argument is sent followed by CR. Use '' to send a bare CR.
Reads for --wait seconds after the last line. Also logs raw to logs/.
"""
import argparse, serial, sys, time, os

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-b', '--baud', type=int, default=115200)
    ap.add_argument('-p', '--port', default='/dev/serial0')
    ap.add_argument('--wait', type=float, default=2.0, help='read seconds after each line')
    ap.add_argument('--eol', default='cr', choices=['cr', 'lf', 'crlf'])
    ap.add_argument('lines', nargs='*')
    args = ap.parse_args()
    eol = {'cr': b'\r', 'lf': b'\n', 'crlf': b'\r\n'}[args.eol]

    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    def drain(secs):
        end = time.time() + secs
        out = b''
        while time.time() < end:
            out += ser.read(4096)
        sys.stdout.buffer.write(out)
        sys.stdout.flush()
        return out

    ser.reset_input_buffer()
    drain(0.5)
    for ln in (args.lines or ['']):
        ser.write(ln.encode() + eol)
        ser.flush()
        drain(args.wait)
    ser.close()

if __name__ == '__main__':
    main()
