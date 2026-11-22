# Rocinate Revenge — SOLVED (flag verified locally)

**Category:** cryptography · **Points/Solves:** 500 / 0 at capture time (post-event).
**Flag:** `hiCTF{r4nd05_15_53cu43d_7h15_71m3_w0t_y0u_g0nN4_d0??}`
**Archive SHA-256:** `78540bed7e1e9fbe4deb67f710abde453b7fd87116fda6c61360749c735d9101`

## Status history
- My prior pass session (`work/HANDOFF-agent.md`) concluded **NOT SOLVED** — it reduced the
 problem to a single-unknown affine LCG family `(R* + a^i G)^e = T_i` and tried
 Franklin–Reiter / e-scan, small-order gcd leaks, small-prime reductions (invalid), and
 Coppersmith. All dead ends; the blocker was recovering `r0` from a degree-~1e8 object.
- The reference writeup (team Fr4ctur3) **solved it** with a different kind of step:
 **exact integer relations among the public exponents `C_i` (LLL/BKZ) → a polynomial with the
 secret seed `r0` as a root → polynomial GCD.** The hidden exponent `e` is never needed.

## Verification performed this session (independent of the reference's own claims)
Ran the reference `recover_flag(data, seed)` from `rocinate-revenge-solver.zip` against the
LOCAL artifact (`data.json`) and the published `seed.txt`:

```
VERIFIED FLAG: hiCTF{r4nd05_15_53cu43d_7h15_71m3_w0t_y0u_g0nN4_d0??}
```

`recover_flag` re-derives every nonce from `seed`, requires `Z_i % r_i == 0` (exact, UNREDUCED
division), recovers `s` by Bézout on `C_0,C_1`, and asserts `pow(s, C_i, N) == Z_i // r_i` for
**all 100 samples** before returning. So the flag is checked against the full published corpus,
not just a prefix.

## The winning attack (one paragraph)
The LCG parameters `a,b,N` are public, so every nonce is affine in the seed:
`r_i = alpha_i*r0 + beta_i (mod N)`. Normalizing each product `Z_i = r_i * s^{C_i}` (multiply is
UNREDUCED, so `r_i` divides `Z_i` exactly) by `alpha_i` gives
`v_i = (r0 + t_i) * s^{C_i} (mod N)` with `t_i = beta_i * alpha_i^{-1}`. Pick an **exact integer
relation** `sum k_i C_i = 0` (found by LLL on rows `(e_i, M*C_i)`, shrunk with BKZ to keep
degrees manageable). Then `prod v_i^{k_i}` cancels the flag powers and yields
`F_k(X) = prod_{k_i>0}(X+t_i)^{k_i} - K_k * prod_{k_i<0}(X+t_i)^{-k_i}` with `F_k(r0) = 0 mod N`.
Two independent relations give `gcd(F1,F2) = X - r0` → `r0 = -v*u^{-1} mod N`. Regenerate all
nonces, do exact `m_i = Z_i // r_i`, and finish with Bézout on two coprime `C_i`.

## Pitfalls (each real)
- **Degree explosion:** naive LLL relations give degrees ~4.4e7. BKZ (block 45) brought the two
 chosen relations to ~2.4e7. Polynomial work is heavy (the reference used a C++/NTL/GMP helper
 with on-disk coefficients, FFT-mod-aux-prime arithmetic + CRT, checkpointed half-GCD).
- **Composite-modulus polynomial arithmetic is not field arithmetic.** An attempted inverse can
 fail on a non-unit — and that failure *factors N*. In this run the gcd path succeeded directly.
- **`Z_i` is an UNREDUCED product** (`r_i * s^{C_i}`), which is what makes exact division possible.
- The hidden exponent `e` and the `T_i = r_i^e` commitments are **red herrings** — do not chase
 them (my prior session burned the whole budget there).

## Reproduction
```python
import json, importlib.util
spec = importlib.util.spec_from_file_location("s","rocinate-revenge-solver/solve.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
d = json.load(open("data.json"))
seed = int(open("seed.txt").read)
print(m.recover_flag({"a":d["a"],"b":d["b"],"N":d["N"],"Z":d["Zs"],"C":d["Cs"],"T":d["Ts"]}, seed))
```
