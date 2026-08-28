# Reverting to the as-found state

The Hitron EN2251 was modified in exactly **one** way during rooting: the file
**`/data/.nologin`** was created on the persistent `rgnonvol0` UBIFS volume.
Everything else (`init=/bin/sh`, `XARGS`) was RAM-only and vanished at the first
power cycle.

Removing that one file restores the normal `getty` login prompt and returns the
unit byte-for-byte to how it was found.

## Method A — from the rooted console (simplest)

The board currently drops straight to a root shell (`[3390:RG]#`). Run:

```sh
rm -f /data/.nologin && sync && reboot
```

On the next boot the console shows `(none) login:` again. Done.

## Method B — offline, via the bootloader

Use this only if the login prompt is already back but you want to be sure, or if
`/data` won't mount from the running system. You need physical UART access.

1. Interrupt BOLT on a power cycle: `python3 tools/breakin.py`
2. Drop to a root shell: `python3 tools/bootsh.py`
3. In that shell:

```sh
mkdir /dev/d
ubiattach -m 10 -d 1
mount -t ubifs ubi1:data /dev/d
rm -f /dev/d/.nologin
sync; umount /dev/d; ubidetach -d 1
reboot
```

## What is NOT part of the modem revert

The Raspberry Pi capture host had `dtoverlay=disable-bt` added to
`/boot/firmware/config.txt` (backup: `config.txt.bak-uart-20260828`) to put the
PL011 on GPIO14/15. That is a change to the *Pi*, not the modem, and is unrelated
to reverting the Hitron. Remove that line and reboot the Pi if you want its
Bluetooth/UART back.
