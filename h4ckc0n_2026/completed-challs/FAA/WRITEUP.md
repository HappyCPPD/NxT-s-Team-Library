# FAA — h4ckc0n 2026 (Forensics, 500) — SOLVED

Flag: `d4rk{JsFAaAaA_0bfu5c4710n_<3}`

The two hints were the key. Hint 1: *"A name turned halfway round the alphabet opens the
room hidden inside the picture."* → **ROT13** of the Unsplash photo ID opens the steghide
payload. Hint 2: *"the key is spoken by portions across the town"* → the **prime
reconstructed from the Shamir shares** is the key for the final cipher.

## Full chain

Artifact: `chall-image/benjamin-chambon-WAWyV76C3t8-unsplash.jpg` (5152x7728).

### Layer 0 — JPEG metadata holds 6 Shamir shares (threshold 3, GF(2^521-1))
Seven 69-byte blobs hidden behind different encodings across the file:

| segment | encoding | index byte |
|---|---|---|
| APP1 XMP `xmp:Label` | base64 | 1 |
| APP1 Exif UserComment (0x9286) | base85 | 2 |
| APP12 (`SHR\0`) | base32 | 3 |
| APP11 (`SHR\0`) | base36 | 5 |
| APP0/JFIF extra 69 bytes | raw | 6 |
| bytes after `FFD9` | ascii85 | 7 |
| APP15 (`SHR\0`) | hex | **0x46='F'** (not a share) |

Any 3 of the 6 valid shares (indices 1,2,3,5,6,7; index 4 is deliberately missing —
"not everything is needed") reconstruct the same 264-bit prime:

```
b8b606e6b8290b478f06ba56d316d3933b3dd6a369885c76975c6b622d8b59b3e5
```

The COM segment says *"The Three Musketeers may find the prime"* (threshold 3).

### Layer 1 — steghide payload (the "room hidden inside the picture")
The JPEG carries a genuine steghide payload (stegseek seed `c6adb5de`, ~389 KB, AES-128-CBC).

Hint 1: *"A name turned halfway round the alphabet"* = **ROT13 of the filename's photo id**
`WAWyV76C3t8` → `JNJlI76P3g8`.

Password `JNJlI76P3g8` (seed oracle confirms `seed("JNJlI76P3g8") == c6adb5de`):

```
stegseek -q chall.jpg pw.txt out.bin # pw.txt contains JNJlI76P3g8
```

### Layer 2 — XZ → base64 → JSFuck
`out.bin` = XZ compressed (398852 B). Decompress → 21,238,623 B ASCII text: **base64**
(76-char lines, 23-symbol alphabet) of a 15,722,097-byte **JSFuck** program (charset `[]!+`).

### Layer 3 — JSFuck → obfuscated JS
The JSFuck is `Function("return eval")( <JSFuck-encoded obfuscated JS> )`.
Evaluating the inner expression yields a 393 KB `javascript-obfuscator`-style program
(string array + rotation + RC4/base64 decoder).

Deobfuscated with `npx webcrack` → `deobfuscated.js` (289 lines). It is a **custom
byte cipher**: splitmix64 keystream seeded by xxhash64(FNV-1a) of the key, a Fisher-Yates
S-box, per-byte round keys selecting one of 3 ops (xor / add / rotate) in one of 6 orders,
plus a 4-byte checksum trailer.

```js
const cipherBytes = [126,120,134,76,92,84,146,16,121,17,151,240,230,181,137,153,166,
 146,210,58,239,48,109,117,183,117,157,123,57,12,59,78,2,117,197,212,90,79,49,169,79,23,119];
const playerKey = process.argv[2];
const result = playerKey ? decryptPayload(cipherBytes, playerKey) : null;
if (result === null) { console.error("wrong key"); process.exit(1); }
console.log(result);
```

### Layer 4 — the final door's key
Hint 2: *"the key is spoken by portions across the town"* — the key is the prime
reconstructed from the shares, **in decimal**:

```
node payload_run.js 21388077551557335503598707706588121040060001228422848505354972680588693352330213
FLAG = "d4rk{JsFAaAaA_0bfu5c4710n_<3}"
```

(Prime hex / 0x / upper / the `0x46` blob / rot13 ids all return "wrong key"; only the
**decimal** form of the reconstructed prime works.)

## Reproduce
```
cd faa_work/extract2
node payload_run.js 21388077551557335503598707706588121040060001228422848505354972680588693352330213
```
Working artifacts kept here: `out.bin` (steg payload), `payload.bin` (XZ out), `layer2.jsfuck.js`,
`payload_js.txt` (obfuscated JS), `webcrack_out/deobfuscated.js`, `payload_run.js`.
Custom JSFuck interpreter: `jsfuck_interp.py` + `run_interp.py` (used to deobfuscate the JSFuck
without running the slow full program).
