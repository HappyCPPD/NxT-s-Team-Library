---
title: "Ron's Revenge"
ctf: "platypwnies 2026"
date: 2026-11-14
category: crypto
difficulty: 2
flags:
 - PP{st4t3s1z3_w4s_n0t_th3_m41n_pr0bl3m::MyazN90an3Fx}
---

# Ron's Revenge (crypto, difficulty 2) — 1 flag

## Summary

A hand-rolled, **variable-state-size RC4** ("Ron's Revenge" / "eight times the size, eight
times the fun"). The service encrypts a fixed flag under a key built from a *client-chosen
3-word IV* concatenated with an 8-word long-term key, and lets you re-encrypt as often as
you like with any IV. The words are `random.seed(flag); [randrange(2048) for _ in range(8)]`.

The intended-looking red herring is the **state size** (`N = 2048`, i.e. "8×" the classic
256) — but state size is not the bug. The bug is the **IV-prefix key structure**: it is
exactly the WEP / FMS *related-key* setting. By choosing `IV = (B+3, N-1, X)` you force the
KSA to place known values in a way that makes the first PRGA output `Z1` a strong function
of the single unknown key word `K[B]`; a vote over many IVs recovers the secret words one at
a time. The flag's known prefix `PP{` makes the first two keystream bytes known from any
single ciphertext, so every vote is exact.

**The state size was not the main problem** (the flag says as much): a 256-word state would
fall to the same attack, because the weakness is structural in how the IV and the long-term
key are concatenated, not in the PRG's state width.

## Solution / Exploit

Exploit: `ronsrevenge_exploit.py`

```bash
python3 ronsrevenge_exploit.py HOST PORT # or HOST:PORT
# knobs: --samples (IVs per secret word, default 1000), --prefix, --seed
```

### The cipher (`server.py`)

```python
class RC4_1: # classic RC4, state_size = 2048
 def ksa(self):
 self.state = [i for i in range(self.state_size)]
 j = 0
 for i in range(self.state_size):
 j = (j + self.state[i] + self.key[i % self.key_length]) % self.state_size
 self.state[i], self.state[j] = self.state[j], self.state[i]
 def __next__(self):
 self.a = (self.a + 1) % self.state_size
 self.b = (self.b + self.state[self.a]) % self.state_size
 self.state[self.a], self.state[self.b] = self.state[self.b], self.state[self.a]
 return self.state[(self.state[self.a] + self.state[self.b]) % self.state_size]
```

`Stream` **bit-packs** the `log2(2048) = 11`-bit PRGA outputs into bytes, so
`ciphertext byte 0 = Z1 >> 3` and `byte 1 = ((Z1 & 7) << 5) | (Z2 >> 6)` — the first two
keystream bytes reconstruct the **entire 11-bit `Z1`**.

```python
def encryption_service(flag, state_size):
 random.seed(flag)
 longterm_key = [random.randrange(state_size) for _ in range(8)]
 print(longterm_key, file=sys.stderr) # debug leftover, not on the socket
 while True:
 iv = list(map(lambda s: int(s, 16), input('IV: ').strip.split(','))) # 3 words
 cipher = Stream(iv + longterm_key, state_size) # key = IV(3) || secret(8)
 print(cipher.encrypt(flag).hex)
```

### The FMS/related-key vote

Query with `IV = (B+3, N-1, X)` for the target word index `B` (we recover `K[0]`, then
`K[1]`, …). The KSA prefix is then fully determined by the *known* words:

```
KSA i=0 : j = B+3 -> S[B+3]=0, S[0]=B+3
KSA i=1 : j = (B+3 + 1 + N-1) = B+3 (mod N) -> S[1]=0, S[B+3]=1
```

With probability ~4–5% neither position `1` nor `B+3` is touched again for the rest of the
KSA, so the first PRGA output is

```
Z1 = S[S[1] + S[S[1]]] = S[0 + S[0]] = S[B+3] = 1
```

`K[B]` is consumed at KSA step `3 + B`, so for each candidate word value we simulate just
the known KSA prefix, apply the candidate at step `3+B`, and **predict `Z1`**. The correct
candidate matches the observed `Z1` ~4–5% of the time, versus ~`1/2048` for a wrong one. So
one round of ~1000 chosen IVs is enough to identify `K[B]` by plurality vote.

```python
def vote_word(b, known, samples):
 votes = [0]*N; step = 3 + b
 for iv, obs in samples:
 state = list(range(N)); j = 0
 for i in range(step): # known KSA prefix
 kv = iv[i] if i < 3 else known[i-3]
 j = (j + state[i] + kv) % N
 state[i], state[j] = state[j], state[i]
 s_step = state[step]
 for g in range(N): # try each candidate for K[b]
 j2 = (j + s_step + g) % N; vj = state[j2]
 state[step] = vj; state[j2] = s_step
 s1 = state[1]
 if state[(s1 + state[s1]) % N] == obs:
 votes[g] += 1
 state[step] = s_step; state[j2] = vj # undo
 return max(range(N), key=votes.__getitem__), ...
```

### Getting `Z1` from a ciphertext

`Z1` is recovered with the known plaintext prefix: `ks0 = ct[0] ^ ord('P')`,
`ks1 = ct[1] ^ ord('P')`, then `Z1 = (ks0 << 3) | (ks1 >> 5)`. The exploit tries the
plausible prefixes `PP`, `pl`, `pp`, `fl`, `CT` and keeps the one that produces a strong
FMS signal (`v1 >= 12 and v1 >= 3·v2`) on `K[0]`.

### Verification

Once all 8 words are recovered, decrypt two ciphertexts taken under different IVs; a
correct key yields **the same printable flag** both times (`PP{…}`), a wrong key yields
differing garbage.

```bash
[*] trying known-plaintext prefix b'PP' (1000 IVs/word)
 K[0] = ... votes=.. (runner-up ..)
 ...
[+] recovered long-term key = [...]
[*] decrypted: b'PP{st4t3s1z3_w4s_n0t_th3_m41n_pr0bl3m::MyazN90an3Fx}'
[+] FLAG: PP{st4t3s1z3_w4s_n0t_th3_m41n_pr0bl3m::MyazN90an3Fx}
```

## Flag

```
PP{st4t3s1z3_w4s_n0t_th3_m41n_pr0bl3m::MyazN90an3Fx}
```

## Notes / Pitfalls

- **Brute-forcing the seed does not work, and is not needed.** The key is
 `seed(flag)`-derived, so one *could* try to invert the RNG — but the FMS attack recovers
 the words directly and never touches the seed.
- **The `print(longterm_key, file=sys.stderr)` is a decoy.** Under the Dockerfile's
 `socat … EXEC:python server.py`, stderr does **not** go to the socket, so the key is not
 actually leaked. Do not count on it.
- **Bit-packing is easy to get wrong.** The 11-bit outputs are not byte-aligned; only the
 known prefix lets you fill in the missing low bits of `Z1` from `ct[1]`. Verify your local
 `Stream` against the `test` vectors in `server.py` (`RC4_1(b'Key',256)` → `EB9F7781…`).
- **Weak margins happen.** Sometimes the runner-up is close; the exploit logs
 `[!] weak margin for K[b]` and the outer loop retries with more IVs (1000 → 2000 → 4000
 …) and re-verifies. Have the retry path — a single bad word silently produces garbage.
- **Prefix matters only through `Z1`.** Prefixes that yield the same `Z1` (e.g. `PP` vs
 `PW`) work equally well, which is why prefix auto-detection is cheap.
- The deployment is one process per TCP connection (`socat fork`), and the long-term key is
 fixed for the lifetime of a connection — so all queries for one recovery must stay on the
 same socket (the exploit does).
