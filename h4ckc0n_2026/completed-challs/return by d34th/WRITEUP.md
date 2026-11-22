# return by d34th

## SOLVED — `d4rk{r3turn_0f_r3m_40}`

Rev, PE32+ (`parcel_delivery.exe`, MinGW-w64 g++ 16.1.0, **DWARF symbols intact**).

`./parcel_delivery <TRACKING_ID>`:
- **TRACKING_ID** must equal the hardcoded `VALID_TRACKING` = `woah_a_rezero_mystery`
 (`.rdata` 0x140006741) — the invoice tracking ID from "Love is a secret key".
- Then it prompts `Recovery code>` and runs `check_lattice` on a 16-char string of
 digits `'0'..'4'`:
 - 4 cells are pinned by `sudoku[i] ^ DEATH_KEY` (not-ed); `DEATH_KEY =
 RE_ZERO_FACTS.size = 40 = 0x28` (the table holds 40 Re:Zero trivia strings).
 `sudoku = d7 d7 d6 d7 d7 d7 d7 d7 d7 d3 d7 d4 d7 d7 d7 d3`
 ⇒ forced `{2:'1', 9:'4', 11:'3', 15:'4'}`.
 - Every row and column must pass `verify_line`: sum==10, product==24, sum-of-squares==30
 ⇒ each line is a permutation of `{1,2,3,4}` (4x4 Latin square).
 - Unique solution: **`4312324114232134`**.
- On success it prints `FLAG: d4rk{` + `ENCRYPTED_INNER[i] ^ input[i]` + `}`.
 `ENCRYPTED_INNER = 46 00 45 47 41 5c 6b 01 57 6b 40 00 5f 6e 07 04`.

Proof (Wine, exit 0):
```
$ printf '4312324114232134\n' | wine parcel_delivery.exe woah_a_rezero_mystery
[+] Tracking verified: woah_a_rezero_mystery
Recovery code>
[★] The lattice glows. The memories return...
FLAG: d4rk{r3turn_0f_r3m_40}
```

Artifacts: `RESULT-returnbyd34th.md`, `solve_lattice.py`, `disasm.txt`, `wine_run.txt`.
