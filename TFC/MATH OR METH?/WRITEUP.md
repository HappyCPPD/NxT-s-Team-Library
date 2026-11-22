# MATH OR METH?

**Category:** Crypto 
**Points:** 298

## Flag

```text
TFCCTF{this_is_a_very_very_long_flag_for_a_short_ctf_chall_ggs}
```

## Challenge overview

The challenge converts the flag body into an integer and writes that integer as
little-endian base-33 digits:

```python
base = B + 1 # 33
while x:
 row.append(x % base)
 x //= base
```

Consequently, the planted row satisfies

```text
x = sum(row[j] * 33^j for j in range(m))
```

with every coordinate between 0 and 32.

The generated matrix `A` has 57 rows and 88 columns. One randomly selected row
is replaced with the flag's digit vector. The published vector is

```text
h[j] = sum(a[i] * A[i][j] for i in range(n)) mod p.
```

Equivalently, if `a` is regarded as a row vector,

```text
h = a A (mod p).
```

Only `h` and the public parameters are provided; neither `a` nor `A` is
published.

## Vulnerability

Consider the modular-relation lattice

```text
L = {v in Z^88 : <h, v> = 0 mod p}.
```

Every integer null-vector of `A` belongs to this lattice. If `A v = 0`, then

```text
<h, v> = a A v = 0 mod p.
```

Since `A` has 57 rows and 88 columns, its expected nullity is

```text
m - n = 88 - 57 = 31.
```

These 31 integer null-vectors are unusually short because all entries of `A`
are small. In contrast, an ordinary vector satisfying only the single modular
relation is much larger because `p` is a 1084-bit prime. Applying LLL to `L`
therefore reveals precisely these 31 short vectors.

Let the recovered short relations be the rows of a matrix `Y`. Every original
row of `A` is orthogonal to `Y`, so the integer right kernel of `Y` contains the
row lattice of `A`:

```text
Y * A[i]^T = 0.
```

This right kernel has rank 57. Applying LLL again produces short vectors in the
hidden row lattice. Searching those vectors, their signs, and small pairwise
combinations reveals a vector whose 88 coordinates all lie in `[0, 32]` and
whose base-33 decoding is printable text.

## Recovery

The recovered base-33 row decodes as follows:

```text
this_is_a_very_very_long_flag_for_a_short_ctf_chall_ggs
```

The challenge source instructs us to wrap the recovered body in `TFCCTF{}`.
Thus the final flag is

```text
TFCCTF{this_is_a_very_very_long_flag_for_a_short_ctf_chall_ggs}
```

## Solver

The accompanying SageMath solver is located one directory above this write-up:

```text
../solve_math_or_meth.sage
```

Run it from the repository root with:

```bash
sage solve_math_or_meth.sage
```

The important output is:

```text
short modular relations: 31
relation rank: 31
row lattice: 57 88
CANDIDATE b'this_is_a_very_very_long_flag_for_a_short_ctf_chall_ggs'
```
