# brew&drew — deep-analysis notes (agent hz, 2026-11-15)

STATUS: UNSOLVED (clean structural characterisation done; flag not recovered)

## Data
logged_convo.txt = 6 integers (~1750 bits each), alternating brew:/drew:, no hidden bytes
(only ASCII digits; verified with od/byte histogram). re-solve: 6 values X0..X5.

## PROVEN structural facts
1. v2(n) = 448, 686, 1093, 837, 161, 840 (all even numbers, huge 2-adic valuation).
2. Every n is divisible by 17 (X0,X2 by 17^2). Pairwise gcd(Xi,Xj) = 2^min(v2)*17^(0..2)
 — i.e. NO shared large primes, NO hidden RSA structure. Cores are pairwise coprime.
3. Binary autocorrelation of each n peaks at multiples of 17 (17,34,51,68,85,102,119,...).
4. KEY: for each n there is a shift s (s = 4,4,4,3,3,3 for X0..X5) such that ALL
 base-2^17 digits of (n >> s) are divisible by 17*2^e (e = 4,3,3,2,1,2).
 Raw digit max is ~69500 ~= 17*4096 for EVERY number.
 => n = 17 * U, U = sum_j u_j * (2^17)^j, u_j = 2^e * w_j, w_j <= 255 (X0) .. 2047 (X4).
5. The u_j / w_j sequences contain ZERO-separated "words" that are PALINDROMIC, e.g.
 X0: [255,8,8,8,255], [232], [191], [255,8,8,255], [60,66,129,66,60],
 [127,128,64,48,64,128,127], [7,8,240,8,7], [252,18,17,18,252]
 X4: [2047,16,16,16,2047] (x4), [1024,1024,1024,1024], [511,512,1024,1024,1024,512,511]
 Repeated words within a number => repeated characters.
 One word value (base-2^17) is shared between X3 and X5 exactly (684557176480465296).
 => the message is encoded by a *multiplicative convolution* (word = conv of chars with a
 short palindromic kernel), i.e. W' (digits = w_j) = M (*) K.
6. gcd of all W' = pure power of two (2^158) => no common kernel factor across messages.
7. 17 is NOT a divisor of any other natural constant tested (2^17+/-1, 65537, 43691, ...).
 n/(17*2^a) is NOT a perfect power for any a<=23, e in 2..8. Not squares/cubes/17th powers.

## Attacks tried and FAILED (all reproducible in brewdrew_hz*.py)
- gcd / shared-prime / batch-GCD: nothing but 2^k*17.
- Recurrence: x_{i+1}=x_i^2 mod N, x^e mod N (e<=8), LCG, XOR(=M^(M<<k), M^(M>>k)), all gcd tests.
- Byte/digit extraction (base 2..1024, incl. 17^k, 2^k*17^m, 127/128), both orders: no ascii/'d4rk'.
- Interleave / spread extraction (bit strides 2..178), complement, bit/byte/nibble reversals.
- Affine byte transforms per number (x*a^-1+b mod 256), repeating-key XOR/ADD/SUB (per-column break).
- Base64 packing of 12-bit units; 12/13..17-bit re-packing.
- Multiplicative kernels: divide by 2^k+/-1 (k<=1900), repunits (base 2^17), B^t+/-1, all tested
 divisors — no quotient yields text.
- Round-pair combos: sum/diff/xor/and/or of X0..X5 and of their unit sequences, top-aligned.
- Continued fractions of ratios show near-rationals (127/128, 1023/1024...) but no exact relation.
- Perfect "consecutive-integer" forms M(M+c), triangular 4V+1/8V+1: no.
- Web: no public writeup (h4ckc0n 2026 has no archived tasks; description search negative).

## WHERE IT IS BLOCKED
W' (base-2^17 digits = w_j) is *convolution-shaped* => W' = M (*) K, M = message bytes
(ASCII), K = unknown "weird-scheme" kernel. All simple/likely K (B+/-1, repunits, powers,
small ints, palindromic windows) fail. Either K is per-message/random-looking, or the
per-character encoding differs (e.g. K is itself derived from the message), so blind
deconvolution is needed. No flag fabricated.

## Next candidates if resumed
(a) Blind deconvolution of W' with ASCII constraint on M (search K with carry model).
(b) Factor the ~650-bit core cofactors (X2) to see whether the message is a multiplicative
 factor (needs ECM/QS; laptop limits — NOT run).
(c) Test K = the *other* twin's message digits (cross deconvolution) with proper alignment.
