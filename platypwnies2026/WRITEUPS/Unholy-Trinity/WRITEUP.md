---
title: "Unholy Trinity"
ctf: "platypwnies 2026"
date: 2026-11-14
category: crypto
difficulty: 2
flags:
 - PP{modulo_hashing_is_not_collision_resistant::fGWQMe7UvDiF}
 - PP{rsa_messages_need_to_be_sufficiently_large::89gDoeIsXkoC}
---

# Unholy Trinity (crypto, difficulty 2) — 2 flags

## Summary

"Commitments are basically hashes, signatures are essentially hashes, and hashes are
fundamentally encryption" — so the challenge *is* the hash. `hash_pw(pw) = b2l(pw)^e mod N`
with `e = 17` and a per-connection 1337-bit-prime RSA modulus `N`. Two bugs, both classic
RSA misuse:

- **flag0 — no domain separation ⇒ trivial collision.** The "hash" is just modular
 exponentiation of the raw password integer with no salt/padding/domain tag. Two distinct
 `NLEN`-byte passwords `x` and `x + N` satisfy `x ≡ x+N (mod N)`, hence
 `hash(x) == hash(x+N)`. The register routine treats a hash collision as an "unexpected
 database storage optimization" and prints flag0.

- **flag1 — small message, no modular wrap ⇒ integer root.** `admin_secret` is only **19
 bytes** (≤ 152 bits), so `admin_secret^17 < 2^2584` while `N ≥ 2^2672` (two 1337-bit
 primes). The modular reduction never happens: `pw_hash = admin_secret^17` **as an exact
 integer**. The login banner leaks `admin`'s `pw_hash`, so we take the plain integer 17th
 root to recover the admin password, then answer the challenge/response.

Both flags live in **one connection** — `N` and `admin_secret` are fresh per TCP connection
(`socat fork EXEC:python server.py`), so flag0 (register) and flag1 (login as admin) must
be done in the same session.

## Solution / Exploit

Exploit: `unholytrinity_exploit.py`

```bash
python3 unholytrinity_exploit.py --host HOST --port PORT
python3 unholytrinity_exploit.py --local # spawns server.py with dummy flags
```

### The primitive

```python
def hash_pw(pw: bytes) -> int:
 return pow(b2l(pw), e, N) # e = 17, N = p*q (2 x 1337-bit primes)
```

Server banner gives `N` and `e`; `NLEN = (N.bit_length+7)//8` = 335 bytes.

### flag0 — collision via `x` and `x + N`

```python
pw1 = make_password(NLEN) # NLEN bytes, satisfies password policy
v1 = int.from_bytes(pw1, "big")
v2 = v1 + N # fits in 8*NLEN bits -> still NLEN bytes
pw2 = v2.to_bytes(NLEN, "big")
# hash_pw(pw1) == pow(v1, e, N) == pow(v1+N, e, N) == hash_pw(pw2)
```

Register `pw1` as `alice`, then `pw2` as `bob`. The `audit_log` collision check fires:

```
ERROR: Something happened. It was probably a pentest. Have this for now:
PP{modulo_hashing_is_not_collision_resistant::fGWQMe7UvDiF}
```

Notes on the password policy (it is enforced *before* the hash): `str(password)` is checked
for one lowercase, one uppercase, one digit and one special char, and `len == NLEN`. The
solver builds `head = b"A9!"` and pads with random bytes; both `pw1` and `pw2` must be
distinct and pass the policy, so a few random attempts may be needed.

### flag1 — integer 17th root of the leaked hash

The login path prints the committed hash before the challenge/response:

```
Authenticating 'admin' with committed pw_hash <int>...
```

Because `admin_secret < 2^152` and `e = 17`, `pw_hash = admin_secret^17` with **no**
modular reduction. Take the exact integer root:

```python
def iroot(x, n): # exact integer n-th root, raises if not perfect
 ...
secret = iroot(h, e)
assert pow(secret, e) == h # verified
```

Now login as `admin`. The server runs a Fiat–Shamir-style protocol for
`ROUNDS = 256 // e.bit_length + 1 = 65` rounds:

1. We send `announcement = k^e mod N` for a random `k` (with `gcd`, `≠0` checks).
2. Server replies `Challenge: c` with `c` a random hash mod `e`.
3. We reply `response = k · secret^c mod N`, which satisfies
 `response^e ≡ announcement · pw_hash^c (mod N)`.

Knowing `secret` we answer every round correctly, and the server prints the flag:

```
Welcome, admin!
Here is your flag: PP{rsa_messages_need_to_be_sufficiently_large::89gDoeIsXkoC}
```

## Flags

```
PP{modulo_hashing_is_not_collision_resistant::fGWQMe7UvDiF} # flag0 (collision)
PP{rsa_messages_need_to_be_sufficiently_large::89gDoeIsXkoC} # flag1 (integer root)
```

## Notes / Pitfalls

- **One connection only.** `N`, `d` and `admin_secret` are regenerated in a fresh process
 per TCP connection. Get flag0 and flag1 in the same socket.
- **A failed login kills the server.** `main` exits with
 `MITM detected. Shutting down server for security reasons.` on any failed round — so once
 you start the admin login you must answer every one of the 65 rounds correctly. Recovery
 first, then login.
- **The `e = 17` root is only valid because the message is small.** This is the whole
 point: if `admin_secret` were large enough that `secret^17 ≥ N`, the reduction would
 apply and the root would fail (the exploit's `assert pow(secret, e) == h` catches this).
- **Collision needs `v1 + N` to still fit in `NLEN` bytes**, i.e. `v1` must be small enough.
 The solver retries random `v1` until both passwords satisfy the policy and the byte length.
- **`d = pow(e, -1, (p-1)(q-1))`** is computed at startup; if `gcd(e, (p-1)(q-1)) != 1` the
 loop retries. Irrelevant to the attack but explains the banner delay.
- The contrived "zero-knowledge server authentication" is just textbook RSA
 challenge/response; there is no zero-knowledge here, and no signature forgery is needed —
 the leaked hash is the only break.
