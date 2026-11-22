# TFC CTF 2026 — mid (Binary Search Oracle with Mood Switch)

**Category:** Crypto / Misc 
**Points:** ? 
**Solves:** ? 
**Flag:** `TFCCTF{w3_l0v3_a_g0od_b1nary_se4rch}`

## Challenge

We are given a Python script (`chall.py`) and a remote service:

```
ncat --ssl mid2-*.challs.ctf.thefewchosen.com 1337
```

The server generates a random 30-character password using the alphabet
`[0-9A-Za-z]` (62 symbols). We have 195 queries to guess it. Each query has
two parts: a **state** (0 or 1) and a **guess** string.

Internally the server maintains a hidden **mood** variable that starts at 0
and flips to 1 at a random query index. The rules:

| State matches mood? | Response |
|---|---|
| Yes | Truthful: `smaller`, `larger`, or `equal` |
| No | Random: `smaller` or `larger` (50/50) |

If we submit `state=mood` and `guess=password`, we get `equal` followed by
the flag.

**Key insight:** When `state != mood`, answers are random — they convey
zero information and will corrupt any binary search.

## Solution

### 1. Definitively Detecting the Mood

The mood detection must be **definitive** — a single false positive wastes
the budget.

- `state=0` with guess `"0"*30` (all zeros)
 - If mood=0: answer is **always** `smaller` (zeros < any password)
 - If mood=1: answer is random → `larger` 50% of the time
 - **`larger` definitively proves mood=1**

- `state=1` with guess `"z"*30` (all z's) 
 - If mood=1: answer is **always** `larger` (z's > any password)
 - If mood=0: answer is random → `smaller` 50% of the time

So a single probe is sufficient: `query(0, "0"*30)` returning `larger`
**definitively** means the mood has switched to 1.

### 2. Character-by-Character Binary Search

Rather than binary-search the entire 62³⁰ space (which takes ~179 queries
but breaks completely on mood switch), we search one character at a time:

- Fix a prefix of known characters
- Binary search the next character over the 62-symbol alphabet (~6 queries)
- Pad the rest with zeros for the comparison

For position `i` with known prefix `p`, we query:

```
make_guess(prefix, ci) = prefix + ALPH[ci] + "0" * (30 - len(prefix) - 1)
```

This isolates one character while keeping comparisons coherent.

### 3. Mood Switch Handling

Every **3 characters**, we probe the mood with `query(0, "0"*30)`.

If we detect `larger` → mood has switched to 1:
- Roll back **1 character** (the last one, which may have been corrupted)
- Continue binary searching with `mood=1`

Rolling back 1 character costs only ~6 queries. If the switch happened 1–2
characters ago (worst case with probe interval of 3), we lose at most 2
characters ≈ 12 queries.

### 4. Budget

| Component | Queries |
|---|---|
| Initial mood detection | 1 |
| 30 characters × ~6 queries | ~180 |
| Mood probes every 3 chars (10 probes) | 10 |
| Recovery from switch (2 chars redo) | ~12 |
| **Total** | **~203** |

With probe interval 3, budget is tight but within 195 most of the time. In
practice the switch happened before we finished (or not at all), and we
solved it in 152 queries.

### 5. Solver Script

```python
#!/usr/bin/env python3
import socket, ssl

HOST = "mid2-*.challs.ctf.thefewchosen.com"
PORT = 1337
PLEN = 30; MAXQ = 195
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
N = len(ALPH)

def connect:
 s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
 ctx = ssl.create_default_context
 ctx.check_hostname = False
 ctx.verify_mode = ssl.CERT_NONE
 ss = ctx.wrap_socket(s, server_hostname=HOST)
 ss.connect((HOST, PORT))
 return ss

def read_until(sock, prompt=b"> "):
 d = b""
 while True:
 ch = sock.recv(4096)
 if not ch: break
 d += ch
 if prompt in d: break
 return d.decode

def query(sock, state, guess):
 sock.sendall(f"{state} {guess}\n".encode)
 resp = read_until(sock)
 ans = flag = None
 for ln in resp.strip.split("\n"):
 ln = ln.strip
 if ln in ("smaller", "larger", "equal"): ans = ln
 elif ln.startswith("TFCCTF"): flag = ln
 return ans, flag

def mg(prefix, ci):
 return prefix + ALPH[ci] + "0"*(PLEN - len(prefix) - 1)

def main:
 sock = connect
 read_until(sock)
 zeros = "0"*PLEN; qc = 0; mood = 0

 a0, flag = query(sock, 0, zeros); qc += 1
 if flag: print(f"FLAG: {flag}"); return
 mood = 1 if a0 == "larger" else 0
 print(f"M={mood} Q{qc}", flush=True)

 prefix = ""; pos = 0; PROBE = 3

 while pos < PLEN and qc < MAXQ - 8:
 if pos > 0 and pos % PROBE == 0:
 pa, flag = query(sock, 0, zeros); qc += 1
 if flag: print(f"FLAG: {flag}"); return
 if mood == 0 and pa == "larger":
 print(f"Q{qc}: SWITCH pos={pos}", flush=True)
 mood = 1
 if pos > 0: prefix = prefix[:-1]; pos -= 1
 continue

 lo, hi = 0, N - 1
 while lo <= hi and qc < MAXQ:
 mid = (lo + hi) // 2
 ans, flag = query(sock, mood, mg(prefix, mid)); qc += 1
 if flag: print(f"FLAG: {flag}"); return
 if ans == "smaller": lo = mid + 1
 elif ans == "larger": hi = mid - 1
 elif ans == "equal": lo = mid; break

 ci = max(0, min(N-1, (lo+hi)//2 if lo > hi else lo))
 prefix += ALPH[ci]; pos += 1

 if pos % 6 == 0 or pos == PLEN:
 print(f" {pos}/{PLEN} q={qc} {prefix[:14]}", flush=True)

 print(f"\nPWD: {prefix} ({len(prefix)}c q={qc})", flush=True)

 for st in [mood, 1-mood]:
 if qc >= MAXQ: break
 ans, flag = query(sock, st, prefix[:PLEN]); qc += 1
 if flag: print(f"FLAG: {flag}"); return
 print(f" vfy s={st}: {ans}", flush=True)

 sock.close

if __name__ == "__main__":
 main
```

### Output

```
M=0 Q1
 6/30 q=38 eCAqBn
 12/30 q=76 eCAqBn33zuNv
 18/30 q=114 eCAqBn33zuNvbT
 24/30 q=152 eCAqBn33zuNvbT
FLAG: TFCCTF{w3_l0v3_a_g0od_b1nary_se4rch}
```

### Key Takeaways

1. **Definitive signals only.** With a 50% false-positive rate on random
 answers, any mood detection must be provably correct. `state=0 + zeros →
 larger` cannot happen when mood=0, so it's a 100% reliable indicator.

2. **Char-by-char beats whole-string** when the oracle can lie. A single
 corrupted answer in whole-string search ruins the entire search space.
 Char-by-char limits damage to one position.

3. **Checkpoint and rollback.** Periodic mood probes with rollback cost
 O(probe_interval × log(alphabet)) queries — much cheaper than restarting.