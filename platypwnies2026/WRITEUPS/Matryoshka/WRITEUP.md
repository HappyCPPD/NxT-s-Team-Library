---
title: "Matryoshka"
ctf: "platypwnies 2026"
date: 2026-11-14
category: rev
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}"
---

# Matryoshka

## Summary

A "multi-stage ~~rocket~~ binary" — literally binaries nested inside binaries. Stage 1 is a
stripped PIE ELF that decrypts a blob from its own `.data` with a small LCG keystream and
`fexecve`s the result from a `memfd` (never touching disk). Stage 2 asks for a password
whose check is a **reflected CRC-32** over each 4-byte block. CRC-32 is affine over GF(2),
so each block's preimage is a 32×32 linear solve (Gaussian elimination) — no brute force,
no reversing of the CRC routine beyond recognising it. Password recovered, flag printed.

## Solution / Exploit

### Stage 1 (`matryoshka`): decrypt an embedded ELF

Stripped PIE ELF. `main` (0x1080):

1. Reads a 32-bit length from `.data` (vaddr `0x4040`, value `0x25ad8`).
2. Stream-decrypts the blob at `0x4060` with a small **LCG-based keystream**:
 `edx = 0xed9e231; loop { edx *= 0x7c674e63; k = ((edx>>16) ^ (edx>>8)&0xff) ^ edx ^ (edx>>24); buf[i] ^= k & 0xff }`
3. `memfd_create("stage2")`, writes the decrypted blob, `fexecve`s it (never touches disk).

Decrypting the blob (file offset of `0x4060` = `0x3020 + 0x40` in `.data`) yields a valid
ELF = **stage 2** (`matryoshka_solve.py: extract_stage2`).

### Stage 2: password = CRC-32 preimages

Prompts `Enter password:`, hex-decodes the input into a 64-byte buffer, then for every
4-byte little-endian block computes `fcn.00004628` and compares the 4 output bytes
big-endian against the string `"my_c00l_p44sw0rd"`, i.e. the four 4-byte words
`"my_c" | "00l_" | "p44s" | "w0rd"`.

`fcn.00004628` is the **standard reflected CRC-32** (the table at `0x1b160` is the classic
CRC-32 table, init `0xffffffff`, final `~state`). So the check is:

```
CRC32(block_bytes_little_endian) == word_target (as big-endian u32)
```

### Solving CRC-32 preimages with GF(2) linear algebra

CRC-32 is **affine over GF(2)**: `crc(x) = M·x ⊕ c`, where `M` is a fixed 32×32 bit matrix
and `c = crc(0)`. Build `M`'s columns from single-bit inputs, then solve `M·x = target ⊕ c`
per block with Gaussian elimination → the preimage bytes.

```python
c0 = crc(b"\x00"*4)
cols = [crc((1 << i).to_bytes(4, "little")) ^ c0 for i in range(32)]
out = b"".join(gf2_solve(cols, t ^ c0).to_bytes(4, "little") for t in targets)
```

Password (hex): `c667c58c3b02d6c91b8def4fdd1bc5f3`

```bash
echo c667c58c3b02d6c91b8def4fdd1bc5f3 | ./matryoshka
# Enter password: Password correct!
# Here is your flag: PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}
```

Solver: `matryoshka_solve.py` (extracts stage 2, computes the password, feeds it in).
Verified reproduction:

```
$ python3 matryoshka_solve.py
[+] password: c667c58c3b02d6c91b8def4fdd1bc5f3
Enter password: Password correct!
Here is your flag: PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}
```

## Flag(s)

```
PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}
```

## Notes / Pitfalls

- **`.data` file offset vs vaddr.** The length at vaddr `0x4040` lives at file offset
 `0x3020`, so the blob at vaddr `0x4060` is at file offset `0x3020 + (0x4060-0x4020)`
 = `0x3060`; getting this mapping wrong silently yields garbage instead of an ELF.
- **The keystream is stateful, byte-serial.** It must be applied in order, one `edx`
 update per byte (a `& 0xffffffff` mask keeps the 32-bit wrap correct) — do not try to
 vectorise or parallelise it.
- **Recognise CRC-32, don't reverse it.** The win is spotting the reflected CRC-32
 (init `0xffffffff`, final XOR `~state`) from the table/structure; once recognised, the
 affine-GF(2) solve is mechanical. Brute-forcing 2^32 per block is infeasible.
- **Endianness flips.** The block is ingested little-endian into the CRC but the target
 word is compared big-endian (`"my_c"` as bytes → u32 BE). Feed the solve the little-endian
 4-byte value and emit little-endian bytes.
- **Bash-friendliness.** The password is entered as **hex text** (64 hex chars → 32 bytes),
 not raw bytes; the solver prints the hex form.

## Files

- `matryoshka_solve.py` — stage-2 extractor + CRC-32 GF(2) preimage solver + runner.
- `rev-matryoshka/matryoshka` — the challenge binary (stripped PIE ELF).
- `rev.matryoshka.zip` — the original handout.
