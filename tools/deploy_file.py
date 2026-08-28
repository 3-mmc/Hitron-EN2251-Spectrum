#!/usr/bin/env python3
"""Push a local file to a path on the target over the serial console.

Sends the contents inside a quoted here-doc (no shell expansion on the target),
then verifies with md5sum on the target vs hashlib locally.

Usage:  deploy_file.py <local-path> <remote-path>
Assumes the target already has a shell on /dev/serial0 @ 115200.
"""
import serial, sys, time, hashlib

PORT, BAUD = '/dev/serial0', 115200
EOF_TAG = '__HITRON_EOF__'

def main():
    local, remote = sys.argv[1], sys.argv[2]
    with open(local, 'rb') as f:
        data = f.read()
    text = data.decode('utf-8', 'replace')

    ser = serial.Serial(PORT, BAUD, timeout=0.1)

    def send(s, wait):
        ser.write(s.encode() if isinstance(s, str) else s)
        ser.flush()
        end = time.time() + wait
        while time.time() < end:
            ser.read(4096)

    ser.reset_input_buffer()
    send('\r', 0.3)
    send(f"cat > {remote} <<'{EOF_TAG}'\r", 0.4)
    for line in text.split('\n'):
        send(line + '\r', 0.06)
    send(f"{EOF_TAG}\r", 0.6)

    # read back md5 from the target
    ser.reset_input_buffer()
    send(f"md5sum {remote}\r", 0.2)
    out = b''
    end = time.time() + 2.0
    while time.time() < end:
        out += ser.read(4096)
    ser.close()

    # target file is LF-joined; a trailing newline may or may not be present.
    remote_md5 = None
    for tok in out.split():
        if len(tok) == 32 and all(c in b'0123456789abcdef' for c in tok):
            remote_md5 = tok.decode(); break

    body = text
    cand = {
        'as-sent (LF, no trailing NL)': hashlib.md5(body.rstrip('\n').encode()).hexdigest(),
        'as-sent (LF, one trailing NL)': hashlib.md5((body.rstrip('\n') + '\n').encode()).hexdigest(),
    }
    sys.stdout.buffer.write(out)
    print(f"\n--- remote md5: {remote_md5}")
    for k, v in cand.items():
        print(f"--- local  md5 {v}  [{k}]  {'MATCH' if v == remote_md5 else ''}")

if __name__ == '__main__':
    main()
