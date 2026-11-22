# SOLVED — hitcon{531f_dE5i6N_cRy9T0Gr4Ph1C_41G0r1ThM_15_9r0B4b1Y_4_64D_1D3a_QQ}

Date: 2026-10-24. Solved from the previously-captured `remote_pipe_3.json` — no new remote connection needed.

## The missing piece (why prior agents were stuck at "26 leaks")
`remote_pipe.py` **discarded the flag blob from the leak set**:
 if B['blen']>4 and B['cost']>1000: flagblob=blob; continue
But the flag blob carries its OWN key-check at offset 20, under the SAME slot-1 key — a valid
**27th leak**. 26 encrypts + get_flag = 27 blobs = 27 leaks (the 27-query cap is the real limit).

Measured planted-vector norm ratio (relative to true Gaussian heuristic):
 N=26 -> 2.48 (wall) N=27 -> 1.975 (reachable!) N=28 -> 1.58 N=29 -> 1.28
The flag-blob leak moves the problem from the impossible N=26 to the tractable N=27.

## Enumerator fix
The old `enum.c` scanned `[lo,hi]` naively at every level -> the top level (width ~sqrt(R2g/r_last))
spun without progress on an LLL-only (GSO span ~1e15) basis. Fixes in `enum2.c`:
 1. **Schnorr–Euchner center-out ordering with early `break`** (stop a direction once the 1-D
 term pushes the partial norm past the radius).
 2. **BKZ-40 preprocessing** in `export_lattice.py` (added a `bkz` arg) flattens the GSO profile.
 3. F0 182-sample filter at the leaves (0 false positives) — exits on first match.
Top level is only 9 branches ([-4,4]); shard those across 16 cores (`/tmp/shard_run.sh`).

## Reproduce
 python3 /tmp/mk_remote27.py # adds flag-blob key-check as 27th leak -> /tmp/remote27.json
 python3 export_lattice.py /tmp/remote27.json 27 /tmp/latR27.txt 1.95 40
 /tmp/shard_run.sh /tmp/latR27.txt /tmp/enum2 /tmp/shardR27 # ~4-5 min on 16 cores
 # -> FOUND kA=a255c9ac2ef7037f kB=e77aeddfd81acbd7 (0/182 F0 mismatches)
Validation: native N=27 with known key solved in ~41 s (key matched exactly); N=28 also found.

## Key / flag
kA=a255c9ac2ef7037f kB=e77aeddfd81acbd7
Flag blob: iv=ca54c2d6 cost=548787 blen=70; decrypt via native firmware perm inverse (pperm's
python inverse is WRONG) + python Feistel^-cost.
FLAG: hitcon{531f_dE5i6N_cRy9T0Gr4Ph1C_41G0r1ThM_15_9r0B4b1Y_4_64D_1D3a_QQ}
