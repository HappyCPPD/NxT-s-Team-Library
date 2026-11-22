#!/usr/bin/env python3
"""Soul's Whisper (Byteme2026, RE, 100 pts) - static solver.

Two secrets in the binary:
  1. main() compares the user input against a local 5-byte string built with
     `mov DWORD PTR [rbp-0x55], 0x6c756f73` -> little-endian "soul".
  2. On a match it calls soul_stone(), which assembles the flag on the stack
     from four 8-byte `movabs` immediates (overlapping writes at -0x70/-0x68/
     -0x63/-0x5b) and printf("Flag: %s").
This solver decodes the flag from the immediates WITHOUT running the binary.
"""
import struct

# immediates as they appear in soul_stone (address -> 64-bit value)
CHUNKS = [
    (0x70, 0x68747b505341574f),  # movabs rax -> "OWASP{th" @ rbp-0x70
    (0x68, 0x735f6c7530735f33),  # movabs rdx -> "3_s0ul_s" @ rbp-0x68
    (0x63, 0x5f336e3074735f6c),  # movabs rax -> "l_st0n3_" @ rbp-0x63
    (0x5b, 0x7d72337073316877),  # movabs rdx -> "wh1sp3r}" @ rbp-0x5b
]
# rbp-relative offsets overlap by design (3rd chunk re-writes bytes it shares
# with the 2nd); resolve by reading byte-by-byte with later chunks winning.
BY, N = {}, 0x1C  # loop copies 0..0x1C inclusive = 29 bytes; NUL at rbp-0x33
for off, val in CHUNKS:
    for i, b in enumerate(struct.pack("<Q", val)):
        BY[off - i] = b

flag = bytes(BY[0x70 - i] for i in range(N + 1)).decode()
assert flag.startswith("OWASP{") and flag.endswith("}")
print(flag)
