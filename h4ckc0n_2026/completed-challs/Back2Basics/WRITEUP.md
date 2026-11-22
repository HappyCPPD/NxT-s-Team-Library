# Back2Basics

_TODO_

---

## Back2Basics (Web, 100) — SOLVED
Flag: d4rk{r0b0t_1D0R_J//T_5Q1_T0(T0U_P0LYF1LL}

Six foundational web primitives, each leaks one "[n/6] <VALUE>" label:
1. r0b0t — /robots.txt -> Disallow: /internal-notes/ -> page prints [1/6] r0b0t
2. 1D0R — IDOR GET /api/users/1 (admin bio) -> [2/6] 1D0R
3. J//T — JWT payload "note" claim in every token -> [3/6] J//T
4. 5Q1 — SQLi bypass POST /api/staff-login username: admin'-- -> [4/6] 5Q1
5. T0(T0U — TOCTOU race on /api/redeem (WELCOME100) -> balance>200 -> /api/vault -> [5/6] T0(T0U
6. P0LYF1LL — obfuscated /static/polyfill.min.js: base64 blob ^ key "w3bCh41n" -> [6/6] P0LYF1LL

Full detail + raw proof: RESULT-back2basics.md, back2basics_artifacts/back2basics_EVIDENCE.txt
