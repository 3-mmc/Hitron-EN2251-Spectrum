#!/usr/bin/env python3
"""Cycle common baud rates on /dev/serial0 and score which one yields sane text.

Run this WHILE the target board is booting (or repeatedly power-cycling it).
Each baud gets --dwell seconds. Best guess is printed at the end.
"""
import argparse, serial, sys, time, collections

BAUDS = [115200, 57600, 38400, 19200, 9600, 230400, 460800, 921600, 4800, 2400]

# Substrings that strongly suggest we've locked onto a real bootlog.
KEYWORDS = [b'Boot', b'boot', b'CFE', b'U-Boot', b'Linux', b'BCM', b'Broadcom',
            b'RAM', b'DRAM', b'flash', b'Flash', b'init', b'kernel', b'login',
            b'Hitron', b'version', b'Press', b'MAC', b'eCos', b'DOCSIS']

def score(buf: bytes):
    if not buf:
        return 0.0, {}
    printable = sum(1 for b in buf if 32 <= b <= 126 or b in (9, 10, 13))
    ratio = printable / len(buf)
    nl = buf.count(b'\n') + buf.count(b'\r')
    hits = sum(1 for k in KEYWORDS if k in buf)
    # Framing noise shows up as a flood of a few high-bit values.
    common = collections.Counter(buf).most_common(1)[0][1] / len(buf)
    s = ratio * 100
    s += min(nl, 40) * 1.5          # real logs have line breaks
    s += hits * 25                  # keywords are near-conclusive
    s -= common * 40                # one byte dominating == garbage
    return s, {'bytes': len(buf), 'printable%': round(ratio * 100, 1),
               'lines': nl, 'kw': hits}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--port', default='/dev/serial0')
    ap.add_argument('-d', '--dwell', type=float, default=4.0,
                    help='seconds to listen per baud rate')
    ap.add_argument('-r', '--rounds', type=int, default=1,
                    help='how many times to sweep the full list')
    ap.add_argument('-b', '--bauds', default=None,
                    help='comma-separated baud list to override the default')
    args = ap.parse_args()

    bauds = [int(x) for x in args.bauds.split(',')] if args.bauds else BAUDS
    totals = collections.defaultdict(float)
    samples = {}

    for rnd in range(args.rounds):
        for baud in bauds:
            try:
                ser = serial.Serial(args.port, baud, timeout=0.2)
            except Exception as e:
                print(f'  {baud:>7}  OPEN FAILED: {e}')
                continue
            ser.reset_input_buffer()
            buf = b''
            end = time.time() + args.dwell
            while time.time() < end:
                buf += ser.read(4096)
            ser.close()
            s, info = score(buf)
            totals[baud] += s
            if buf and (baud not in samples or s > samples[baud][0]):
                samples[baud] = (s, buf[:400])
            print(f'  {baud:>7}  score={s:7.1f}  {info}')
        print(f'--- round {rnd+1}/{args.rounds} done ---')

    print('\n=== ranking ===')
    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    for baud, s in ranked:
        print(f'  {baud:>7}  {s:8.1f}')
    if ranked and ranked[0][1] > 0:
        best = ranked[0][0]
        print(f'\nBest guess: {best}')
        if best in samples:
            print('--- sample ---')
            sys.stdout.write(samples[best][1].decode('utf-8', 'replace'))
            print('\n--- end sample ---')
    else:
        print('\nNothing received. Check wiring: target TX -> Pi GPIO15 (pin 10), '
              'and a COMMON GROUND. Verify the target is actually transmitting.')

if __name__ == '__main__':
    main()
