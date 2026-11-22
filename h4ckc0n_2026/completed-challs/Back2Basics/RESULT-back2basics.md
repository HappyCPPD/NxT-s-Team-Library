# RESULT — Back2Basics (Web, 100 pts)

STATUS: SOLVED (all 6 fragments verified directly from the live server by the lead)

FLAG: d4rk{r0b0t_1D0R_J\\/\\/T_5Q1_T0(T0U_P0LYF1LL}

## The six fragments (each printed by the server as "[n/6] <value>")
1. r0b0t — GET /robots.txt -> Disallow /internal-notes/ ; GET /internal-notes/ -> "[1/6] r0b0t"
2. 1D0R — IDOR: GET /api/users/1 (any member JWT) -> bio "[2/6] 1D0R..."
3. J\/\/T — hidden JWT claim. Register -> token; payload note (JSON) = "[3/6] J\/\/T".
 CRITICAL: the value contains literal BACKSLASHES: J \ / \ / T (the \/\/ renders as
 a stylised "W" => "JWT"). The common reading "J//T" is WRONG and gets rejected.
4. 5Q1 — SQLi auth bypass: POST /api/staff-login {"username":"admin'--","password":"x"}
 -> {"secret":"[4/6] 5Q1"}
5. T0(T0U — TOCTOU race on /api/redeem (one-per-user coupon). ~40 concurrent redeems over-credit
 the purse (balance 3500); then GET /api/vault -> {"fragment":"[5/6] T0(T0U"}
6. P0LYF1LL — /static/polyfill.min.js is an obfuscated decoy whose final IIFE is a guarded XOR
 "lantern": it only runs when URL query param `shimdebug` matches, then console.log +
 writes #polyfill-debug. Verified in-browser by neutralising the guard `return`:
 output = "[6/6] P0LYF1LL". (The earlier P0LYF1LL was a FABRICATED XOR; this is the
 real lantern actually executing.)

## Correction history
- prior pass flag d4rk{...J//T...P0LYF1LL} was rejected. Fragment 6 value P0LYF1LL turned out
 correct (confirmed by executing the real lantern), but fragment 3 must keep its backslashes:
 J\/\/T, not J//T.
