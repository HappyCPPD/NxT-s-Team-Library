# RESULT — Quantum Echo (h4ckc0n_2026, Crypto, 100 pts, 360 solves)

STATUS: SOLVED

FLAG: d4rk{quantum_echo_reuse_breaks_the_pad}

## MECHANISM

The challenge bundles three artifacts in `challenge.json`: a BB84-style
`quantum_transcript`, a `register` dump with a documented controller model, and a
`sealed_flag` with `seal_record` compatibility vectors. The task brief guessed
"AES-256-CTR" — **that is wrong**. The compat vectors prove the seal is a
SHA-256-based stream cipher: **32-byte keystream blocks = SHA256(material_ascii || counter_u32_be)**, counter starting at 0. That is the "32-byte block size and a
counter that starts at zero". No AES key is ever needed.

The real secret is the **material string** `"s:t:e0:q"`, which is exactly the four
controller-model parameters, recovered from the register via a linear solve.

### Step 1 — controller model parameters from the calibration probes
The calibration gives `(input, fold_word, walk_word)` triples. Brute-forcing the
rotation distances against
`fold_word = input ^ (rotl(input,r1) & rotl(input,r2))` and
`walk_word = rotl(input,r)` gives:

```
fold rot = (5, 11) walk rot = 7
```

### Step 2 — recover fold_mask / walk_mask / echo seed / pad bits (GF(2))
Model (from `controller_model`):
```
z_i = parity(fold_mask & fold_word_i) XOR echo_i XOR pad[contact_i]
echo_i = echo_{i-1} XOR parity(walk_mask & walk_word_i) (echo_0 = e0, updated before recording)
```
Every term is GF(2)-linear in the 81 unknowns (`fold_mask` 32b, `walk_mask` 32b,
`e0` 1b, 16 pad bits for contacts A..P). 160 equations → Gaussian elimination:

```
rank = 80/81 -> fold_mask = 1d0cc456 walk_mask = ccc78639 e0 = 1 pads = 0101101101011110
```
(one free variable: `(e0, pads)` are only determined up to a global XOR with 1)

### Step 3 — resolve the ambiguity with the audit tap
The transcript's `audit_tap` at sample 0 has `source = register_seed_contact_A`,
`reported_bit = 1`. Flipping the free variable to satisfy `pad_A = 1` gives the
unique correct solution, which reproduces **all 160** `z` values:

```
e0 = 0 pads = 1010010010100001
model reproduces all 160 z bits: True
```

### Step 4 — material string + keystream
```
material = "1d0cc456:ccc78639:0:1010010010100001" # s:t:e0:q
```
The `seal_record` compatibility vectors are confirmed to be keystream blocks of
`SHA256(material_ascii || counter_u32_big_endian)` (e.g. all-zero material,
counter 0 → `3edde0bf…3227`). Decrypt `sealed_flag` (39 bytes = 2 blocks):

```python
ks = b''.join(hashlib.sha256(material.encode + i.to_bytes(4,'big')).digest for i in range(2))
flag = bytes(a ^ b for a, b in zip(bytes.fromhex(sealed_flag), ks))
```

### Proof (actual output)
```
$ python3 qe_solve.py
[1] calibration -> fold rot=(5, 11) walk rot=7
[2] GF(2) rank=80/81 -> fold_mask=1d0cc456 walk_mask=ccc78639 e0=1 pads=0101101101011110
[3] ambiguity resolved by audit_tap (contact A=1) -> e0=0 pads=1010010010100001
[4] model reproduces all 160 z bits: True
[5] compat vectors confirmed: keystream = SHA256(material_ascii || counter_u32_be), 32B blocks
[6] material = 1d0cc456:ccc78639:0:1010010010100001
[6] sealed_flag = 4ab01e45d207a22253b43be9ba5710de791fb9c4be0934273338adede41fc83931c3d42af2d174

FLAG: d4rk{quantum_echo_reuse_breaks_the_pad}
```

The BB84 transcript only supplies the basis convention (sifted samples 0..23) and
the `contact_A = 1` audit bit; the "quantum key" is in fact the register-derived
material string, whose reuse is what "breaks the pad".

## ARTIFACTS
- `qe_solve.py` — clean end-to-end solver (prints the flag)
- `qe_solve_output.txt` — captured proof output
- `qe_solve_model.py` — standalone GF(2) model recovery (stage 1)
- `qe_seal_probe.py` — reverse-engineering of the seal function from compat vectors
- `qe_sweep.py` — wide key-derivation sweep (used before the SHA256-keystream insight)
- `qe_model.json` — recovered model parameters
