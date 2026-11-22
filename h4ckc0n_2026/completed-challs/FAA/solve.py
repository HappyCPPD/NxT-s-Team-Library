#!/usr/bin/env python3
"""
FAA (h4ckc0n 2026, Forensics 500) — complete solve, challenge data -> flag.

Chain:
  1. JPEG metadata  -> 6 Shamir shares over GF(2^521-1) (threshold 3)  -> 264-bit prime
  2. steghide payload, password = ROT13(unsplash photo id "WAWyV76C3t8") = "JNJlI76P3g8"
  3. payload: XZ -> base64 -> JSFuck -> obfuscated JS  (custom byte cipher)
  4. decrypt the 43-byte ciphertext with the prime (DECIMAL form) -> flag

Usage:  python3 solve.py <chall-image/benjamin-chambon-WAWyV76C3t8-unsplash.jpg>
Requires: stegseek or steghide on PATH (or notes/bin/stegseek) for step 2; node for step 3.
"""
import base64, hashlib, lzma, re, struct, subprocess, sys, os, shutil, tempfile

# ---------------------------------------------------------------- 1. Shamir
Q = (1 << 521) - 1                      # Mersenne prime 2^521-1 (proven by gcd-of-consistency)
THRESHOLD = 3

def _b32(s): return base64.b32decode(s.upper() + "=" * ((8 - len(s) % 8) % 8))
def _b36(s):
    n = 0
    for c in s: n = n * 36 + int(c, 36)
    return n.to_bytes((n.bit_length() + 7) // 8, "big")

def parse_segments(data):
    segs, p = [], 2
    while p < len(data) - 1:
        if data[p] != 0xFF: p += 1; continue
        m = data[p + 1]
        if m in (0xD8, 0xD9) or 0xD0 <= m <= 0xD7 or m == 0x01: p += 2; continue
        if m == 0xDA: break
        L = struct.unpack(">H", data[p + 2:p + 4])[0]
        segs.append((m, data[p + 4:p + 2 + L])); p += 2 + L
    return segs

def recover_prime(jpg):
    data = open(jpg, "rb").read()
    segs = parse_segments(data)
    shares = {}
    for m, pl in segs:
        try:
            if m == 0xEB:   v = _b32(pl[4:].decode())                       # APP12 base32
            elif m == 0xEC: v = _b36(pl[4:].decode())                       # APP11 base36
            elif m == 0xEF: continue                                        # APP15 = 'F' blob, not a share
            elif m == 0xE0: v = pl[14:]                                     # JFIF extra 69 bytes (raw)
            elif m == 0xE1 and pl.startswith(b"Exif"):
                v = base64.b85decode(pl[pl.find(b"ASCII\x00\x00\x00") + 8:])  # UserComment base85
            elif m == 0xE1:
                v = base64.b64decode(re.search(rb"xmp:Label=\"([^\"]+)\"", pl).group(1))  # XMP base64
            else: continue
        except Exception: continue
        if len(v) == 69 and hashlib.sha256(v[:67]).digest()[:2] == v[67:69]:
            shares[v[0]] = int.from_bytes(v[1:67], "big")                   # checksum validated
    # trailer after EOI = ascii85 share
    tail = data[data.rfind(b"\xff\xd9") + 2:]
    v = base64.a85decode(tail)
    if len(v) == 69 and hashlib.sha256(v[:67]).digest()[:2] == v[67:69]:
        shares[v[0]] = int.from_bytes(v[1:67], "big")
    idx = sorted(shares)[:THRESHOLD]
    # Lagrange interpolation at x=0
    secret = 0
    for i, xi in enumerate(idx):
        num = den = 1
        for xj in idx:
            if xj == xi: continue
            num = num * (-xj) % Q
            den = den * (xi - xj) % Q
        secret = (secret + shares[xi] * num * pow(den, -1, Q)) % Q
    return secret

# ---------------------------------------------------------------- 2. steghide
def extract_steg(jpg, out_xz):
    pw = base64.b32decode  # unused
    password = "JNJlI76P3g8"            # = ROT13("WAWyV76C3t8")
    wl = out_xz + ".wl"
    open(wl, "w").write(password + "\n")
    for exe in ("stegseek", "notes/bin/stegseek", "../notes/bin/stegseek"):
        path = exe if os.path.exists(exe) else shutil.which(exe)
        if path:
            subprocess.run([path, "-q", jpg, wl, out_xz], check=True)
            os.remove(wl)
            return
    if shutil.which("steghide"):
        subprocess.run(["steghide", "extract", "-sf", jpg, "-p", password, "-xf", out_xz], check=True)
        return
    raise SystemExit("need stegseek or steghide on PATH for the steghide step")

# ---------------------------------------------------------------- 3. layers
def jsfuck_to_obfuscated(jsfuck_path):
    # JSFuck is:  <Array.proto.at.constructor>("return eval")()( <INNER> )
    # The last top-level call argument (INNER) evaluates to the obfuscated JS source.
    s = open(jsfuck_path, "r").read()
    depth, calls, i = 0, [], 0
    while i < len(s):
        c = s[i]
        if c == "[": depth += 1
        elif c == "]": depth -= 1
        elif c == "(" and depth == 0:
            d, j = 0, i
            while j < len(s):
                if s[j] == "(": d += 1
                elif s[j] == ")":
                    d -= 1
                    if d == 0: break
                j += 1
            calls.append((i, j)); i = j
        i += 1
    a, b = calls[-1]
    inner = s[a + 1:b]
    tmp = jsfuck_path + ".inner"
    open(tmp, "w").write(inner)
    js = ("process.stdout.write(eval(require('fs').readFileSync(%r,'utf8')));" % tmp)
    return subprocess.run(["node", "-e", js], capture_output=True, check=True).stdout

# ---------------------------------------------------------------- 4. cipher
MASK64 = (1 << 64) - 1
GOLDEN_GAMMA = 0x9E3779B97F4A7C15
CHECKSUM_LENGTH = 4
CIPHER_BYTES = [126,120,134,76,92,84,146,16,121,17,151,240,230,181,137,153,166,146,210,58,
                239,48,109,117,183,117,157,123,57,12,59,78,2,117,197,212,90,79,49,169,79,23,119]

def hash_text(s: str) -> int:
    h = 0xCBF29CE484222325
    for b in s.encode("utf8"):
        h ^= b
        h = (h * 0x100000001B3) & MASK64
    return h

def make_random(seed):
    st = seed
    def nxt():
        nonlocal st
        st = (st + GOLDEN_GAMMA) & MASK64
        z = st
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)
    return nxt

def build_box(rng):
    box = list(range(256))
    for i in range(255, 0, -1):
        j = rng() % (i + 1)
        box[i], box[j] = box[j], box[i]
    return box

def invert_box(box):
    inv = [0] * 256
    for i, v in enumerate(box): inv[v] = i
    return inv

def rot_left(x, r): return ((x << r) | (x >> (8 - r))) & 255

def op_xor(a, k): return a ^ k["xorKey"] ^ k["previousPlainByte"]
def op_add_undo(a, k): return (a - k["addKey"] + 256) & 255
def op_rot_undo(a, k): return rot_left(a, 8 - k["rotation"])

ORDERS = [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]
UNDO = {0: op_xor, 1: op_add_undo, 2: op_rot_undo}

def derive_round_keys(rng, prev_plain):
    r = rng()
    return {"previousPlainByte": prev_plain,
            "xorKey": r & 0xFF,
            "addKey": (r >> 8) & 0xFF,
            "rotation": (r >> 16) % 7 + 1,
            "order": ORDERS[(r >> 24) % 6]}

def compute_checksum(body):
    h = hash_text(bytes(body).decode("latin1"))
    return [(h >> (i * 8)) & 0xFF for i in range(CHECKSUM_LENGTH)]

def decrypt_bytes(data, key):
    rng = make_random(hash_text(key))
    inv = invert_box(build_box(rng))
    prev, out = 0, []
    for b in data:
        k = derive_round_keys(rng, prev)
        v = inv[b]
        for op in reversed(k["order"]):
            v = UNDO[op](v, k)
        prev = v
        out.append(v)
    return out

def decrypt_payload(data, key):
    dec = decrypt_bytes(data, key)
    body, chk = dec[:-CHECKSUM_LENGTH], dec[-CHECKSUM_LENGTH:]
    return bytes(body).decode("utf8") if compute_checksum(body) == chk else None

# ---------------------------------------------------------------- main
def main():
    jpg = sys.argv[1]
    prime = recover_prime(jpg)
    print("[1] prime (dec) =", prime)
    print("[1] prime (hex) =", "%x" % prime)

    with tempfile.TemporaryDirectory() as td:
        xz = os.path.join(td, "payload.xz")
        extract_steg(jpg, xz)
        print("[2] steghide payload:", os.path.getsize(xz), "bytes (XZ)")
        raw = lzma.decompress(open(xz, "rb").read())
        print("[3] xz -> base64 text:", len(raw), "bytes")
        jsfuck = os.path.join(td, "layer.jsfuck")
        open(jsfuck, "wb").write(base64.b64decode(b"".join(raw.split())))
        print("[3] base64 -> JSFuck:", os.path.getsize(jsfuck), "bytes")
        obf = jsfuck_to_obfuscated(jsfuck)
        print("[3] JSFuck -> obfuscated JS:", len(obf), "bytes")

    flag = decrypt_payload(CIPHER_BYTES, str(prime))
    print("[4] flag:", flag)

if __name__ == "__main__":
    main()
