#!/usr/bin/env python3
"""
FS-Enc (platypwnies 2026) — flag recovery.

Vulnerability: fs-enc derives key material with Argon2 and then STORES it in the
output file in plaintext.  File layout (verified with gdb + controlled files):

    magic(12) || key(32) || nonce(12) || ciphertext || tag(16)
    565fe6937919ad6a113d0240

gdb on <argon2::Argon2>::hash_password_into for a vault created with the known
password "testpass" showed:
    salt = 16 bytes = magic(12) || magic[0:4]      (NOT stored-random)
    out_len = 44 = 32-byte ChaCha20 key || 12-byte Poly1305 nonce
and bytes 12..56 of the file are exactly that Argon2 output.

Therefore: no password is required.  Use the stored key/nonce directly.

Usage: python3 fsenc_solve.py flag.bin
"""
import sys
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

def decrypt(path):
    d = open(path, 'rb').read()
    magic = d[:12]
    key, nonce = d[12:44], d[44:56]
    ct, tag = d[56:-16], d[-16:]
    pt = ChaCha20Poly1305(key).decrypt(nonce, ct + tag, None)
    return magic, key, nonce, pt

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "flag.bin"
    magic, key, nonce, pt = decrypt(p)
    print(f"[*] magic = {magic.hex()}   (also the Argon2 salt prefix)")
    print(f"[*] stored key   = {key.hex()}")
    print(f"[*] stored nonce = {nonce.hex()}")
    print(f"[+] plaintext    = {pt!r}")
