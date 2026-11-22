---
name: faa-challenge-structure
description: "h4ckc0n 2026 \"FAA\" forensics challenge — verified structure, recovered prime, and the open steghide-password step"
metadata:
 node_type: memory
 type: project
 originSessionId: 69389dcc-c514-48a1-9cbb-d579b103f7a3
 modified: 2026-11-15T09:32:55.608Z
---

h4ckc0n 2026 **FAA** (forensics, 500 pts, 0 solves as of 2026-11-15). Flag format `d4rk{...}`.
Carrier: `faa_work/chall-image/benjamin-chambon-WAWyV76C3t8-unsplash.jpg` (Paris Haussmann building, Fujifilm X100VI, 5152x7728).

**Verified:**
- JPEG metadata holds **6 Shamir shares** (threshold 3 = "Three Musketeers"; field = Mersenne prime 2^521-1). Share format = 1-byte index + 66-byte value + 2-byte `sha256(idx+value)[:2]` checksum (all 6 valid).
 - Encodings: XMP Label=base64 (idx1), EXIF UserComment=base85 (idx2), APP12 SHR=base32 (idx3), APP11 SHR=base36 (idx5), JFIF APP0 extra bytes=raw (idx6), post-FFD9 trailer=ascii85 (idx7). Index 4 deliberately absent ("not everything is needed").
- All 3-subsets reconstruct the same secret = **264-bit prime**
 `b8b606e6b8290b478f06ba56d316d3933b3dd6a369885c76975c6b622d8b59b3e5`
 (dec `21388077551557335503598707706588121040060001228422848505354972680588693352330213`). This is "the prime".
- **7th metadata blob** = APP15 SHR, hex-encoded, 69 bytes, **index byte 0x46**, checksum does NOT match share scheme → it is NOT a share. Bytes: `46e367a44540ef374f3b9baa3a5f8b6e71332a0295858563cc3b07d63190055680e995497a5bd5a3a0177d6528eab197686ec540f8e80ddd46d3b5010553b7bc261c2d1040`. Purpose unresolved.
- **Genuine steghide payload confirmed** in the JPEG: stegseek `--seed` → seed `c6adb5de`, ~389.3 KB compressed, rijndael-128 CBC. Control: re-encoded clean copy yielded NO seed over all 4.29B, so not a false positive. steghide seed = `xor` of 4 LE uint32 from `md5(password)`.

**Exhausted (did NOT yield the steghide password / did not decrypt the hex blob):**
rockyou (14M); themed wordlists (musketeer motto "all for one…", names, FAA, prime, Paris); prime in dec/hex/0x/HEX/base36/58/62/raw33/32/reversed + base64/32/85 of each + md5/sha* of each; substrings of prime & hex blob; metadata strings; coefficients a1,a2,p; the challenge comment phrases. Hex blob vs prime-as-key: RC4, repeating-XOR, ChaCha20/Salsa20/AES-CTR/CFB/OFB/CBC/ECB (16 & 32-byte keys, many nonce/IV splits), ChaCha20Poly1305/AES-GCM/XChaCha/secretbox, RSA mod q. d4rk{ crib → keystream `22d715cf3e` matches no prime hash.

**Open step:** derive the steghide password (seed `c6adb5de`) — not the prime (confirmed by real `steghide extract`, not just seed-proxy), not in rockyou(14M)+darkc0de(1.47M)+Pwdb(1M)+themed. steghide seed = fold(md5(pw)) and validated: a correct pw MUST produce seed `c6adb5de`, so seed-matching is an exact fast offline oracle for candidate passwords.

**Round 2 negatives (2026-11-15):** hex-blob index byte `0x46` = ASCII `'F'` (challenge="FAA") — noted but no payoff. Ruled out for hex blob with prime/share/f(0)/f(4)-derived keys: AES-CBC/ECB block-window sweeps w/ PKCS7 check, ChaCha20/Salsa20/AES-CTR/CFB/OFB, ChaCha20Poly1305/AES-GCM full AEAD auth sweep (keys=sha256/md5x2/pbkdf2/raw-trunc of raw/dec/hex; nonces=head12/zero/tail12/head8; aad=none/''/FAA; AES-128 & 256) — NOTHING authenticates. OTP (hx XOR f(70), hx±f(70) mod p), RSA (hx not divisible by q), degree-6 interpolation using all 7 points → f(0) garbage. f(4) (the missing share, "not everything needed") is a full 521-bit non-prime, not a useful key. `d4rk{` crib on hx → keystream `22d715cf3e`, matches no prime hash. Control: re-encoded clean copy of the carrier found NO steghide seed over all 4.29B → original's payload is REAL not a false positive.

**Candidate flags to try submitting** (if intended flag is the prime itself): `d4rk{21388077551557335503598707706588121040060001228422848505354972680588693352330213}` or `d4rk{b8b606e6b8290b478f06ba56d316d3933b3dd6a369885c76975c6b622d8b59b3e5}`. Challenge is being solved (491→468 pts), so a path exists; likely the hex blob→steghide-password construction, not yet found. stegseek binary at scratchpad `ss/root/usr/bin/stegseek` (ephemeral).
