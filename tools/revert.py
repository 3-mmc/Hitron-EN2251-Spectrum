#!/usr/bin/env python3
"""Revert the persistent root: remove /data/.nologin so the console returns to
the normal getty login prompt.

Two ways to revert, easiest first:

  A) From the rooted console (the board already drops you to [3390:RG]# root):
         rm -f /data/.nologin && sync && reboot
     Done. Nothing else was ever changed on the modem.

  B) If the console login has somehow been restored but you still have the
     bootloader (BOLT) access, re-enter the init=/bin/sh root shell with
     tools/bootsh.py, then run this script's OFFLINE routine, which re-attaches
     the rgnonvol0 UBI volume and deletes the file:

         mkdir /dev/d
         ubiattach -m 10 -d 1
         mount -t ubifs ubi1:data /dev/d
         rm -f /dev/d/.nologin
         sync; umount /dev/d; ubidetach -d 1
         reboot

This file is documentation-as-code; it is meant to be read, and the block below
prints the exact commands. It intentionally does NOT execute anything, because
reverting is a deliberate act you run on the target's own console, not from the
capture host.
"""

ROOTED_CONSOLE = "rm -f /data/.nologin && sync && reboot"

OFFLINE_FROM_BOLT = """\
# 1. Break into BOLT on a power cycle:      python3 tools/breakin.py
# 2. Drop to a root shell:                  python3 tools/bootsh.py
# 3. In that shell, remove the marker from the persistent data volume:
mkdir /dev/d
ubiattach -m 10 -d 1
mount -t ubifs ubi1:data /dev/d
rm -f /dev/d/.nologin
sync; umount /dev/d; ubidetach -d 1
reboot
"""

if __name__ == "__main__":
    print("=== Revert method A: from the rooted console (simplest) ===")
    print("    " + ROOTED_CONSOLE)
    print()
    print("=== Revert method B: offline via BOLT + init=/bin/sh ===")
    print(OFFLINE_FROM_BOLT)
    print("After either method the console returns to the '(none) login:' getty "
          "prompt and the modem is byte-for-byte back to its as-found state.")
