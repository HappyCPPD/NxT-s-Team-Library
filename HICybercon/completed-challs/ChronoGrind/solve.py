#!/usr/bin/env python3
"""ChronoGrind: parse CGD1 state.dat, verify chk, derive key, open CGFX container."""
import hashlib, sys

SD = "ChronoGrind/extracted/chronogrind/state.dat"
FE = "ChronoGrind/extracted/chronogrind/flag.enc"

raw = open(SD, "rb").read()
assert raw[:4] == b"CGD1"
body = bytes(c ^ 0x4C for c in raw[4:])          # body obfuscation

fields = {}
i = 2                                            # body header is 2 bytes
while i + 5 <= len(body):
    tag = body[i]
    ln = int.from_bytes(body[i + 1:i + 5], "little")
    fields[tag] = body[i + 5:i + 5 + ln]
    i += 5 + ln
print("tags:", [hex(t) for t in fields])

def base241(b):
    v = 0
    for by in b:
        assert by <= 240, f"digit {by} >= 241"
        v = v * 241 + by
    return v

anchor = base241(fields[0x11])
seed = base241(fields[0x22])
cycles = int(fields[0x33].decode())
chk = fields[0x44]

print("anchor bits:", anchor.bit_length())
print("seed bits:  ", seed.bit_length())
print("cycles:     ", cycles)
calc_chk = hashlib.sha256(f"{anchor}:{seed}:{cycles}".encode()).digest()[:8]
print("chk match:  ", calc_chk == chk, calc_chk.hex(), chk.hex())

# primality
def is_probable_prime(n, k=40):
    if n < 2: return False
    for p in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n % p == 0: return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2; r += 1
    import random
    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1: break
        else:
            return False
    return True

prime = is_probable_prime(anchor)
print("anchor probably prime:", prime)

# v = seed iterated: v_{n+1} = v_n^2 mod anchor  =>  v_cycles = seed^(2^cycles) mod anchor
if prime:
    e = pow(2, cycles, anchor - 1)               # Fermat
    v = pow(seed, e, anchor)
    print("reduced exponent bits:", e.bit_length())
else:
    raise SystemExit("anchor not prime - need Carmichael/loop fallback")

# sanity: iterate a small number of steps and compare with the pow formula for test
import time
t0 = time.time()
vv = seed
for _ in range(1000):
    vv = vv * vv % anchor
tight = vv
chk_exp = pow(seed, pow(2, 1000, anchor - 1 if prime else 1 << 62), anchor) if prime else None
print("small-step check:", tight == chk_exp, f"({time.time()-t0:.2f}s for 1000 steps)")

k = hashlib.sha256(v.to_bytes(256, "big")).digest()
print("key:", k.hex())

# --- open CGFX -------------------------------------------------------------
d = open(FE, "rb").read()
print("flag.enc:", len(d), d[:5])
assert d[:4] == b"CGFX"
ver = d[4]
nonce = d[5:17]
tag = d[17:33]
ct = d[33:]
print("ver", ver, "nonce", nonce.hex(), "tag", tag.hex(), "ct", len(ct))

try:
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
    pt = ChaCha20Poly1305(k).decrypt(nonce, ct + tag, None)
    print("PLAINTEXT:", pt)
except ImportError:
    try:
        from Crypto.Cipher import ChaCha20_Poly1305
        c = ChaCha20_Poly1305.new(key=k, nonce=nonce)
        pt = c.decrypt_and_verify(ct, tag)
        print("PLAINTEXT:", pt)
    except ImportError:
        print("no AEAD lib; key computed above")
