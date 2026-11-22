---
title: "FAA"
ctf: "h4ckc0n 2026"
date: 2026-11-15
category: forensics
difficulty: hard
points: 500
flag_format: "d4rk{...}"
author: "author (author)"
---

# FAA

## Summary

A JPEG carries six Shamir shares in its metadata (threshold 3, over GF(2^521-1)) plus a
steghide payload. The shares reconstruct a 264-bit prime; the steghide password is the
ROT13 of the Unsplash photo id. Inside the steghide payload is a four-layer stack —
XZ → base64 → JSFuck → obfuscated JavaScript — ending in a custom byte cipher whose key
is the reconstructed prime (in **decimal**). Decrypting the 43-byte ciphertext yields the flag.

Author `paramveer504`. Description: *"Many may not know that not everything is needed to make up
something"*. Hints:
- **H1:** *"A name turned halfway round the alphabet opens the room hidden inside the picture."*
- **H2:** *"Strip the coats one by one, but never strike the match; the last door wants a key before
 it speaks, the key is spoken by portions across the town."*

## Solution

### Step 1 — Recover the prime from the metadata shares

Seven 69-byte blobs are hidden across the JPEG's metadata, each behind a different encoding.
Six of them are Shamir shares (index byte + 66-byte value + 2-byte `sha256(idx‖value)[:2]`
checksum, all validating); the 7th (APP15, index byte `0x46` = `'F'`) is not a share.

| segment | encoding | index |
|---|---|---|
| APP1 XMP `xmp:Label` | base64 | 1 |
| APP1 Exif UserComment (0x9286) | base85 | 2 |
| APP12 (`SHR\0`) | base32 | 3 |
| APP11 (`SHR\0`) | base36 | 5 |
| APP0/JFIF extra 69 bytes | raw | 6 |
| bytes after `FFD9` | ascii85 | 7 |
| APP15 (`SHR\0`) | hex | `0x46` = `'F'` (not a share) |

Index 4 is deliberately absent — "not everything is needed". The `COM` segment says
*"The Three Musketeers may find the prime"* → threshold 3. Lagrange interpolation at `x=0`
over `Q = 2^521 − 1` from **any** 3 valid shares gives the same 264-bit prime:

```
dec: 21388077551557335503598707706588121040060001228422848505354972680588693352330213
hex: b8b606e6b8290b478f06ba56d316d3933b3dd6a369885c76975c6b622d8b59b3e5
```

### Step 2 — Open the steghide payload (H1)

The image contains a genuine steghide payload (stegseek seed `c6adb5de`, ~389 KB, AES-128-CBC).
H1 says *"a name turned halfway round the alphabet"* → **ROT13** of the photo id in the filename
`WAWyV76C3t8` → password **`JNJlI76P3g8`**:

```bash
stegseek -q chall.jpg <(printf 'JNJlI76P3g8\n') out.bin
```

### Step 3 — Strip the remaining layers (H2: "strip the coats one by one")

```bash
xz -dc out.bin > payload.bin # 398852 B -> 21,238,623 B ASCII
# payload.bin = base64 (76-char lines) of a 15,722,097-byte JSFuck program (charset []!+)
```

The JSFuck is `Function("return eval")( <inner> )`; evaluating the inner expression yields a
393 KB `javascript-obfuscator`-style program. Deobfuscate it with `npx webcrack`. The payload is a
custom byte cipher (splitmix64 keystream seeded by xxhash64/FNV-1a of the key, a Fisher-Yates S-box,
per-byte round keys picking one of {xor, add, rotate} in one of 6 orders, plus a 4-byte checksum):

```js
const cipherBytes = [126,120,134,76,92,84,146,16,121,17,151,240,230,181,137,153,166,146,210,58,
 239,48,109,117,183,117,157,123,57,12,59,78,2,117,197,212,90,79,49,169,79,23,119];
const playerKey = process.argv[2];
const result = playerKey ? decryptPayload(cipherBytes, playerKey) : null;
if (result === null) { console.error("wrong key"); process.exit(1); }
console.log(result);
```

### Step 4 — The last door's key (H2)

*"the key is spoken by portions across the town"* → the key is the prime reconstructed from the
shares, and it must be supplied in **decimal** (hex / `0x…` / uppercase / the `'F'` blob / the
rot13 ids all fail the checksum):

```
node payload_run.js 21388077551557335503598707706588121040060001228422848505354972680588693352330213
FLAG = "d4rk{JsFAaAaA_0bfu5c4710n_<3}"
```

### Complete solve script

`FAA/solve.py` — runs the whole chain
(challenge JPEG → flag) in ~13 s. It parses the JPEG segments and validates share checksums,
reconstructs the prime by Lagrange interpolation mod 2^521−1, shells out to `stegseek` with the
ROT13 password, unwraps XZ→base64→JSFuck (using `node` to evaluate the inner expression), and
re-implements the custom cipher in pure Python to decrypt the 43-byte ciphertext.

```bash
cd FAA
python3 solve.py faa_work/chall-image/benjamin-chambon-WAWyV76C3t8-unsplash.jpg
```

Actual output:

```
[1] prime (dec) = 21388077551557335503598707706588121040060001228422848505354972680588693352330213
[1] prime (hex) = b8b606e6b8290b478f06ba56d316d3933b3dd6a369885c76975c6b622d8b59b3e5
[2] steghide payload: 398852 bytes (XZ)
[3] xz -> base64 text: 21238623 bytes
[3] base64 -> JSFuck: 15722097 bytes
[3] JSFuck -> obfuscated JS: 393688 bytes
[4] flag: FLAG = "d4rk{JsFAaAaA_0bfu5c4710n_<3}"
```

## Flag

```
d4rk{JsFAaAaA_0bfu5c4710n_<3}
```

## Notes / dead ends

- The prime is **not** the flag and **not** the steghide password (confirmed with a real
 `steghide extract`); it is the key for the *final* cipher only, and only in decimal.
- `stegseek --seed` reports the seed (`c6adb5de`) without extracting; with steghide's default AES
 the password is still required. Validate the seed oracle against a long-password embed before
 trusting any password sweep.
- Running the *whole* JSFuck executes `eval(obfuscated JS)` and hangs for many minutes; extract and
 evaluate only the inner call argument instead.
- The obfuscated payload is padded with ~370 KB of Lorem-ipsum as a decoy.

## Tools

`python3` (stdlib: base64/hashlib/lzma/re/struct), `stegseek 0.6`, `node v22`, `npx webcrack`.
