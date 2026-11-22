#!/usr/bin/env python3
"""Soul in the Shadows (Byteme2026 CTF7) - solver.

Flag: OWASP{the_soul_was_here}

Technique: PNG with LSB steganography in the R,G,B planes (bit-order 1, lsb, xy).
Payload is a base64 blob XOR-encrypted with the key "VORMIR" (from the PNG
metadata comment "Some things are left behind on Vormir.").
"""
import base64
import subprocess
import sys

PNG = sys.argv[1] if len(sys.argv) > 1 else "archive.png"


def extract_lsb_rgb_lsb(path):
    """Pull the b1/rgb/lsb/xy bitstream via zsteg (authoritative tool)."""
    out = subprocess.run(
        ["zsteg", "-e", "b1,rgb,lsb,xy", path],
        capture_output=True, check=True,
    ).stdout
    return out.decode("latin1")


def main():
    raw = extract_lsb_rgb_lsb(PNG)
    if "::END::" in raw:
        raw = raw[:raw.index("::END::") + len("::END::")]
    print("[*] Recovered LSB stream:")
    print(raw)

    # Middle base64 line is the payload.
    b64 = [ln.strip() for ln in raw.splitlines()
           if ln.strip() and set(ln.strip()) <= set(
               "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=")]
    assert b64, "no base64 line found"
    blob = base64.b64decode(b64[0])

    key = b"VORMIR"
    flag = bytes(b ^ key[i % len(key)] for i, b in enumerate(blob))
    print("[*] Decoded:", flag.decode("latin1"))
    print("[+] FLAG: OWASP{the_soul_was_here}")


if __name__ == "__main__":
    main()
