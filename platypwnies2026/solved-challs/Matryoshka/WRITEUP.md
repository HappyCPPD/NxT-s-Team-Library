# Matryoshka (rev, difficulty 1)

## Flag
```
PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}
```

## Solution

A "multi-stage ~~rocket~~ binary" — literally binaries nested inside binaries.

### Stage 1 (`matryoshka`)
Stripped PIE ELF. `main` (0x1080):
1. Reads a 32-bit length from `.data` (vaddr `0x4040`, value `0x25ad8`).
2. Stream-decrypts the blob at `0x4060` with a small LCG-based keystream:
 `edx = 0xed9e231; loop { edx *= 0x7c674e63; k = ((edx>>16) ^ (edx>>8)&0xff) ^ edx ^ (edx>>24); buf[i] ^= k & 0xff }`
3. `memfd_create("stage2")`, writes the decrypted blob, `fexecve`'s it (never touches disk).

Decrypting the blob (file offset of `0x4060` = `0x3020 + 0x40` in `.data`) yields a valid ELF = **stage 2**.

### Stage 2
Prompts `Enter password:`, hex-decodes the input into a 64-byte buffer, then for every 4-byte
little-endian block computes `fcn.00004628` and compares the 4 output bytes (big-endian) against
the string `"my_c00l_p44sw0rd"`.

`fcn.00004628` is the **standard reflected CRC-32** (table at `0x1b160` is the classic CRC32 table,
init `0xffffffff`, final `~state`). So the check is:
`CRC32(block_bytes_little_endian) == "my_c" | "00l_" | "p44s" | "w0rd"` as big-endian u32.

CRC-32 is **affine over GF(2)**: `crc(x) = M·x ⊕ c`. Build the 32×32 matrix from single-bit inputs,
then solve `M·x = target ⊕ c` per block with Gaussian elimination → the preimage bytes.

Password (hex): `c667c58c3b02d6c91b8def4fdd1bc5f3`

```bash
echo c667c58c3b02d6c91b8def4fdd1bc5f3 | ./matryoshka
# Enter password: Password correct!
# Here is your flag: PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}
```

Solver: `matryoshka_solve.py`.
