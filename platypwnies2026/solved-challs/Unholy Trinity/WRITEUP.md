# Unholy Trinity — crypto (difficulty 2)

Status: exploit written & verified locally (3/3 runs, dummy flags); live instance NOT contacted.

## Vulnerability

`hash_pw(x) = x^e mod N` with `e = 17`, N = p·q (two 1337-bit primes). Two independent flaws:

### flag0 — hash "commitment" collisions (no domain separation)
Registration rejects duplicate *passwords* but only compares `hash_pw(pw)`, and passwords must be
exactly `NLEN = ceil(bits(N)/8)` bytes. Since `NLEN` bytes can hold values larger than N, two
distinct byte strings with `pw2 = pw1 + N` hash identically (`(pw1+N)^e ≡ pw1^e mod N`).
The server notices the duplicated hash and prints `FLAG0`.

### flag1 — small-exponent "encryption" with no modular wrap (integer 17th root)
`admin_secret` is only 19 bytes (≤ 152 bits), so
`admin_hash = admin_secret^17 < 2^2584` while `N ≥ 2^2672` — the exponentiation **never reduces
mod N**. Taking the plain integer 17th root of the leaked hash recovers the admin password.

The hash is leaked by the login prompt itself:
`Authenticating 'admin' with committed pw_hash <h>...`, and the σ-protocol check
`response^e ≡ announcement · pw_hash^chal (mod N)` is then trivially satisfiable with the
known `m = admin_secret`: pick random `k`, send `announcement = k^e mod N`, reply
`response = k · m^chal mod N` (chal ∈ [0,16]).

All 52 rounds must pass in one connection (a failure kills the server), and socat forks a fresh
process per connection (new N / new admin_secret) — so flag0 and flag1 must be collected in the
**same** session: register the colliding pair first, then log in as admin.

## Exploit
`unholytrinity_exploit.py` (stdlib only, no pwntools required):

```
python3 unholytrinity_exploit.py --host HOST --port PORT
python3 unholytrinity_exploit.py --local # spawns server.py with dummy flags
```

Local result:
```
[*] N has 2674 bits, NLEN=335, e=17, rounds=52
[+] flag0 = PP{LOCAL_FLAG0_collision}
[+] recovered admin_secret (19 bytes): b'z\xd7Yu...'
[+] flag1 = PP{LOCAL_FLAG1_root}
```
Also verified over real TCP against `socat TCP-LISTEN:1338,fork EXEC:"python3 -u server.py"`.
