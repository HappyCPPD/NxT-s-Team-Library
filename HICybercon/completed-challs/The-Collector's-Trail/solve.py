#!/usr/bin/env python3
"""
The Collector's Trail (HICybercon) - full reproducible solve.

Six hidden fragments (one per painting image) -> master key (HKDF) ->
catalogue salt -> cabinet password -> sealed_cabinet contains stego.png ->
HMAC-selected LSB payload -> GitHub release asset + tag note serial ->
AES-256-GCM decrypt -> flag.

Run from the work/ dir after unzipping the-collectors-trail.zip into
work/vault/vault and work/cabinet_out (see WRITEUP.md).
"""
import struct, zlib, hashlib, hmac, subprocess, re, json, urllib.request
import numpy as np
from PIL import Image
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

VAULT = "vault/vault"
REPO = "broski-creator/velarium-ossuary-ledger-7f3c2a"
ASSET = 648829625          # release v1.0 -> flag.enc

def _api(path, raw=False):
    req = urllib.request.Request(f"https://api.github.com/{path}",
                                 headers={"Accept": "application/octet-stream" if raw else "application/vnd.github+json",
                                          "User-Agent": "solve"})
    with urllib.request.urlopen(req) as r:
        return r.read() if raw else json.load(r)

# ------------------------------------------------------------------ fragments
def frag_31c8():            # Van Gogh, alpha=0 border text
    # The fragment is plain text drawn in the transparent (alpha=0) border.
    # Isolate the non-white glyph pixels and save them for a human/OCR read;
    # the two 0x00/0xFF inks plus PIL's glyphs mean the string is legible.
    ar = np.array(Image.open(f"{VAULT}/record-31c8/image"))
    m = (ar[:, :, 3] == 0) & (ar[:, :, 0] != 255)
    ys, xs = np.where(m)
    crop = ar[ys.min():ys.max()+1, xs.min():xs.max()+1, 0]
    Image.fromarray(255 - crop).save("/tmp/frag_31c8.png")
    return "c1d322deee71edf2-cfb8"   # read from /tmp/frag_31c8.png (see WRITEUP)

def frag_5a73():            # Munch, blue LSB every 7th pixel from 0
    px = list(Image.open(f"{VAULT}/record-5a73/image").getdata())
    bits = [p[2] & 1 for p in px[0::7]]
    return _grep(bits)

def frag_7f2a():            # Vermeer, extra PNG chunk 'coLl'
    d = open(f"{VAULT}/record-7f2a/image", "rb").read()
    i, idat = 8, b""
    while i < len(d):
        ln = struct.unpack(">I", d[i:i+4])[0]; typ = d[i+4:i+8]; dat = d[i+8:i+8+ln]
        if typ == b"coLl":
            return dat.decode()
        i += 12 + ln
        if typ == b"IEND":
            break

def frag_b19d():            # Goya, base64 after IEND
    import base64
    d = open(f"{VAULT}/record-b19d/image", "rb").read()
    i, idat = 8, b""
    while i < len(d):
        ln = struct.unpack(">I", d[i:i+4])[0]; typ = d[i+4:i+8]
        i += 12 + ln
        if typ == b"IEND":
            break
    return base64.b64decode(d[i:].strip()).decode()

def frag_d604():            # Klimt (JPEG) steghide, passphrase = canonical locator
    out = "/tmp/d604_out"
    subprocess.run(["steghide", "extract", "-sf", f"{VAULT}/record-d604/image",
                    "-p", "belvedere.at/912", "-f", "-xf", out], check=True,
                   capture_output=True)
    return open(out).read().strip()

def frag_e2f1():            # Schiele, filter-byte == 2 gives 1 bit, MSB-first
    d = open(f"{VAULT}/record-e2f1/image", "rb").read()
    i, idat = 8, b""
    while i < len(d):
        ln = struct.unpack(">I", d[i:i+4])[0]; typ = d[i+4:i+8]; dat = d[i+8:i+8+ln]
        if typ == b"IDAT":
            idat += dat
        i += 12 + ln
        if typ == b"IEND":
            break
    raw = zlib.decompress(idat)
    h, w = 1692, 2000; stride = w * 3
    flt = [raw[r*(stride+1)] for r in range(h)]
    bits = [1 if f == 2 else 0 for f in flt]
    return _grep(bits)

def _grep(bits, msb=True):
    out = bytearray()
    for i in range(0, len(bits)-7, 8):
        v = 0
        for j, b in enumerate(bits[i:i+8]):
            v |= b << (7-j if msb else j)
        out.append(v)
    return re.search(rb"[0-9a-f]{16}-[0-9a-f]{4}", bytes(out)).group().decode()

def validate(f):
    h, c = f.split("-")
    assert hashlib.sha256(bytes.fromhex(h)).hexdigest()[:4] == c, f"bad seal: {f}"
    return bytes.fromhex(h)

# ------------------------------------------------------------------ main
def main():
    # (artist birth-year, record-dir, fragment fn, canonical locator)
    entries = [
        (1632, "7f2a", frag_7f2a,   "mauritshuis.nl/670"),          # Vermeer
        (1746, "b19d", frag_b19d,   "museodelprado.es/P000749"),    # Goya
        (1853, "31c8", frag_31c8,   "moma.org/472.1941"),           # Van Gogh
        (1862, "d604", frag_d604,   "belvedere.at/912"),            # Klimt
        (1863, "5a73", frag_5a73,   "nasjonalmuseet.no/NG.M.00939"),# Munch
        (1890, "e2f1", frag_e2f1,   "belvedere.at/3171"),           # Schiele
    ]
    entries.sort(key=lambda e: e[0])
    ikm, locators = b"", []
    for yr, rd, fn, loc in entries:
        f = fn(); b = validate(f)
        print(f"{yr} record-{rd}: {f}")
        ikm += b; locators.append(loc)

    master = HKDF(algorithm=hashes.SHA256(), length=32,
                  salt=b"collector-v2:ossuary", info=b"master").derive(ikm)
    cat = hashlib.sha256("\n".join(locators).encode()).digest()
    pw = HKDF(algorithm=hashes.SHA256(), length=16, salt=cat, info=b"zip").derive(master)
    print("cabinet password:", pw.hex())
    subprocess.run(["7z", "x", f"-p{pw.hex()}", "-ocabinet_out",
                    "sealed_cabinet.zip", "-y"], check=True, capture_output=True)

    # stego.png: HMAC-selected LSBs
    ikey = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"",
                info=b"stego").derive(master)
    data = Image.open("cabinet_out/stego.png").convert("RGB").tobytes()
    N = len(data); seen = set(); bits = []; i = 0
    while len(bits) < 8*(4+4096) and i < 5_000_000:
        v = int.from_bytes(hmac.new(ikey, i.to_bytes(8, "big"), hashlib.sha256).digest()[:8], "big")
        p = v % N
        if p not in seen:
            seen.add(p); bits.append(data[p] & 1)
        i += 1
    out = bytearray()
    for j in range(0, len(bits)-7, 8):
        v = 0
        for b in bits[j:j+8]:
            v = (v << 1) | b
        out.append(v)
    ln = int.from_bytes(out[:4], "big")
    payload, crc = bytes(out[4:4+ln]), bytes(out[4+ln:8+ln])
    assert zlib.crc32(payload) == int.from_bytes(crc, "big"), "CRC fail"
    print(payload.decode())

    ref = _api(f"repos/{REPO}/git/ref/tags/v1.0")["object"]["sha"]      # annotated tag object
    note = _api(f"repos/{REPO}/git/tags/{ref}")["message"]
    serial = re.search(r"Serial:\s*([0-9a-f]+)", note).group(1)
    print("serial:", serial)
    blob = _api(f"repos/{REPO}/releases/assets/{ASSET}", raw=True)
    assert hashlib.sha256(blob).hexdigest() == \
        "cf9932777723fb3b768006dc21bb832baf3cfa6ffba59c8d84f43f095e3e4bb4", "asset hash"
    key = HKDF(algorithm=hashes.SHA256(), length=32,
               salt=bytes.fromhex(serial), info=b"flag").derive(master)
    pt = AESGCM(key).decrypt(blob[:12], blob[12:-16]+blob[-16:], b"collector-v2")
    print("FLAG:", pt.decode())

if __name__ == "__main__":
    main()
