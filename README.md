# Hitron EN2251 (Spectrum / Charter) — UART root

Notes, boot logs, and tooling from rooting a **Hitron EN2251** DOCSIS 3.1
cable gateway over its UART serial console. The board was rescued from e-waste
and is being repurposed; this repo documents exactly what was done so the single
persistent change can be reverted and the unit returned to its as-found state.

The retail badge says *Hitron*; the silicon and firmware are **Broadcom + Ubee**,
with a **Charter/Spectrum** firmware build.

---

## TL;DR

- **SoC:** Broadcom **BCM3390B0** — 2× Cortex-A15 @ 1503 MHz, 933 MHz DDR, 512 MB
- **Board ID:** `BCM93390VVCM`
- **Bootloader:** BOLT **v5.03** (built 2021-08-05), **secure boot enforced**
- **OS:** Linux **4.9.248-Prod_21.2**, squashfs-on-UBI rootfs, BusyBox userspace
- **Firmware build:** `21.2_charter_1325` (Ubee build host, Charter/Spectrum)
- **Flash:** 256 MB Winbond NAND (W29N02KV), 20 MTD partitions
- **Console:** GPIO UART, **115200 8N1**, 3.3 V
- **Factory WAN MAC:** `A0:ED:6D:9D:71:E3` (recovered from `router-perm.config`;
  the `macadr` NAND partition itself has a failed checksum)

**Root method, one line:** BOLT's autoboot can be interrupted with Ctrl-C to reach
an unlocked `BOLT>` CLI. Secure boot authenticates the kernel and DTB but **not
the bootloader-appended kernel command line**, so setting `XARGS=init=/bin/sh`
and booting drops straight to a `uid=0` shell on the authenticated rootfs.

**Persistence, one line:** the login program (`/bin/loginscript.sh`) spawns a
passwordless root shell instead of `getty` if the file **`/data/.nologin`** exists
on the persistent data partition. Creating that one file gives a root console on
every normal cold boot — no bootloader interaction required — and deleting it
reverts everything.

---

## Hardware / wiring

The capture host here is a Raspberry Pi 4B driving the modem's TTL serial console.

| Modem console pad | → | Pi 40-pin header |
|---|---|---|
| TX | → | GPIO15 / RXD, phys pin 10 |
| RX | → | GPIO14 / TXD, phys pin 8 |
| GND | → | any GND (e.g. phys pin 6) |

Levels are **3.3 V**. UART idles high, so the pad's idle voltage measured against
the board's own ground = the logic level — check it before wiring the Pi's TX.

On the Pi, the real PL011 was moved onto GPIO14/15 (off the mini-UART) with
`dtoverlay=disable-bt` so the console is jitter-free; `/dev/serial0 → ttyAMA0`.
The Linux serial console on the Pi stays disabled so nothing else touches the port.

---

## The boot chain (from the logs)

`logs/first-full-boot.log` is the untouched first capture. Highlights:

```
BCM33900010  BOLT v5.03 v5.03_B1
MARKET ID VALIDATION : Generic Mode - PASS
Secure boot detected
DDR SCRAMBLER ENABLED
SSBL INTEGRITY: OK
SSBL AUTHENTICATION: OK
Board: BCM93390VVCM
CPU: 2x A15, 1503 MHz
MAC ADDRESS CHECKSUM FAILED
MAC ADDRESS MUST BE PROGRAMMED; use macprog command
Linux version 4.9.248-Prod_21.2 (ubee@ubee-B560M-AORUS-ELITE) ... Thu Aug 25 2022
```

Two anti-tamper monitors start in userspace and are the reason **the login prompt
was never brute-forced**:

```
Start monitoring Abnormal JTAG usage
Start monitoring UartRxCnt, beginning RxCnt set to 0 ...   # counts console RX bytes
```

The board boots all the way to `(none) login:` — a BusyBox `getty`. There is no
`/etc/shadow`; auth is Broadcom's custom scheme, so guessing was a dead end.

### The 20 NAND partitions (`/proc/mtd`)

```
mtd0  flash0.fsbl       mtd7  flash0.devtree1   mtd14 flash0.cm0
mtd1  flash0.ssbl0      mtd8  flash0.cmnonvol0  mtd15 flash0.cm1
mtd2  flash0.ssbl1      mtd9  flash0.cmnonvol1  mtd16 flash0.debug
mtd3  flash0.macadr     mtd10 flash0.rgnonvol0  mtd17 flash0.rg0   (rootfs UBI)
mtd4  flash0.nvram      mtd11 flash0.rgnonvol1  mtd18 flash0.rg1
mtd5  flash0.nvram1     mtd12 flash0.kernel0    mtd19 flash0        (whole device)
mtd6  flash0.devtree0   mtd13 flash0.kernel1
```

`/data` = **mtd10 `flash0.rgnonvol0`**, a UBIFS volume named `data`. `/data_bak`
is `flash0.rgnonvol1`.

---

## Root, step by step

Everything is driven from the Pi with the small scripts in `tools/`. None of them
write to the port except where noted; the capture/scan tools are listen-only and
cannot interrupt the bootloader by accident.

### 1. Find the baud and capture a clean boot
```
python3 tools/baudscan.py -d 4 -r 3     # start, then power the board (answer: 115200)
python3 tools/capture.py  -b 115200     # listen-only, timestamped log to logs/
```

### 2. Interrupt BOLT
```
python3 tools/breakin.py                # start, then power-cycle the board
```
`breakin.py` floods Ctrl-C during the boot window. BOLT aborts its `STARTUP`
script and drops to `BOLT>`. The CLI is fully unlocked (`help`, `printenv`,
`setenv`, flash read/erase, `dt` DTB editing, `ukey`, etc.).

The critical detail in `printenv` — `STARTUP` ends with an unset **`$XARGS`**
that is appended verbatim to the kernel command line:

```
STARTUP = load -nz -raw -addr=$DT_ADDRESS ... flash0.devtree$DT_IDX;$PREBOOT;
          boot flash0.kernel$KL_IDX "ubi.mtd=flash0.rg$RG_IDX ubi.block=0,rootfs
          rootfstype=squashfs root=/dev/ubiblock0_0 ro platformboot
          ubifs_data coherent_pool=1M $XARGS"
```

### 3. Boot to a root shell
```
python3 tools/bootsh.py                 # sets XARGS=init=/bin/sh (RAM only) and boots
```
Result:
```
VFS: Mounted root (squashfs filesystem) readonly on device 254:0.
sh-3.2# id
uid=0 gid=0
```
`setenv` without `-p` is RAM-only, so this leaves **nothing** on the device — a
power cycle fully reverts it. Secure boot is not defeated; the cmdline simply
isn't part of the signed payload.

### 4. Make it persistent (the only on-device change)
From the `init=/bin/sh` shell, mount the persistent data volume and drop the
`.nologin` marker that `loginscript.sh` checks:

```sh
mkdir /dev/d                            # /tmp is read-only squashfs; /dev is devtmpfs
ubiattach -m 10 -d 1                    # attach flash0.rgnonvol0
mount -t ubifs ubi1:data /dev/d
echo booted-by-owner > /dev/d/.nologin
sync; umount /dev/d; ubidetach -d 1
```

`/bin/loginscript.sh` (verbatim from the rootfs):
```sh
#!/bin/bash
NOLOGIN=/data/.nologin
if [ -f "$NOLOGIN" ]; then
    /bin/cttyhack /bin/sh -l            # passwordless root shell
else
    /sbin/getty -L 115200 ttyS0 vt102   # normal login prompt
fi
```

### 5. Confirm on a clean boot
After a normal power-on (no bootloader hack, clean `/proc/cmdline`):
```
[3390:RG]# id
uid=0(root) gid=0(root)
[3390:RG]# cat /proc/cmdline
ubi.mtd=flash0.rg0 ubi.block=0,rootfs rootfstype=squashfs root=/dev/ubiblock0_0 ro platformboot ubifs_data coherent_pool=1M
```
Root, on the full running gateway, with all services up and `/data` mounted rw by
the firmware's own init.

---

## Reverting

The modem was changed in exactly **one** way: the file `/data/.nologin` was
created. To undo it, from the rooted console:

```sh
rm -f /data/.nologin && sync && reboot
```

The console returns to the `(none) login:` getty and the unit is byte-for-byte
as found. See `tools/revert.py` (also covers the offline-via-BOLT route) and
[`REVERT.md`](REVERT.md).

---

## `tools/`

| Script | Writes to port? | Purpose |
|---|---|---|
| `baudscan.py` | no | Sweep common bauds, score which yields sane text |
| `capture.py`  | no | Listen-only timestamped boot capture (`.bin` + `.log`) |
| `breakin.py`  | yes (Ctrl-C flood) | Interrupt BOLT autoboot to reach `BOLT>` |
| `talk.py`     | yes | Send lines and print the reply (send-expect helper) |
| `bootsh.py`   | yes | Set `XARGS=init=/bin/sh` and boot to a root shell |
| `revert.py`   | no | Prints the exact revert commands |

---

## Notes & safety

- Nothing here targets a network. The `macadr` partition checksum fails, so the
  unit won't register on a DOCSIS plant; this is purely local hardware reuse.
- Per-chip secrets were left alone — the BOLT `ukey` was never dumped. The only
  identifier recorded is the board's own WAN MAC.
- Secure boot remains intact and enforced; nothing was reflashed. The root relies
  on an unsigned kernel cmdline and a stock login-script behaviour, both reversible.
