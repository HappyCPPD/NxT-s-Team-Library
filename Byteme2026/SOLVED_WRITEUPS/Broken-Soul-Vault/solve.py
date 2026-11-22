#!/usr/bin/env python3
"""Broken Soul Vault (Byteme 2026, Forensics/Easy) solver.

The recovered metadata is a small text file:
    line 1 : 00ff11aa      -> block-start marker
    line 2 : <hex string>  -> recovered payload (ASCII hex)
    line 3 : deadbeef      -> block-end marker

The vault log shows two recovery attempts (block=17, block=18) and a
"corrupted metadata follows" note. Only one block carries a well-formed
OWASP{...} payload, so we hex-decode line 2 and validate the flag format.
"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "metadata.bin.txt"

with open(path) as f:
    raw = f.read()

lines = [l.strip() for l in raw.splitlines() if l.strip()]
print("[*] metadata lines:", lines)

payload = None
for l in lines:
    # candidate = long, even-length, pure-hex line
    if len(l) % 2 == 0 and re.fullmatch(r"[0-9a-fA-F]+", l) and len(l) >= 16:
        blob = bytes.fromhex(l)
        text = blob.decode("latin1", "replace")
        print(f"[*] block {l[:8]}... -> {text}")
        if re.search(r"OWASP\{.*\}", text):
            payload = text

print()
print("[+] FLAG:", payload)
