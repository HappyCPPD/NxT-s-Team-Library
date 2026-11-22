# DEStruction flag1 — FINAL verdict (Opus session, 2026-11-14)

## TL;DR
**flag1 is NOT obtainable against the live instance 10.83.11.237:2004 as deployed.**
The intended attack is GHASH-key (H) recovery via **AD-length tag differences**
(the `hsolve` route — confirmed intended by the deliberately huge
`MAX_AD_LENGTH = 2**20`). It mathematically works, but it needs **readable tags at a
repeated nonce**, and the shipped deployment removes every way to get them:
- correct-GCM masking (variant A): the tag mask `E(J0)` is never exposed;
- the mask cancels only across tags that share a nonce;
- the only tag-verification oracle (flag0) costs ~2^16 guesses per tag read;
- the key/H is **fresh per TCP connection** (socat `fork EXEC:python server.py`),
 so reads can't be accumulated across connections.

Per connection you can extract **at most ~16 bits** about that connection's 64-bit H
(and only if you win flag0), and H changes every connection — so a 64-bit H can never
be assembled. This is an information-theoretic wall, not a "we didn't try hard enough."

## The intended attack (hsolve) and why the big AD limit is the tell
For a FIXED nonce and FIXED ciphertext `ct`, an all-zero AD of byte-length `L` changes
GHASH only through the length term `len_A·H^2` (`len_A = 8L`). Hence
```
tag(L1) xor tag(L2) = top16( ((8L1) xor (8L2)) · H^2 )
```
The mask `E(J0)` and all ct-terms cancel. Multiplication by a constant is GF(2)-linear,
so each 16-bit difference is 16 linear equations in `Y = H^2` (64 bits). ~5 well-chosen
lengths reach rank 64 (validated end-to-end in `destruction_hsolve.py` /
`find_lengths.py`), then `H = sqrt(Y)` (squaring is a bijection in GF(2^64)).
Needing varied, large `len_A` to hit full rank is exactly why the author raised the AD
cap to 2^20 bytes — strong evidence hsolve is the intended path.

Once H is known: reuse an option-1 nonce `N` (known keystream `KS`) in option-2, set
`ct[:8] = KS[:8] xor H` so the decrypted plaintext starts with H, forge the 2-byte tag
(brute, 1/2^16), and `target_H in decrypted_data` → flag1.

## Why it cannot run against this deployment (4 empirical confirmations this session)
1. **Variant A (mask hidden).** `variantB_test.py` live → system INCONSISTENT
 (rank 191/320): the first ciphertext block is `E(J0+1)`, not `E(J0)`, so the Enc
 tag's mask `E(J0)` is never recoverable. (If it were variant B, 60 Enc queries in a
 single connection would solve H outright — it is not.)
2. **Key is fresh per connection.** Robust persistence test (`persist2.py`): captured
 one fixed flag0 tuple, then covered the FULL 2^16 tag space across 393 connections
 at low parallelism with per-slice retries (every slice executed; no refusals). Zero
 flag0 wins → the key/H does not survive a reconnect. (Matches socat fork → one
 `secrets.token_bytes(24)` per process.)
3. **No Enc nonce reuse.** 12 option-1 queries in one connection → 12/12 distinct
 nonces. So Enc free tags never share a mask; hsolve-by-Enc is impossible.
4. **No verification oracle.** A genuinely valid Enc tuple replayed into Dec returns
 `Sus.` (valid tag + innocuous plaintext == bad tag). Odd nonce lengths (0,1,3,4,16,24),
 `nonce=0000` (forces `Y0enc=E(0)=H`, but it stays in the tag mask only), and a 4 KB
 ciphertext overflow path all returned plain `Sus.`/normal — no leak, no crash.

## Information-theoretic wall (why no cleverer single-connection attack exists)
- Enc ciphertext (`KS = E(J0+1),E(J0+2)`) reveals 3DES outputs at points ≠ 0; for a PRP
 these give ~0 bits about `H = E(0)`.
- Enc tag `= top16(GHASH(H,ad,ct) xor E(J0))`; `E(J0)` is a one-time pad (distinct nonce
 ⇒ distinct, ~uniform mask) ⇒ ~0 bits about H.
- Dec reveals only `Sus./flag0/flag1`. A flag0 win reveals one exact 2-byte tag = one
 16-bit same-nonce equation about H; reading each additional same-nonce tag is another
 ~2^16-guess brute. 168 attempts/connection ⇒ at most ~one lucky tag-read per
 connection ⇒ ≤16 bits about a 64-bit H that is discarded at reconnect.
⇒ Assembling 64 bits of a single connection's H is impossible. flag1 is unreachable.

## What this means / recommendations
- The challenge's OWN Dockerfile (`socat TCP-LISTEN:2004,fork EXEC:python server.py`)
 spawns a fresh process — hence a fresh key — per connection, which removes exactly the
 key reuse the intended hsolve depends on. This looks like a **deployment bug**: flag1
 is solvable only if H persists across connections (single long-lived server process).
- Action items:
 1. Report to organizers: on 10.83.11.237:2004 the key is per-connection, so flag1's
 intended GHASH-key-recovery is information-theoretically blocked. Ask whether the
 instance is meant to run a persistent (non-forking) server.
 2. If any persistent instance is available (or they fix the deploy), the hsolve
 recovers H in ~5 tag reads × ~393 connections ≈ ~2000 connections (minutes), then
 inject H for flag1. A ready exploit can be built on top of
 `destruction_hsolve.py` (math already validated).
- flag0 (`PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0llisi0ns::VQEMEM6L6nNb}`) remains the
 obtainable, validated flag on this deployment.
