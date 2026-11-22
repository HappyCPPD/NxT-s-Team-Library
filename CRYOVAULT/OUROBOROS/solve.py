#!/usr/bin/env python3
"""
OUROBOROS (CRYOVAULT) solver.

The binary reads 32 bytes, then for each of 4 blocks JIT-compiles a small
function into an RWX mmap.  The generated code is  template[b] XOR keystream,
where the keystream is a splitmix64 stream keyed by seed = word[b] ^ state.
Before executing, the code is hashed by a splitmix chain and must equal a
stored constant, E[b].  The chain is a 64-bit preimage guard (infeasible by
search), BUT the generated code is a clean compiled C function sharing a
fixed prologue.  Knowing its first 8 bytes (the prologue) is a known-plaintext
that reveals keystream group 0 -> seed -> the entire 85..96 byte program ->
word[b] = seed ^ state.  Ouroboros eats its own tail: the code tells you the key.

Output: isfcr{c0d3_th4t_3ats_1ts_t41l!!}
"""
import struct, subprocess, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
CHALL = os.path.join(HERE, "chall")

data = open(CHALL, "rb").read()
rd = lambda v, n: data[v - 0x400000:v - 0x400000 + n]

M = (1 << 64) - 1
G  = 0x9e3779b97f4a7c15              # splitmix64 gamma (also the chain's step add)
M1 = 0xbf58476d1ce4e5b9
M2 = 0x94d049bb133111eb
invM1, invM2 = pow(M1, -1, 1 << 64), pow(M2, -1, 1 << 64)

def _unxorshift(y, s):
    x = y
    for _ in range(6):
        x = y ^ (x >> s)
    return x & M

def mix(x):
    x &= M; x ^= x >> 30; x = (x * M1) & M; x ^= x >> 27
    x = (x * M2) & M; x ^= x >> 31
    return x & M

def mixinv(y):
    y &= M; y = _unxorshift(y, 31); y = (y * invM2) & M
    y = _unxorshift(y, 27); y = (y * invM1) & M; y = _unxorshift(y, 30)
    return y

TEMPL_PTR = [0x401520, 0x4014c0, 0x401460, 0x401400]   # .rodata template pointers
TEMPL_LEN = [0x55, 0x5d, 0x60, 0x55]                    # 85, 93, 96, 85
TEMPL = [rd(TEMPL_PTR[b], TEMPL_LEN[b]) for b in range(4)]
E     = [int.from_bytes(rd(0x4013a0 + 8 * b, 8), "little") for b in range(4)]  # stored code hashes
C0    = 0xc0ffeebadc0de5                                # chain seed
STATE0 = 0x1f0d1e5cafeb00b5                             # r9 initial state
PROLOGUE = bytes([0xf3, 0x0f, 0x1e, 0xfa, 0x55, 0x48, 0x89, 0xe5])  # endbr64; push rbp; mov rbp,rsp

def keystream(seed, nbytes):
    """splitmix64 stream: group g = mix(seed + (g+1)*G), bytes taken LE."""
    ng = (nbytes + 7) // 8
    return [mix((seed + (g + 1) * G) & M) for g in range(ng)]

def gen(b, state, word):
    """Reproduce the binary's code generator."""
    seed = (word ^ state) & M
    vs = keystream(seed, TEMPL_LEN[b])
    return bytes(TEMPL[b][i] ^ ((vs[i // 8] >> (8 * (i % 8))) & 0xff) for i in range(TEMPL_LEN[b]))

def chain(code, init):
    """splitmix chain hash used by the guard: h <- mix((c ^ h) + G)."""
    h = init
    for c in code:
        h = mix(((c ^ h) + G) & M)
    return h

def recover(b, state):
    """Known-plaintext attack: assume the generated code starts with the shared
    prologue; derive keystream group 0 -> seed -> full program -> word."""
    k0 = bytes(PROLOGUE[i] ^ TEMPL[b][i] for i in range(8))   # first group of keystream
    v0 = int.from_bytes(k0, "little")
    seed = (mixinv(v0) - G) & M
    code = gen(b, 0, seed)                                    # state=0 => seed==word
    word = (seed ^ state) & M
    assert chain(code, C0) == E[b], "guard mismatch on block %d" % b
    return word, code

def main():
    flag, state = b"", STATE0
    codes = []
    for b in range(4):
        w, code = recover(b, state)
        flag += w.to_bytes(8, "little")
        codes.append(code)
        state = chain(code, state)
    flag = flag.rstrip(b"\x00")
    print("recovered 32 bytes :", flag)
    print("flag               :", flag.decode())
    for b, code in enumerate(codes):
        print("block %d program (%3d bytes): %s" % (b, len(code), code.hex()))

    # ground truth: drive the real binary
    try:
        r = subprocess.run([CHALL], input=flag, capture_output=True, timeout=10)
        print("binary says        :", r.stdout.decode().strip(), "(exit %d)" % r.returncode)
    except Exception as ex:
        print("binary check skipped:", ex)

if __name__ == "__main__":
    main()
