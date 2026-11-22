# Paper Trail — payload characterised, encoding NOT yet cracked (2026-10-31, late)

## THE PAYLOAD (confirmed by me, pikepdf)
The plant is **4 appended invisible-text overlay streams**, objects **178, 179, 180, 181**
(pages 2, 5, 8, 11 zero-indexed -> /Contents arrays e.g. page2 = [53, 179]).
Each stream is:
```
q
BT
/F1 1 Tf
3 Tr <- render mode 3 = invisible
1 0 0 1 8 8 Tm
[ a  b  c d e f ...] TJ
... <- several TJ arrays
ET
Q
```
- **Every `` group is EMPTY** — 60 of them, all `b''`. There are **no hidden control /
 zero-width bytes anywhere** in the overlays (`odd bytes present: []`). So the usual
 "invisible characters" carrier is NOT used here.
- The ONLY payload is the **integers: 169 total** (per object 52 + 51 + 45 + 21),
 min **-77**, max **254**, **no zeros**.
- The arrays read `[ a  b  c <run…>]` — every array has exactly **3 ``** then a
 variable run. 20 arrays, lengths:
 `5,4,8,23,5,7, 7,4,7,23,4,6, 8,8,24,5, 6,4,6,5`.
- Tell-tale: real page kerning in this PDF is fractional (e.g. `-18688.6`, `-13841.6`),
 but the overlay numbers are all INTEGERS -> they are data, not real kerning.

## RULED OUT (spent real effort — do not repeat)
- byte `x & 0xff`, `abs(x)`, `-x`, `x+offset` **for all offsets 0..255**
- single-byte **XOR for all keys 0..255** (also with positional keys `^ i ^ k`, `+ i + k`)
- **cumsum**, cumsum of abs, diff, reverse — plain and with all offsets/keys
- 13x13 **reorderings** (row-major, column-major, transpose, snake) x all offsets
- **bit-packing** from sign, `abs>64`, `abs>100`, parity (`x&1`), `x&2`, each MSB-first,
 LSB-first and reversed
- per-array **sign-bits as a binary number -> chr**, and per-array count / first / last /
 sum / xor -> chr
- **mod-26 / mod-36** alphabet mappings (base 0 and 1)
- rendered the 169 values as a **13x13 bitmap** (grey + several thresholds): it is a
 dithered/checkerboard pattern, NOT legible text — (saved /tmp/pt_gray.png etc.)
- indexing into the **page's own visible text** (pypdf) -> gibberish
- 16-bit big-endian pairings -> nothing
- The ZIP container (no comment / trailing data), and a fresh Wayback diff (exactly these
 4 streams are new; nothing else altered or removed).

## BEST REMAINING HYPOTHESES (untried / under-tried)
1. **Glyph/width table of /F1.** The numbers may be glyph codes or advance widths into a
 subset font. Dump `/F1` (`/Widths`, `/FirstChar`, `/Differences`, ToUnicode) and see if
 the 169 values map onto it; a custom `/Differences` array could BE the substitution.
2. **The 3 leading ``-numbers per array as a header.** Each array = `(h1)(h2)(h3) run`.
 Maybe h1/h2/h3 are (row, col, len) and the run is that row's data — test reading each
 array's run as a row of a grid whose geometry comes from the header.
3. **Advance/position reconstruction.** Treat the numbers as *kerning deltas* and
 accumulate them into X positions of the invisible glyphs; the *position sequence*
 (not the values) may be the payload (e.g. positions -> indices into the visible text,
 or a barcode of widths).
4. **Relative to the original.** Diff the overlay numbers against the ORIGINAL page's own
 kerning sequence (Wayback copy ~/tmp/wb2.pdf or re-download) — the plant may encode the
 flag as *differences* from the natural kerning.
5. The sibling challenge (`Whispers in the Margin`) used **bit rows in whitespace**
 ("space=0, tab=1, read each row as a value, chr"). Our analogue may be *bit rows made
 of the numbers' signs* laid out per **line of the page** rather than per TJ array.

## Practical notes
- `pikepdf` and `pypdf` are available to the system `python3` (NOT in the agent sandbox —
 run extraction via `terminal` with `python3`, or write a file and run it).
- Foreground `terminal` calls cap at 180 s; use `background=true` + `notify_on_complete`.
- Flag format `hiCTF{}`. Do NOT submit anywhere.

---

## CORRECTION + NEW FACTS (delegated pass, 2026-11-01) — read before working

1. **"178 is an orphan" is imprecise.** Object **178 has NO stream at all** — it is purely a metadata
 dictionary (`/Appligent`, `/Author`, `/Title`). So there are only **THREE real overlay streams:
 179, 180, 181** (not four). Correct this in any earlier reasoning.
2. **Page mapping pinned with pikepdf** (not just "pages 3/6/9"):
 - page index **2** -> `/Contents [53, 179]`
 - page index **5** -> `/Contents [62, 180]`
 - page index **8** -> `/Contents [73, 181]`
 All three pages: MediaBox `[0 0 612 792]` = **Letter portrait, Rotate 0**.
3. **All three overlays share the SAME text matrix** `1 0 0 1 8 8 Tm` => cursor starts at **(8,8)**,
 i.e. 8 pt from the bottom-left corner of the page, in 8-pt units. Same origin for all three.
4. **Raw TJ arrays dumped in full.** Each array = three numbers between empty strings, then a long run:
 - 179's long run: `174 4 89 136 22 76 68 138 142 86 12 82 146 218 127 23 34 169 201 1 142`
 (all large positives)
 - 180's long run: mixed small values
 - 181's long run: `250 135 239 169 254 8 176 235 116 67 59 12 130 216 181 215 244 213 176 33 57 246`
 (near-uniform HIGH range)
 The three clearly different value ranges => **three different encodings, or three passes of ONE image.**

## ★ THE UNTRIED MOVE (this is almost certainly the 3-minute intended solve)
The **positioning/kerning reconstruction was never executed.** No absolute-x accumulation, no
page-coordinate scatter, no path join, no overlay-on-page render. Do it:

```
x = 8.0 # Tm origin x, pt
for each TJ number n: # n is in 1/1000 em
 x -= n/1000 * fontsize # NOTE: in PDF a NEGATIVE TJ number advances the cursor RIGHT
 # (sign convention is the classic trap - verify empirically)
 record (x, y)
```
- `y` from the Tm; all three overlays share `(8,8)`, so **render all three onto ONE 612x792 canvas**
 (matplotlib, `invert_yaxis` for PDF coordinates, `s=1`, and also join consecutive points as a path).
- Three streams, same origin, complementary value ranges = **one picture drawn in three passes.**
- Also try: cumulative-x as a 1-D timeline; and (array index, position index) mapped to a 2-D bitmap.

## Still not run (cheap, do them too)
`mutool draw -F txt`, `pdftotext -layout`, `pdftohtml -xml`, pdftoppm at high DPI with all OCGs on,
annotation/AcroForm dumps.
