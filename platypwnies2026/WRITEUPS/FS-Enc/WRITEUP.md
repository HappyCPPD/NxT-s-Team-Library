---
title: "FS Enc"
ctf: "platypwnies 2026"
date: 2026-11-14
category: rev
difficulty: 2
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{f1l3_3ncrypt10n_1s_h4rd::knrpLH1NobCZ}"
---

# FS Enc

## Summary

A Rust CLI (`fs-enc`) that "uses strong authenticated encryption to store your secrets":
it derives a key with **Argon2** and then encrypts with **ChaCha20-Poly1305** — a genuinely
sound construction. The bug is that the program **stores the Argon2-derived key material in
plaintext inside the output file**. The file layout (verified with gdb on
`<argon2::Argon2>::hash_password_into` plus controlled files created with a known password)
is:

```
magic(12) || key(32) || nonce(12) || ciphertext || tag(16)
```

Bytes 12..56 of the file are *exactly* the Argon2 output (`out_len = 44` = 32-byte
ChaCha20 key ‖ 12-byte Poly1305 nonce), and the Argon2 salt is `magic(12) || magic[0:4]`
(not a stored random value). Therefore **no password is required at all**: read the stored
key and nonce and decrypt directly.

## Solution / Exploit

### Recon the binary

```
$ file fs-enc
fs-enc: ELF 64-bit LSB executable, x86-64, ... with debug_info, not stripped
```

It is **not stripped** and carries Rust crate paths, which is the whole game:

```
$ strings -n6 fs-enc | grep -iE 'argon|chacha|poly|nonce|salt|password'
.../argon2-0.5.3/src/lib.rs
.../argon2-0.5.3/src/params.rs
.../argon2-0.5.3/src/blake2b_long.rs
.../poly1305-0.8.0/src/backend/avx2.rs
Enter Password:
Printing content of encrypted file:
Modifying content of encrypted file:
Creating encrypted file:
This is your super secret vault
Use strong authenticated encryption to store your secrets
```

CLI:

```
$ ./fs-enc --help
Use strong authenticated encryption to store your secrets
Usage: fs-enc [OPTIONS] <COMMAND>
Commands: create, print, modify, set, help
Options: -p, --password <PASSWORD> The password to use, if '-' use stdin
```

### Determine the on-disk format

With a controlled vault (known password `testpass`), break on the Argon2 key-derivation
entry point and inspect its arguments:

```
(gdb) break <argon2::Argon2>::hash_password_into
...
salt = 16 bytes = magic(12) || magic[0:4] # NOT stored-random
out_len = 44 = 32-byte ChaCha20 key || 12-byte Poly1305 nonce
```

And bytes `12..56` of the output file are byte-for-byte that `out_len=44` Argon2 output.
So the header is `magic(12) || key(32) || nonce(12)`, followed by the AEAD
`ciphertext || tag(16)`.

### Decrypt with the stored key

`fsenc_solve.py`:

```python
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

def decrypt(path):
 d = open(path, 'rb').read
 magic = d[:12]
 key, nonce = d[12:44], d[44:56]
 ct, tag = d[56:-16], d[-16:]
 pt = ChaCha20Poly1305(key).decrypt(nonce, ct + tag, None)
 return magic, key, nonce, pt
```

Run against the challenge's `flag.bin` (114 bytes = 12+32+12 header + 42-byte ciphertext +
16-byte tag):

```
$ python3 fsenc_solve.py flag.bin
[*] magic = 565fe6937919ad6a113d0240 (also the Argon2 salt prefix)
[*] stored key = c15801a3333008dcfb930fdb9fc805ffaad5452a7c2915f945a131629cc7cae3
[*] stored nonce = 5b364948dd29a7b60e22cc42
[+] plaintext = b'PP{f1l3_3ncrypt10n_1s_h4rd::knrpLH1NobCZ}\n'
```

Header layout of `flag.bin` (hexdump):

```
00000000: 565f e693 7919 ad6a 113d 0240 | c158 01a3 3330 08dc fb93 0fdb 9fc8 05ff V_..y..j.=.@.....
 magic (12) | stored key (32) ...
00000030: dd29 a7b6 0e22 cc42 | ... nonce (12) | ciphertext ...
```

## Flag(s)

```
PP{f1l3_3ncrypt10n_1s_h4rd::knrpLH1NobCZ}
```

## Notes / Pitfalls

- **The crypto is fine; the storage is not.** Argon2 + ChaCha20-Poly1305 would be correct if
 the derived key never left memory. The "small must be secure" premise in the description
 is the misdirection — the flaw is a format leak, not a broken primitive.
- **Debug info is the shortcut.** `fs-enc` ships **with `debug_info`, not stripped**, so the
 Argon2 symbol names and the crate registry paths are readable end-to-end. Always run
 `file` + `strings` before attacking the math.
- **No password / no brute force.** Because the key and nonce are in the file, the password
 is irrelevant. Don't waste time brute-forcing Argon2 params.
- **Salt is not random.** The salt is `magic(12) || magic[0:4]` (a 16-byte slice of the
 fixed magic), another reason the derivation is not protecting anything.
- **AEAD tag handling.** The 16-byte Poly1305 tag is the *last* 16 bytes; concatenate it
 after the ciphertext when calling the AEAD `decrypt` (as the solver does). The decrypt
 succeeds with AAD = `None`, confirming no associated data is used.
- **Flag spelling.** The flag has a lowercase-L (`f1l3`) after `PP{` — `PP{f1l3_...}`,
 not `f1f3`.
- **Instance note.** The challenge is flagged "requires a live instance" but the artifact is
 fully self-contained: `flag.bin` (the encrypted flag) and the binary both ship, so the
 whole solve is offline. `flag.bin`, `fs-enc` and the solver are bundled here.

## Files

- `FS-Enc/fsenc_solve.py` — reads the stored key/nonce and decrypts `flag.bin`.
- `FS-Enc/flag.bin` — the encrypted flag (the artifact to recover).
- `FS-Enc/fs-enc` — the challenge binary (not stripped; Argon2 + ChaCha20-Poly1305).
