#!/usr/bin/env python3
"""No Bit Sings Alone (HICybercon, steg 500) — full solve.

Usage:
    python3 solve.py suspicious.wav            # recover key + flag
    python3 solve.py suspicious.wav --banner   # dump the spectrogram text as ASCII bitmaps
"""
import sys
import wave

import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

SR = 44100
BLOCK = 4096
FIRST_BLOCK, LAST_BLOCK = 585, 642  # blocks carrying a pure tone in R
P = 257                             # NTT field
OMEGA = 240                         # order-32 root of unity mod 257

# Read off the spectrogram banner (see --banner)
NONCE = bytes.fromhex("99CB9C49E4C83527CE6F89D9")
CT = bytes.fromhex(
    "8A845BA500DE25B749F1FF63CCFF"
    "9D2D9FD8D2614E19BCA42CC7E438"
    "B31407AE896311C3AADCF9327610"
    "478444A09EF6FE3650DF7EBEC3B7"
    "1FF18CF0EB728DBFA791B7485D76"
    "7172AE849328715A10B5"
)


def load(path):
    w = wave.open(path)
    d = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, 2)
    return d[:, 0].astype(np.int64), d[:, 1].astype(np.int64)


def banner(L, R):
    """Banner glyphs: 5x7 font, 1024-sample columns, rows 177.44 Hz apart."""
    x = (L + R).astype(float)
    rows = 18002 - np.arange(63) * 177.44
    t = np.arange(1024)
    E = np.exp(-2j * np.pi * np.outer(rows, t) / SR)
    win = np.hanning(1024)
    o, ncol = 33048, 6 * 35
    M = np.log(np.array([np.abs(E @ (x[o + c * 1024:o + (c + 1) * 1024] * win))
                         for c in range(ncol)]).T + 1)
    B = M > np.median(M) + (M.max() - np.median(M)) * 0.4
    for line in range(8):
        for r in range(7):
            print("".join("#" if B[line * 8 + r, c] else " " for c in range(ncol)))
        print()


def tone_bin(R, m):
    F = np.abs(np.fft.rfft(R[m * BLOCK:(m + 1) * BLOCK].astype(float)))
    F[:836] = 0   # ignore < 9 kHz
    F[-2:] = 0
    return int(F.argmax())


def extract_bits(L, R):
    bits = []
    for m in range(FIRST_BLOCK, LAST_BLOCK + 1):
        k = tone_bin(R, m)
        base = m * BLOCK
        # Hamming(31,26) syndrome; sample j*k mod 4096, column index rotated by -k
        syn = 0
        for i in range(31):
            if L[base + ((i + 1) * k) % BLOCK] & 1:
                syn ^= ((i - k) % 31) + 1
        bits += [(syn >> (4 - j)) & 1 for j in range(5)]
    return bits


def inverse_ntt(vals):
    n = len(vals)
    n_inv = pow(n, P - 2, P)
    return [sum(v * pow(OMEGA, i * j, P) for j, v in enumerate(vals)) * n_inv % P
            for i in range(n)]


def main():
    L, R = load(sys.argv[1] if len(sys.argv) > 1 else "suspicious.wav")
    if "--banner" in sys.argv:
        banner(L, R)
        return
    bits = extract_bits(L, R)
    vals = [int("".join(map(str, bits[t * 9:t * 9 + 9])), 2) for t in range(32)]
    assert all(v < P for v in vals), "extraction wrong: value outside GF(257)"
    key = bytes(inverse_ntt(vals))
    print("key  :", key.hex())
    # GCM keystream = AES-CTR starting at counter 2
    dec = Cipher(algorithms.AES(key), modes.CTR(NONCE + (2).to_bytes(4, "big"))).decryptor()
    pt = dec.update(CT)
    n = int.from_bytes(pt[:2], "big")
    print("flag :", pt[2:2 + n].decode())


if __name__ == "__main__":
    main()
