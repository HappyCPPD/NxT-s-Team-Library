# TFC CTF 2026 — "1+1" Writeup

**Category:** Crypto 
**Flag:** `TFCCTF{nice_crypto_skillz_kid_you_will_be_great_one_day_af56c3}` 
**Solves:** TBD

---

## Challenge Overview

We are given a SageMath script `chall.sage` and its output file `output.py`.

### `chall.sage`

```python
from Crypto.Util.number import getPrime, bytes_to_long
import random

rbit = 444
pbit = 512

p = bytes_to_long(open('flag','rb').read)

xs = [p * getPrime(pbit) + random.randint(1,2**rbit) for _ in range(10)]

open('output.py', 'w').write(f'xs = {str(xs)}')
```

### `output.py`

A list of 10 large integers `xs[0]` through `xs[9]`, each roughly 1014–1015 bits.

---

## Problem Analysis

Each `x_i` is constructed as:

```
x_i = p * q_i + r_i
```

where:
- `p` is the flag interpreted as a big-endian integer
- `q_i` is a random 512-bit prime
- `r_i` is a random integer in `[1, 2^444)` (the "noise")

All 10 samples share the same secret `p`. The noise `r_i` is small relative to `p * q_i`. This is a classic **Approximate GCD (AGCD)** problem.

We know additional structure:
- `p` is about 503 bits (flag length ~62 bytes)
- The flag format is `TFCCTF{...}`

---

## Solution: Lattice-based AGCD

### The lattice construction

Given samples `x_0, x_1, ..., x_t`, we build the lattice:

```
 [ K x_1 x_2 ... x_t ]
 [ 0 -x_0 0 ... 0 ]
B = [ 0 0 -x_0 ... 0 ]
 [ ... ]
 [ 0 0 0 ... -x_0 ]
```

where `K = 2^ρ` is a scaling factor slightly above the noise bound (we used `K = 2^440`).

### Why this works

Consider the vector formed by `(q_0, q_1, ..., q_t)`:

```
(q_0, q_1, ..., q_t) * B = (q_0*K, q_0*x_1 - q_1*x_0, ..., q_0*x_t - q_t*x_0)
```

But `q_0*x_j - q_j*x_0 = q_0*(p*q_j + r_j) - q_j*(p*q_0 + r_0) = q_0*r_j - q_j*r_0`

So the target vector is:
```
v = (q_0*K, q_0*r_1 - q_1*r_0, ..., q_0*r_t - q_t*r_0)
```

Each `q_0*r_j - q_j*r_0` has norm roughly `2^512 * 2^444 ≈ 2^956`, which is **much smaller** than the lattice determinant. This vector is short enough that LLL will find it.

### Extracting p

After LLL reduction, the first vector `v` satisfies:
- `v[0] = q_0 * K` (since K divides the first component cleanly)

So we compute:
```
q_0 = v[0] / K
p = x_0 // q_0
```

And verify:
- `x_i mod p` is in `[1, 2^444)` for all i
- `(x_i - r_i) / p` is a ~512-bit number for all i

---

## Solver Code

```python
# SageMath
xs = [...] # from output.py

x0 = xs[0]
t = 9 # using all 10 samples
K = 2^440 # scaling factor

# Build the lattice
M = matrix(ZZ, t+1, t+1)
M[0, 0] = K
for j in range(1, t+1):
 M[0, j] = xs[j]
 M[j, j] = -x0

# LLL reduction
L = M.LLL
v = L[0]

# Extract p
q0 = abs(v[0]) // K
p = x0 // q0

# Decode the flag
flag = int(p).to_bytes((p.bit_length + 7) // 8, 'big').decode
print(flag)
```

**Output:** `TFCCTF{nice_crypto_skillz_kid_you_will_be_great_one_day_af56c3}`

---

## Verification

```
p = 17241452403663786258810204912837832078263072704452603141506605300586846995999095742236148609544181346294205288181468316200765146056445245980548526191485

For each x_i:
 r_i = x_i mod p (442-444 bits, within [1, 2^444))
 q_i = (x_i - r_i) / p (512 bits)
 x_i = p * q_i + r_i (holds exactly)
```

---

## Key Insight

The choice of `K` is crucial. If `K` is too large, the lattice doesn't find the right vector. If too small, the target vector isn't short enough. We found `K = 2^440` works well for this parameter set (`rbit = 444`, `pbit = 512`).

This is a standard application of the Howgrave-Graham approximate GCD attack, which is also the foundation of the original Gentry-Halevi FHE scheme's security analysis.