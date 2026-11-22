# RESULTS — Invisible Signal

STATUS: SOLVED. Flag recovered with live evidence.

FLAG: OWASP{Sou15_c4nt_b3_533n_bY_n0rm41_3y3s}

## Decoded character table (position → ASCII)

pos ascii char area(px) x_data y_data
 0 79 O 121 0.00 79.02
 1 87 W 139 1.00 87.05
 2 65 A 122 1.99 65.04
 3 83 S 121 3.00 83.04
 4 80 P 121 3.99 80.03
 5 123 { 121 5.00 123.02
 6 83 S 121 5.99 83.04
 7 111 o 121 7.00 111.00
 8 117 u 121 7.99 117.03
 9 49 1 121 9.00 49.00
10 53 5 121 9.99 53.02
11 95 _ 123 11.00 95.01
12 99 c 121 12.00 99.03
13 52 4 121 13.00 52.02
14 110 n 163 13.98 109.98
15 116 t 121 15.00 116.03
16 95 _ 121 16.00 95.01
17 98 b 121 17.00 98.03
18 51 3 121 18.00 51.01
19 95 _ 121 19.00 95.01
20 53 5 121 20.00 53.02
21 51 3 121 21.00 51.01
22 51 3 121 22.00 51.01
23 110 n 121 23.00 109.99
24 95 _ 179 23.98 94.93
25 98 b 121 25.00 98.03
26 89 Y 121 26.00 89.03
27 95 _ 121 27.00 95.01
28 110 n 121 28.00 109.99
29 48 0 121 29.00 48.05
30 114 r 121 30.01 114.02
31 109 m 121 31.00 109.04
32 52 4 121 32.01 52.02
33 49 1 121 33.00 49.00
34 95 _ 121 34.01 95.01
35 51 3 121 35.00 51.01
36 121 y 121 36.01 121.01
37 51 3 121 37.00 51.01
38 115 s 121 38.01 115.02
39 125 } 121 39.00 125.03

All 40 markers: |x - round(x)| < 0.02, area 121 ± 2 (a few are 139–179 due to a
coincident noise marker overlapping the payload marker). Noise markers are area ≈ 61.
Position 40 is empty (end of message).

## Coverage / method notes
- Primary discriminator = connected-component area of markers thresholded at grey ≥ 45 (COMPLETE: all 40 payload markers found, none missing).
- Area alone is NOT a clean separator: two coincidental double-noise overlaps reach area ≈ 106 at x = 25.01 and 37.01. Payload markers are area 121 ± 2 at |x-int| ≤ 0.02; the decoder disambiguates by nearest-to-integer-x per column.
- Axis calibration validated independently by two end-of-range values ('{' = 123, '}' = 125 both exact) — calibration is not merely assumed.
- Ruled out: encoding via marker brightness alone (false positives from overlapping noise), via the sine-curve "signal" (decoy), via non-integer x spacing (payload is exactly at integer positions).

## Verification (ad-hoc, run 2026-10-09)
No test suite exists; verification is a focused ad-hoc script (`<verification script>`, since removed). It checks, independently of `decode.py`'s per-column logic:
1. `decode.py signal.png` exits 0 and its `FLAG:` line equals the expected string.
2. `flag.txt` equals the expected string.
3. A whole-image single-pass labelling + nearest-integer-column assignment re-derives the identical flag; asserts columns 0..39 exactly once each.

Result: PASS. `components=1038 payload=40 dup_cols_flagged=2 noise_median_area=61 payload_area=121-179`.
This is ad-hoc verification of one solver, not suite-green.

## Prove it
```bash
python3 decode.py signal.png
```
