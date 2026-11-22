# brew&drew

**CTF:** h4ckc0n 2026 · **Category:** crypto · **Points:** 200 · **Author:** pr4njal

**Flag:** `d4rk{0bV_DUHHH?}`

## Challenge

> These two twins brew and drew are communicating, they talk less but when they do they use weird crypto-schemes, we tried to log the start of it.

We get `logged_convo.txt`, six decimal integers of about 1750 bits each, alternating between `brew:` and `drew:`.

## TL;DR

Each integer is a `k` value for Tupper's self-referential formula. Divide by 17, plot the bits as a 17-pixel-tall bitmap, and read the conversation. The fifth message is the flag.

## What the numbers look like

There is no modulus, no exponent and no key, so this is not RSA or anything like it. The useful observations were all about the number 17:

- Every integer is divisible by 17.
- Pairwise GCDs are only `2^k · 17^m`, so there are no shared primes to exploit.
- The binary autocorrelation of each integer peaks at multiples of 17.
- Written in base `2^17`, the digits form short zero-separated groups that are often palindromes, such as `[255, 8, 8, 8, 255]` and `[60, 66, 129, 66, 60]`.

That last point is what gives it away. `255, 8, 8, 8, 255` is not ciphertext. It is the letter **H** drawn as five pixel columns: a full bar, three columns with one middle pixel, and another full bar. `60, 66, 129, 66, 60` is an **O**. The palindromes are just letters that are left-right symmetric, and the repeated groups are repeated letters.

A number that is a multiple of 17 and encodes a bitmap 17 pixels tall is Tupper's formula.

## Tupper's self-referential formula

```
1/2 < floor( mod( floor(y/17) · 2^(-17·floor(x) - mod(floor(y), 17)), 2 ) )
```

Plotted over `0 ≤ x < 106` and `k ≤ y < k + 17`, the formula draws a 106×17 bitmap. Stripped of the notation, it says:

> pixel `(x, y)` is on when bit `17·x + y` of `k / 17` is set.

So `k` is the bitmap read column by column, multiplied by 17. Decoding is a division and a bit test.

## Solve

```python
import re
from PIL import Image

ns = [int(x) for x in re.findall(r"\d{50,}", open("logged_convo.txt").read)]

S = 8 # pixel scale
im = Image.new("L", (106 * S, len(ns) * 19 * S), 255)
for i, k in enumerate(ns):
 assert k % 17 == 0
 N = k // 17
 for x in range(106):
 for y in range(17):
 if (N >> (17 * x + y)) & 1:
 X, Y = 105 - x, i * 19 + 1 + y
 im.paste(0, (X * S, Y * S, X * S + S, Y * S + S))
im.save("out.png")
```

The `105 - x` is the usual Tupper mirroring. Without it the text comes out reversed.

## Output

| Speaker | Message |
|---|---|
| brew | Hi! HOW ARE YOU? |
| drew | I AM SCARED ☹ |
| brew | WHY??? |
| drew | Is This Safe? |
| brew | `d4rk{0bV_DUHHH?}` |
| drew | Ok! Thanks ☺ |

The `0` is a slashed zero in the bitmap, and the `b` has a full-height ascender, so neither is ambiguous once rendered.

## What went wrong first

A lot of time went into treating the integers as ciphertext: factoring the cofactors, batch GCD, recurrences, XOR and affine byte transforms, and trying to deconvolve the base-`2^17` digits against an unknown "kernel". The structure had already been found (17, base `2^17`, palindromic digit groups), but it was read as algebra instead of as a picture.

The lesson is to print the bits as a grid before reaching for number theory. Palindromic digit groups in a fixed-width base are a strong hint that you are looking at glyph columns.
