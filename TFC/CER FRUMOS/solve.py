#!/usr/bin/env python3

from hashlib import sha256
from Crypto.Cipher import AES
from z3 import BitVec, BitVecVal, Extract, If, LShR, Solver, sat

N, M = 624, 397
A = BitVecVal(0x9908B0DF, 32)
UPPER = BitVecVal(0x80000000, 32)
LOWER = BitVecVal(0x7FFFFFFF, 32)


def twist(state):
    # This mirrors the in-place loops in CPython's _randommodule.c.
    s = list(state)
    for i in range(N - M):
        y = (s[i] & UPPER) | (s[i + 1] & LOWER)
        s[i] = s[i + M] ^ LShR(y, 1) ^ If((y & 1) == 1, A, BitVecVal(0, 32))
    for i in range(N - M, N - 1):
        y = (s[i] & UPPER) | (s[i + 1] & LOWER)
        s[i] = s[i + (M - N)] ^ LShR(y, 1) ^ If((y & 1) == 1, A, BitVecVal(0, 32))
    y = (s[N - 1] & UPPER) | (s[0] & LOWER)
    s[N - 1] = s[M - 1] ^ LShR(y, 1) ^ If((y & 1) == 1, A, BitVecVal(0, 32))
    return s


def temper(y):
    y = y ^ LShR(y, 11)
    y = y ^ ((y << 7) & 0x9D2C5680)
    y = y ^ ((y << 15) & 0xEFC60000)
    return y ^ LShR(y, 18)


lines = open("out.txt").read().splitlines()
samples = [int(x) for x in lines[:-1]]
enc = bytes.fromhex(lines[-1].split(": ", 1)[1])

state = [BitVec(f"s{i}", 32) for i in range(N)]
solver = Solver()
idx = 0


def next_word():
    global state, idx
    if idx == N:
        state = twist(state)
        idx = 0
    out = temper(state[idx])
    idx += 1
    return out


for x in samples:
    solver.add(next_word() == (x & 0xFFFFFFFF))
    solver.add(Extract(31, 16, next_word()) == (x >> 32))
    next_word()  # discarded 16-bit call

for _ in range(10):
    next_word()

key_lo, key_hi = next_word(), next_word()
iv_lo, iv_hi = next_word(), next_word()

assert solver.check() == sat
model = solver.model()
u32 = lambda e: model.eval(e, model_completion=True).as_long()
key_seed = u32(key_lo) | (u32(key_hi) << 32)
iv_seed = u32(iv_lo) | (u32(iv_hi) << 32)
key = sha256(str(key_seed).encode()).digest()
iv = sha256(str(iv_seed).encode()).digest()[:16]
flag = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(enc)
print("key seed:", key_seed)
print("iv seed:", iv_seed)
print("plaintext:", flag)
