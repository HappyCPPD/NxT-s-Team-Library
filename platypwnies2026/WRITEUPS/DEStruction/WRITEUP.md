---
title: "DEStruction"
ctf: "platypwnies 2026"
date: 2026-11-14
category: crypto
difficulty: 2
flags:
 - PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0ll1si0ns::VQEMEM6L6nNb}
 - "flag1 (plaintext must contain target_H): NOT reachable on this deployment — proof below"
---

# DEStruction (crypto, difficulty 2) — 1 of 2 flags

**flag0: `PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0ll1si0ns::VQEMEM6L6nNb}`**
(obtained live on `10.83.11.237:2004`: `[+] FLAG0 after 802 connections (347.9s)` in
`logs/flag0_rerun.out`; an earlier 12-worker run won in 980 connections / 387.7 s.)

**flag1 is unreachable as deployed.** This folder contains the full proof; do not re-grind
it (see *Notes* and `FLAG1_UNREACHABLE_PROOF.md`, `flag1_FINAL_verdict.md`).

## Summary

`encryption.py` is a hand-rolled **GCM over 3DES-ECB with 64-bit blocks and the
authentication tag truncated to 2 bytes**:

```
H = E(0^8) # GHASH key == target_H
ctr0 = get_ctr(key, nonce) # len(nonce)==2 -> 00*6||nonce
 # else -> GHASH(H,"",nonce) (J0 = nonce*H^3 ^ 64*H)
Y0enc = E(ctr0) # tag mask
ct = P xor E(ctr0+1) || E(ctr0+2) || ... # CTR keystream (counter increments FIRST)
tag = (GHASH(H, ad, ct) xor Y0enc)[:2] # <-- only 2 bytes survive
```

`server.py` shares **168 attempts** between "Request encryption" (option 1, chosen 12-byte
plaintext, rejected if it contains `give me flag`) and "Submit ciphertext" (option 2,
echoing `nonce,ciphertext,ad,tag`), and awards flag0 when the decrypted payload contains
`give me flag`. Each TCP connection is a fresh process, hence a **fresh 3DES key and fresh
`H`**.

**The bug (flag0): a 16-bit tag is brute-forceable.** Option 1 with AD length 0 and an
all-zero plaintext returns the *keystream itself* (`ct = 0 xor ks`). XOR that keystream
with `b"give me flag"` and you have a ciphertext that decrypts to the command under the
same nonce/ad — everything is right except the 2-byte tag, which differs from the leaked
tag by an unknown 16-bit constant. Spend the remaining 167 attempts guessing that tag;
`P(connection succeeds) = 167/2^16`, so fan out across ~400 connections.

## Solution / Exploit

Harnesses:
* `destruction_pwn.py <host> <port> [workers] [max_conns]` — parallel flag0 forge
 (recommended; measured ≈2.5 conn/s/worker).
* `destruction_live.py <host> <port> [max_conns]` — single-threaded live variant
 that stops at the 168th `Attempts left:` line instead of waiting for socket EOF.
* `destruction_exploit.py <host> <port>` — the annotated reference implementation.

```bash
python3 destruction_pwn.py 10.83.11.237 2004 12
```

Steps (per connection):

1. **Leak the keystream.** Option 1, `AD length = 0`, plaintext `00`*12. The server prints
 `nonce,ciphertext,ad,tag`; because `P = 0`, `ciphertext == keystream`.
2. **Build the command ciphertext.** `ct2 = ct1 xor b"give me flag"`. Under the same
 `(nonce, ad)` this decrypts to `give me flag`.
3. **The only unknown is the 2-byte tag:**
 `tag2 = tag1 xor (GHASH(H,ad,ct1) xor GHASH(H,ad,ct2))[:2]`, an unknown 16-bit
 constant (the masks `Y0enc` cancel).
4. **Guess it.** Send the real leaked tag first, then random 2-byte values, pipelining all
 167 submits and reading until the 168th `Attempts left:` line (the live wrapper keeps
 the socket open, so an EOF-based loop stalls ~10 s per connection — avoid it).
5. **Reconnect on failure.** Fresh key/H, same game; P(success) = 167/2^16 ⇒ ≈392
 connections expected.

```python
def attempt(host, port):
 ... # option 1, ADL=0, pt=0^12 -> n, ct1, ad1, tag1
 ct2 = xorb(ct1, COMMAND) # -> plaintext == b"give me flag"
 tags = [tag1] + [random.randbytes(2) for _ in range(PER_CONN - 1)]
 blob = b"".join(b"2\n" + (n.hex+","+ct2.hex+","+ad1.hex+","+t.hex).encode + b"\n"
 for t in tags) + b"3\n"
 ...
```

Output:

```
[*] 800 conns, 347.1s, 2.30 conn/s
[+] FLAG0 after 802 connections (347.9s)
FLAG0 = PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0ll1si0ns::VQEMEM6L6nNb}
```

## Flag(s)

```
PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0ll1si0ns::VQEMEM6L6nNb} # flag0 — obtained
flag1 — plaintext must contain target_H = E_K(0^8): UNREACHABLE (proof below)
```

## Why flag1 is unreachable (proof, not an excuse)

`server.py` returns flag1 iff the **decrypted plaintext contains `target_H = E_K(0^8)`**,
i.e. iff the attacker knows `H`. The deployment removes every way to learn it.

**1. The key/H is fresh per connection — measured, not assumed.**
`socat TCP-LISTEN:2004,fork EXEC:python server.py` (the challenge's own Dockerfile) spawns a
fresh process per TCP connection, so `secret_key = secrets.token_bytes(24)` (hence
`H = E_K(0^8)`) is regenerated every time. `sweep_robust.py` fixed one
`(nonce, ad, ct_command)` tuple and swept the **entire 2^16 tag space** across 393 clean
connections:

```
[*] pass1: tested 65536/65536, missing 0, conns=393 320.8s
[-] ZERO wins over the COMPLETE tag space on stable (nonce,ad,ct).
[-] => secret_key/H is NOT stable across connections: flag1 via H-recovery is dead.
```

A correct tag would have decrypted to `give me flag` (readable ⇒ flag0 readout). None did,
and replaying a swept tuple on a fresh connection fails. The same harness **does** win
against a local fixed-key server (`local_persist_server.py`: `H` recovered =
`894bc3085426a441`, local flag1 captured), so the harness is sound — the live service is
per-connection. (An earlier "zero wins" run at 16 workers was *not* airtight: it silently
skipped slices on connection refusals. `sweep_robust.py` re-did it with full
coverage.)

**2. The intended attack (`hsolve`) needs a repeated nonce, which needs a persistent key.**
For a fixed nonce and fixed ciphertext the mask and ct-terms cancel across different AD
lengths, leaving `tag(L1) xor tag(L2) = top16(((8·L1) xor (8·L2))·H^2)` — GF(2)-linear
equations in `Y = H^2` that reach rank 64 in ~5 well-chosen lengths (`destruction_hsolve.py`
/ `find_lengths.py`, validated). The deliberately huge `MAX_AD_LENGTH = 2^20` is the
tell that this is the intended path — but it produces equations only *within one key*, and
the per-connection key discards them at reconnect.

**3. Per-connection information is bounded.**
* Option 1's tag mask is `E(J0)` with the nonce server-chosen (8 random bytes), so
 `J0 = nonce·H^3 ^ 64·H` is a fresh unknown per query — each query is a 16-bit equation
 *plus* 16 bits of new noise ⇒ ~0 bits about `H`.
* Option 2 lets us choose the nonce but reports only success/failure (`Sus.` is identical
 for tag-mismatch and tag-pass-no-flag), so a tag read costs ~2^16 attempts; we have 168.
* `H = E(0)` is never a keystream block: the counter increments **before** encryption and
 `ctr.to_bytes(8)` raises at `2^64` (verified), so no wrap into `E(0)`; a 2-byte nonce
 caps `J0` at 65535, and that `E(J0)` is consumed solely by the 2-byte tag.

So per connection at most ~16 bits about a 64-bit `H` can be extracted, and `H` is then
discarded. flag1 needs a `2^64` search, a 3DES break (`2^112+`), or a deployment key-reuse
bug — not an attack inside a 168-attempt window. (An independent Opus review, asked to
*assume* flag1 was solvable, agreed the only enabling bugs would be a loop that exposes
`E(J0)`, or a distinguishable tag-pass vs tag-fail.)

## Notes / Pitfalls

- **The 168-attempt budget is shared** between options 1 and 2, and even invalid input
 consumes an attempt — so don't waste submits on malformed payloads.
- **Do not wait for socket EOF.** The live wrapper keeps the connection open; stop on the
 168th `Attempts left:` line or a short idle timeout, or you lose ~10 s/connection.
- **`ad` cannot be shorter than 8 bytes** in practice: `encrypt(ad_len+4, P)` builds the AD
 by right-justifying 8 random ASCII letters into `ad_len+4` bytes, and `rjust` does not
 truncate — so "AD length 0" still yields an 8-byte AD (this is fine; the forgery uses the
 *same* `ad` as the leak, so it cancels).
- **Cross-connection tag pairing is dead** (fresh key, proven) — don't accumulate or pair
 tags across connections.
- **Don't over-parallelise.** The instance refuses >8 workers; two clean 8-worker sweeps
 already returned zero wins.
- **Dead ends, documented so they are not re-run:** 5-tag sweep then linear `H` solve (the
 `len_A·H^2` oracle caps at rank 36/64 with transmittable AD lengths — rank 64 needs
 constants ~2^61, i.e. AD lengths ~2^58 bytes, impossible); brute `H` (2^64); break 3DES
 (2^112+); birthday on 64-bit keystream blocks (only ~250 blocks/connection).
- **Artefacts in this folder:** `src/crypto-destruction/{encryption.py,server.py,Dockerfile}`
 (shipped source, confirmed byte-for-byte against the live service), the exploit harnesses
 listed above, `local_persist_server.py` + `logs/local_exploit.out` (persistent-
 key control that *does* recover `H` and pull a local flag1), and the proof files
 `FLAG1_UNREACHABLE_PROOF.md` / `flag1_FINAL_verdict.md`. Raw run logs are in
 `logs/` (`flag0_rerun.out`, `sweep_robust.out`).

### Local control (re-confirm the tooling)

```bash
FLAG0='PP{local0}' FLAG1='PP{local1}' \
 socat TCP-LISTEN:20041,fork,reuseaddr EXEC:"python3 -u local_persist_server.py" # key = bytes(range(24))
python3 destruction_persist_test.py 127.0.0.1 20041 8
# WIN on connection #351 (winning tag=e496)
# replay on a FRESH connection -> PP{local0} => KEY PERSISTS
```

Same harness against the live host (two clean 393-connection sweeps): zero valid tags ⇒
per-connection key.

### Recommendation to the organisers

The challenge's own Dockerfile (`socat … fork`) is what removes the key reuse the intended
`hsolve` depends on. flag1 is solvable only if `H` persists across connections (a single
long-lived server process). flag0 remains the obtainable, validated flag on this
deployment.
