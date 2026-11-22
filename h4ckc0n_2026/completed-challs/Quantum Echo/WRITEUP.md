# Quantum Echo

_Category: Crypto — 100 pts — 360 solves — Status: **SOLVED**_

**Flag:** `d4rk{quantum_echo_reuse_breaks_the_pad}`

## Summary

`challenge.json` ships a BB84 `quantum_transcript`, a `register` dump with a
documented controller model, and a `sealed_flag` + `seal_record` compatibility
vectors.

The hinted "AES-256-CTR" is a decoy. The compatibility vectors prove the seal is
a **SHA-256 keystream**: 32-byte blocks `SHA256(material_ascii || counter_u32_be)`,
counter from 0 (this is the "32-byte block size and counter starting at zero").
The secret is the `s:t:e0:q` material string, which is exactly the register's
controller-model parameters:

1. **Calibration probes** → rotation distances: `fold_word = x ^ (rotl(x,5) & rotl(x,11))`, `walk_word = rotl(x,7)`.
2. **GF(2) linear solve** over 160 observations → `fold_mask = 1d0cc456`, `walk_mask = ccc78639`, echo seed, 16 calibration-pad bits (contacts A..P). Model:
 `z_i = parity(fold_mask & fold_word_i) ^ echo_i ^ pad[contact_i]`, with
 `echo_i = echo_{i-1} ^ parity(walk_mask & walk_word_i)`.
3. **Ambiguity fix:** the solution is determined up to a global XOR of `(e0, pads)`; the transcript's `audit_tap` on `register_seed_contact_A` (=1) picks the unique branch. Recovered model reproduces **all 160** `z` bits.
4. **Material** = `"1d0cc456:ccc78639:0:1010010010100001"`; XOR the `sealed_flag` (39 bytes) with the SHA-256 keystream → flag.

The BB84 transcript contributes only the basis convention (sifted = samples 0..23)
and the `contact_A = 1` audit bit — the "quantum key" is really the register-derived
material, and its **reuse** is what "breaks the pad".

Full proof and code: `RESULT-quantumecho.md`, `qe_solve.py`.
