#!/usr/bin/env python3
"""Shell-Breach (SolarCTF forensics) flag decryptor.

The flag lives in an NTFS alternate data stream:
    Documents/SolarGrid/Reports/report_q3.xlsx:metadata   (44 bytes)

Recover it with:
    unzip solar_forensic.zip
    qemu-img convert -f vpc -O raw disk.vhd disk.raw
    dd if=disk.raw of=part.ntfs bs=512 skip=128 count=128896 status=none
    icat part.ntfs 64-128-4 > ads.bin
    python3 solve.py ads.bin

The XOR key is the repeating 6-byte value ``aa bb cc 11 22 33`` -- the
fabricated Droid/ObjectID tail from drop_link.lnk's TrackerDataBlock
(0xA0000003) in Documents/SolarGrid/Export/.
"""
import sys

KEY = bytes.fromhex("aabbcc112233")
KNOWN_ADS = bytes.fromhex(
    "f9f480507070fefdb7624a00c6d7ae25"
    "456cc78fa264435ff5cbad635102c4dc"
    "9378516cded3ff4e5507d3c6"
)


def xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def main() -> int:
    if len(sys.argv) > 1:
        data = open(sys.argv[1], "rb").read()
    else:
        print("[*] no file given, using the known ADS bytes", file=sys.stderr)
        data = KNOWN_ADS
    flag = xor(data, KEY).decode("utf-8")
    print(flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
