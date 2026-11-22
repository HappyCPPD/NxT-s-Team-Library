# one-more — CRYOVAULT (isfcr) — analysis

## Verdict
This is **Wagner's one-more forgery against blind Schnorr** (the ROS problem).
The attack is *identified and validated*; the full 256-bit instance is a heavy
generalized-birthday computation (~2.6e10 SHA-256, ~16-20 GB working set), which
does **not fit this box** (14 GB total RAM, ~1 GB free — other jobs running).

## Protocol (server.py)
secp256k1. Fresh key per connection: `x`, `X = xG`.
- `open` -> `id k R <64B hex>` (nonce `R = rG`, `r` random)
- `sign k c` -> `s = (r + c*x) mod N` (ONE answer per session; `c` our choice)
- `submit` + JSON line `[[msg_hex,Rx,Ry,s], ...]`
Judge: valid iff `s*G == R + H(R,m)*X`, where `H(R,m)=SHA256(ser(R)||m) mod N`.
Win iff `good (#distinct valid msgs) > answered (#sign calls)`.

## The forgery
Sessions 1..n, chosen challenges c_i, responses s_i. Any submitted signature
built from the coefficient vector `a` is `(Σ a_i R_i, Σ a_i s_i)` and is valid
**iff H(Σ a_i R_i, m) = Σ a_i c_i (mod N)**.

Use k = n+1 signatures: n singletons (a = e_i, challenges c_i = H(R_i,m_i))
plus 1 combined (a = all-ones, nonce `ΣR_i`, scalar `Σs_i`). The combined one
is valid iff

 H(R_1,m_1) + ... + H(R_n,m_n) = H(Σ R_i, m_c) (mod N)

i.e. a **(n+1)-list k-sum over Z_N**. With n = 511 (k = 512 = 2^9), Wagner's
k-tree solves it in

 k * N^(1/(1+lg k)) = 512 * 2^(256/10) = 2^34.6 hash evaluations

with lists of size L = 2^25.6 ~ 4.9e7. That matches the server's comment
`CONN_TIMEOUT = 1800 # (ref attack ~220s)`.

## Validated
`poc_toy_validation.py` runs the EXACT construction on a toy additive group
(same modulus for H and the group) with k=8/n=7 and prints
`valid 8 answered 7 -> FLAG`. `poc_toy_reducedserver.py` runs the same k-sum
against a reduced-width copy of server.py (shows the 7/8 + modulus caveat).
So the reduction and the signature algebra are confirmed.

## Why it is not finished here
Working set = ~9 live lists * 4.9e7 elems * ~32-40 B ≈ **16-20 GB**, plus
2.6e10 SHA-256. Originally judged to need >= 32 GB RAM. **Corrected in the
second session:** the box has NVMe 302 GB free and the k-tree join is
swap-friendly, so with the memory-optimised engine (counter-only leaves +
`HBITS=min(ell,24)` buckets → active ~6-12 GB) it fits this 16 GB box via NVMe
swap. Implementation = Wagner k-tree (bit-exact over 2^W) + reconstruction of
the chosen (list,counter) leaves, then 511 `sign` calls and one `submit` with
512 entries.

## Reproduce (on an adequate machine)
1. open 511 sessions, keep R_i; compute R_sum.
2. build 512 lists: list_i = { H(R_i, msg(i,c)) : c in [0,L) }, list_512 =
 { -H(R_sum, msg(512,c)) }.
3. k-tree (a=9, ell~25.6) -> one element per list summing to 0 mod N.
4. c_i := chosen value i; sign each session; submit 512 sigs
 (511 singletons + the combined).
-- k-tree engine (validated: selfcheck ZERO on small modulus)

## Hard constraint: CONN_TIMEOUT = 1800 s is a WHOLE-CONNECTION wall clock
server.py:189 `async with asyncio.timeout(CONN_TIMEOUT): async for msg in ws:`
=> open(511) + k-sum + sign(511) + submit must ALL finish within 30 min of connecting.
=> the k-sum working set must effectively run in minutes.

CORRECTION (2nd session): a 16 GB box CAN do this. The hash-join access pattern
is swap-friendly (left input sequential, dormant left-spine pages out; only
right input + hash table + output stay hot ≈ 10-12 GB). NVMe swap handles the
~40-50 GB of dormant data in ≈15 s. With the memory-optimised bitksum.c the
active set is ≈6-12 GB, comfortably inside 16 GB + NVMe swap. A >=32 GB box
remains a zero-risk fallback (~10-20 min compute).

Engine bitksum.c VALIDATED (small scale, selfcheck=ZERO) — and RE-VALIDATED after
the memory-optimised rewrite (counter-only leaves; HBITS=min(ell,24)).
Driver solve.py plumbing VALIDATED live (1 valid sig accepted: "valid 1 answered 1").
Real params: ./bitksum 9 256 27 134217728 < 512ser.txt (a=9, hb=256, ell=27, L=2^27)

SHA-256 throughput on this box: OpenSSL full 72B = 371 ns/hash; midstate
single-thread = 263.5 ns; 16-core midstate = 34.8 ns/hash (28.8 M/s); HAVE_SHANI=1.
