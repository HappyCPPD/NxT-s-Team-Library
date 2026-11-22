# RESULT — Shades of Truth (Forensics/stego, 100 pts)

slug: shades
folder: Shades of Truth
chall.png: 900x250 RGB; tEXt chunk Charset = " .:-=+*#%@"

## STATUS: SOLVED

## FLAG: d4rk{asc11_l0v3}

## MECHANISM (proven)

1. Hidden payload = low 2 bits of R and G, folded:
 M = (G % 4) * 4 + (R % 4) -> 16-level image
 B channel low bits are pure noise (uniform); R%4 in {0,1,2} (never 3).
 M is 0 everywhere except the payload band.

2. Payload band (native coords): rows 90..154, cols 10..729 -> crop 65 x 720.
 This crop is an EXACT 5x NEAREST upscale:
 - every 5 columns identical, every 5 rows identical (verified periodicity True)
 - the true hidden bitmap is 13 x 144 (M[::5, ::5]).
 So the payload is a 144x13 bitmap picture of TEXT (an "ASCII-art" style render),
 matching the hint "read between the lines" and the Charset ramp.

3. The rendered text is the flag enciphered with CAESAR +3 (letters only; digits,
 '_', '{', '}' unchanged). Decode = shift letters by -3.
 Anchor: rendered g4un{ -> d4rk{ (g->d, u->r, n->k, 4/{} unchanged)
 rendered d v f -> a s c

4. Glyph reading (connected-component segmentation of the 13x144 bitmap,
 17 components; printouts in shadesX_*.py output):
 g 4 u n { d v f 1 l _ o 0 y 3 }
 => rendered string: g4un{dvf1l_o0y3}
 Shift -3 -> d4rk{asc11_l0v3}

 Per-glyph verification highlights (see shadesX_pg3.py):
 - 'g','4','u','n','{','d','v','f','_','}' read unambiguously.
 - glyph at cols 70-75 has a left flag + stem + base serif -> '1' (digit)
 - glyph at cols 81-86 is the matching tall thin letter -> 'l'
 (shape-match: '1' score 0.497 vs 'l' 0.398 for cols70-75; cols81-86 '1' .426 / 'l' .415)
 - glyph A (cols 101-109) x-height, closed -> 'o' ('o' 0.627 best, vs 'u' 0.517)
 - glyph B (cols 110-119) cap-height closed oval -> '0' (digit, taller than A)
 - glyph C (cols 122-129) x-height TOP + 3-row DESCENDER (rows 5..12, baseline ~r10)
 -> a descender letter with converging diagonals -> 'y' (NOT 'x': x never descends)
 - glyph D (cols 129-136) top bar + right side + bottom bar -> '3'

5. Word check: rendered tail "o 0 y 3" -> shift -3 -> "l 0 v 3" = leet "love".
 This is the unique vowel/consonant-consistent reading (o->l, 0->0, y->v, 3->3).
 Rendered "oOx3" (as a raw visual read) would decode to nonsense "lLu3"; the second
 tail glyph is a digit-height '0' and the third has a descender, so '0'/'y' is correct.

## ARTIFACTS (all prefixed shadesX_, resumable)
- shadesX_native_crop.npy 65x720 native M payload crop
- shadesX_extract.py M-fold extraction
- shadesX_cc.py connected-component glyph segmentation
- shadesX_pg3.py font-calibrated per-glyph shape match (evidence table)
- shadesX_rd_L/R.png, shadesX_g_L/R.png, shadesX_mont5.png, shadesX_tailbig.png,
 shadesX_cmp2/3/4.png visual renders used to read glyphs

## CONFIDENCE / ALTERNATES
Primary (used above): d4rk{asc11_l0v3}

The only genuinely uncertain sub-decisions are (a) 'l' vs 'i' at rendered cols 81-86
(letter 'l' 0.415 vs digit '1' 0.426 — near tie), and (b) 'y' vs 'x' for glyph C
(shape-only match favours 'x' 0.508; vertical descender of 3 rows favours 'y').
Both alternatives give valid-looking flags:

 2nd: d4rk{ascii_l0v3} (if cols 70-75 is 'l' not '1')
 3rd: d4rk{asc1i_l0s3} (if glyph C is 'v' not 'y' -> 'l0s3' = "lose")

All three share the proven "d4rk{..._l0?3}" skeleton produced by the +3 Caesar.
The blocks in (a)/(b) are only 1-2 pixels tall at native resolution, which is the
resolution floor of this stego; the mechanism itself is exact and reproducible.
