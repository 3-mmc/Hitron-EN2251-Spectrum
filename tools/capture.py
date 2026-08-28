#!/usr/bin/env python3
"""Listen-only capture of a serial bootlog: raw bytes + timestamped text.

Never writes to the port, so it cannot accidentally interrupt the bootloader.
Writes <out>.bin (raw) and <out>.log (timestamped, printable-escaped).
"""
import argparse, os, serial, sys, time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--port', default='/dev/serial0')
    ap.add_argument('-b', '--baud', type=int, default=115200)
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('-t', '--timeout', type=float, default=0,
                    help='stop after N seconds of total runtime (0 = until Ctrl-C)')
    args = ap.parse_args()

    base = args.out or os.path.expanduser(
        time.strftime('~/hitron/logs/boot-%Y%m%d-%H%M%S').replace('~', os.path.expanduser('~')))
    os.makedirs(os.path.dirname(base), exist_ok=True)

    ser = serial.Serial(args.port, args.baud, timeout=0.1)
    ser.reset_input_buffer()
    start = time.time()
    total = 0
    line = b''
    print(f'Capturing {args.port} @ {args.baud} -> {base}.{{bin,log}}  (Ctrl-C to stop)',
          file=sys.stderr)
    try:
        with open(base + '.bin', 'wb') as fb, open(base + '.log', 'w') as fl:
            while True:
                chunk = ser.read(4096)
                if chunk:
                    fb.write(chunk); fb.flush()
                    total += len(chunk)
                    for byte in chunk:
                        if byte in (10, 13):
                            if line:
                                txt = line.decode('utf-8', 'replace')
                                stamp = f'[{time.time()-start:9.3f}] {txt}'
                                print(stamp); fl.write(stamp + '\n'); fl.flush()
                                line = b''
                        else:
                            line += bytes([byte])
                if args.timeout and time.time() - start > args.timeout:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if line:
            print(line.decode('utf-8', 'replace'))
        ser.close()
        print(f'\n{total} bytes in {time.time()-start:.1f}s -> {base}.bin', file=sys.stderr)

if __name__ == '__main__':
    main()
