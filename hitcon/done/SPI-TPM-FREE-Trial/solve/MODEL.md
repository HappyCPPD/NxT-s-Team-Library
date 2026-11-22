# SPI-TPM-FREE-Trial — CORRECTED MODEL (supersedes HANDOFF.md §3/§5)

## Blob layout (VERIFIED against firmware + live service)
```
off 0 : magic "STP1" (53545031)
off 4 : 02 00 28 00 (version/const)
off 8 : IV (u32 LE) <- fresh getrandom per encrypt
off 12 : nonce = Feistel rounds = COST (u32 LE)
off 16 : bytelen (u32 LE) = plaintext length
off 20 : key-check (u32 LE) = known_part(IV) ^ (field_result(kA,kB,IV) >> 118)
off 24 : MAC (16 bytes)
off 40 : ciphertext, 4 bytes per 32-bit plaintext word, LE <-- CT IS AT 40, NOT 24
```
The prior pass read the ct at offset 24 (= the MAC) and so concluded "the cipher mixes
globally / length-dependent". It does NOT. ct is per-word independent.

## Cipher (VERIFIED: 0 mismatches vs firmware; decrypt round-trip OK)
For plaintext word j (4 bytes, interpreted LITTLE-endian -> w):
```
E0 = perm(w, IV, j, COST, sel=0, dir=0)
fe = Feistel^COST(E0, kA, kB) # round = round_f(L,kA,kB, rsel=round&3)
ct_j= perm(fe, IV, j, COST, sel=1, dir=0)
```
perm = TEA-variant in `pperm.py` (exact fwd; native inverse via fhapi.Fh).
`kA,kB` = slot key bytes 0..15 (128-bit, full entropy, raw getrandom — no KDF).

For COST=1 the Feistel is one round: fe = ((F0(L)^R)<<16)|L, with (L,R)=(E0>>16, E0&0xffff).
=> F0(L) = (perm(ct_j,IV,j,1,sel=1,dir=1) >> 16) ^ R (key-independent extraction)

round_f(L,kA,kB,rsel):
```
U = rol(kB,17)^kA^C3 ; B = rol(kA,29)^kB
Z = rol(kB,17)^kA^(L*C1)^(rsel*C2)^C3 ; P = sm(Z+GOLD)
Y = B ^ P ; out16 = fold(sm(Y+GOLD))
fold(v)= (v ^ v>>16 ^ v>>32 ^ v>>48) & 0xffff
sm(x)= x^=x>>30; x*=MA; x^=x>>27; x*=MB; x^=x>>31
```
C1=0xd6e8feb86659fd93 C2=0xa5a3564e27f8862f C3=0x62696c696e2d7221
GOLD=0x9e3779b97f4a7c15 MA=0xbf58476d1ce4e5b9 MB=0x94d049bb133111eb

## Attack (one connection)
1. `encrypt 1 1 <N words>` (COST=1) -> N ciphertext words -> N (L,F0(L)) samples (16 bits each)
2. `get_flag` -> flag blob (SAME key as step 1)
3. Recover (kA,kB) from the F0 samples; decrypt flag blob offline (solve_e2e.decrypt_blob).

## Verified working
- solve_e2e.decrypt_blob: encrypt->decrypt round trip MATCH.
- extract_f0: 200/200 consistent on live local VM.
- Cipher model == firmware on thousands of random cases (incl. the gdb-confirmed arg values).

## BLOCKER: recovering (kA,kB) from the F0 samples
- z3 (default), z3 bit-blast->CaDiCaL, my own CNF+CaDiCaL, CryptoMinisat(XOR), z3 on the
 key-check equations: ALL too slow (multiplier inversion).
- key-check HNP: works at >=28 samples (lattice + fpylll enumeration + verify; diag3 2/2 at
 N=28,NV=12), but we only get 26-27 leaks/connection and N=27 quadratic-only fails (d5).
- NEXT IDEAS: (a) more samples per connection (COST=4 gives F0..F3 = 64 bits/word);
 (b) a 2^32 MITM on the (Xu,Bu) form out=PHI(Bu ^ PSI(Xu ^ TW(L)));
 (c) a lattice that folds in the quadratic t=uv (only ONE multiply) -> SAT.

## Remote rules (from organiser): 1 connection at a time, 1 new connection/min, solve locally first.
