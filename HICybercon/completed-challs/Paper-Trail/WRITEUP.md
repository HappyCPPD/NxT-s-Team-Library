# Paper-Trail — planted layer isolated & *proven*; numeric payload still NOT decoded (hard negative)

**Category:** forensics (PDF) · **Artifact:** `extracted/chall.pdf` (516,033 B, PDF, 13 pages)
**Flag format** `hiCTF{}` · **Status:** PLANTED LAYER FOUND, PAYLOAD NOT DECODED.
No flag was recovered and **no `FLAG.txt` was written** (nothing is fabricated).

> ### ⚠ Read this first: the challenge is EASY (211 solves) — our model was wrong
> The platform shows **211 solves** and the boss calls it *easy*. So the payload decodes in **one
> obvious step** and the artifact is fine. The whole brute-force sweep below is therefore *negative
> evidence about our mental model*, not about the challenge. **Do not re-run the sweep.** See
> `HANDOFF.md` → "Strongest leads". The most promising technical lead is the author's own style in
> the **sibling challenge `Whispers-in-the-Margin`** (same event, same organiser, also document
> stego): the secret was hidden as **bit rows** — *"space = 0, tab = 1; read each row as a 12-bit
> value and take `chr(value)`"* — with the hint *"what appears empty might hold the key"*. Our
> "empty" carrier is the invisible text; 169 = 13² and there are 13 pages, so a 13-row × 13-bit (or
> per-TJ-line) bit-row reading deserves a proper, non-brute-force look.

## Challenge
> "The document passed its final review without raising any concerns. What was submitted
> appeared complete, and nothing seemed out of place. But the archived copy tells a different
> story. Some changes leave no visible trace."

## The planted layer (re-verified this pass, against a fresh Wayback original)
The PDF is the real JDFSL paper *"Forensic Analysis of Virtual Hard Drives"* (Tobin / Le-Khac /
Kechadi, 2017), re-saved with **Appligent AppendPDF Pro 6.3** (Producer: Prince 12.5).

* Original re-downloaded this pass: `curl -sL
 "https://web.archive.org/web/20231202062136if_/https://commons.erau.edu/cgi/viewcontent.cgi?article=1438&context=jdfsl"`
 → `/tmp/wb2.pdf` (500,136 B, 13 pp, `/Size` 176).
* Semantic object diff (content-hash of every object, streams by SHA-1 of decompressed bytes):
 the modified file has **exactly four** streams the original lacks — objects **(179,0)–(182,0)** —
 and **zero** streams removed or altered. `/Size` 183 vs 176 = the 4 streams + 3 rewritten
 structural objects (176 = StructTree kids, 177 = /Nums, 178 = a duplicate `/Info`), all benign.
* `pdftotext` byte-identical on all 13 pages → no *visible* text changed.
* `Tr` operators: **0** in the original, **4** in chall.
* Raw-file scan: single `%%EOF`, single `startxref`, no object present in the file but missing from
 the xref, no `hiCTF`/`CTF{` literal, no `%`-comment payload, no embedded files, XMP clean.
* **Every font is byte-identical to the original** (`/Widths`, `/Differences`, `/ToUnicode`,
 `/CharSet`, embedded FontFile3 for CMUSerif-Roman/Bold/Italic, Calibri, TimesNewRoman) → the
 font is not the channel.
* All dictionary strings (`/Alt`, `/ActualText`, `/Contents`, `/URI`, titles…) are benign paper text.
⇒ **The 169-integer kerning array is the entire payload.**

## The numeric payload
Four appended invisible overlay streams on pages index **2, 5, 8, 11** (step 3), each:
```
q BT /F1 1 Tf 3 Tr 1 0 0 1 8 8 Tm
[ A  B  C n1 n2 ... nk] TJ ← exactly S N S N S N then a run of bare numbers
... ET Q
```
`3 Tr` = invisible, 1 pt, corner (8,8), font `/F1 = LBCIAA+CMUSerif-Roman` (subset, 87 glyphs in
the CFF).

**Verified structure (this pass):**
* 20 TJ lines total, stream line-counts **6/6/4/4**; every line has the *identical* token pattern
 `S N S N S N` + run — the number of empty strings is always exactly 3 (no structural channel there).
* **169 integers**, min **−77**, max **254**, 122 distinct, **zero zeros**.
* Per-line run lengths `2,1,5,20,2,4 | 4,1,4,20,1,3 | 5,5,21,2 | 3,1,3,2`.
* Three "big" lines hold 61 of the values — objects 179 L3, 180 L3, 181 L2 — and **all 61 are
 positive** (`1..254`, uniform-ish); every other value is in `[−77, 80]` ("kerning-like", mean ≈ 0).
 Per-line means: normal lines ≈ 0, big lines ≈ 93 / 97 / 142.
* Whole-blob value histogram is **not** uniform and **not** a letter-code cluster: it peaks near
 `−10 … +60` and decays with a sparse tail out to 254. Byte-stream IoC ≈ 0.005.
* Values span 332 (−77…254) > 256 ⇒ the mapping is **not** a plain per-byte offset/XOR of ASCII;
 and 122 distinct values > ~95 printable ⇒ **not** a function of a printable alphabet either
 (so: noise-added, homophonic, or keyed).

## Attacks run — cumulative list (all NEGATIVE)
From earlier sessions (see history at the bottom) plus **this pass** (all new, all negative):

* **Full value-space sweeps**: global affine `(v·a+b) mod M` for every `a` over `M ∈ {2..199,
 254,255,256,331,332,333,400,512}` with a `hiCTF{` crib, on 12 groupings (flat, rev, runs, leads,
 A/B/C-only, first/last-run, runsum, linelen, runsrev) → only trivial `M=2,3` collisions.
* **Linear "scale" maps** (no modular wrap): `chr(32+round((v+77)·r)+off)`, r = 1…2.0 in 0.001 steps,
 off −120…120 → max leet-score outputs are still gibberish.
* **Bit/symbol packings**: every single bit plane (0–7 of `id/abs/p77`), sign, signed-sign
 (`v<0 ∨ v≥128`), parity, `≥128`, `>median`, `>mean`, plus all **pairs and triples** of 12 binary
 channels, incl. inverted and MSB/LSB; 2/3/4/5/6/7/8-bit **symbol packing**; bit-streams → **hex
 (4-bit)** and **base64 (6-bit)** re-packing → all negative.
* **Index/metadata keys**: `v op f(index)` for global/line/stream indices, `f = a·i`, and
 `v op {page,obj,obj−179,line,line+1,position-in-line,line-length}` → negative.
* **Channels vs. the document**: XOR/add/sub against the *visible page text* (all alignments, per
 page and whole doc, raw and printable-filtered), against the page's *visible TJ kerning numbers*,
 against the font `/Widths`, against the `/Differences` codes, against the challenge description
 text, the title, `paper-trail`, `hiCTF`, `JDFSL`, `HICyberCon`, the DOI, the URIs → negative.
* **Deterministic keystreams**: RC4, repeating-key XOR/ADD/SUB, and PRNG keystreams seeded from the
 `/ID` pair (hex + ASCII + MD5), the CreationDate, titles — for PCG/MT `randrange`, `getrandbits`,
 SHA-256-CTR, MD5-repeated → negative. 2-byte repeating-key XOR (65 536 keys) → negative.
* **Crib-drag** (flag = `hiCTF{`-prefixed window under a repeating key, period 1–8, every offset,
 XOR/ADD/SUB ×2) scored by leet-similarity → no candidate above ~0.85.
* **Repetition / periodicity**: `n[i] op n[i+k]` concentration for k = 1…84 (SUB/ADD/XOR) → flat
 (max top-share 0.052). No repeated-key structure (IoC ≈ 0.005).
* **Subsets**: negatives-only, `v<−10/<−30`, positives, `|v|>60/>127`, `|v|<10`, big-runs-only,
 small-runs-only, plus all of the above transforms → negative.
* **Strides**: every subsample `flat[o::k]`, k = 2…25, o = 0…k−1, under `mod 256/95/94/26/36/62/128`
 and cumulative → no `hiCTF`.
* **Big-integer digit codes**: values → digits/base-`B` (`B ∈ {2,3,4,5,6,7,8,9,16,32,64,100,128,256}`)
 via `v`, `|v|`, `v+77`, `v+128`, and via *decimal/hex/octal/binary string concatenation*, decoded
 as a big int both endians → negative. Also digit-count / leading-digit / last-digit extractions.
* **Grouping/aggregation**: partition flat & run streams into consecutive groups of size 2…25 with
 sum/mean/xor/min/max/first/last (with every offset), map `mod 256/95/94/26/36/62/128/100`; plus
 per-line "two chars per line" (feature over leads × feature over run) → no `hiCTF`; top leet-score
 strings are random letter soup.
* **Orderings**: all 24 stream permutations × line-reversal × value-reversal (96 variants) under
 identity/mod/abs/offset/XOR/cumulative → negative. Line-reversal and column-wise reads → negative.
* **Ciphers-as-text**: sign×case alphabets (`−n`→lower, `+n`→upper, etc.), `|v| mod 26`, absmod26,
 printable-mod maps in original and reversed order → negative.
* **Visual**: 13×13 grayscale renders (row-major, column-major, rot90, cumsum) — noise; 20-row
 bitmaps of raw values, `v+77`, `mod 256`, and per-line cumulative positions — noise; value/index
 line plots; 2-D `(x,y)` pair plots of the big-run and full streams — random scatter.

## Why it does not fall (assessment)
The payload is *high-entropy per value*, has **no repeating-key structure**, is **not** a per-value
function of a printable alphabet, and is **not** reproducible from any document-derived material
(`/ID`, dates, titles, visible text, font metrics). Its histogram is odd (peak near 0, tail to 254,
span 332 > 256) which argues the channel is *noise-added / homophonic* rather than a byte cipher.

Most likely, in order:
1. **Author-held key/seed not present in the file.** The four streams are genuine (proven) but the
 transform needs a secret external to the artifact.
2. **A non-value channel that is quantised, not byte-wise** — e.g. the *big lines'* 61 all-positive
 values are real ciphertext and the 108 small values are their keystream (tested: XOR/ADD/SUB, all
 alignments — negative), or the message lives in a *length/position* statistic (tested broadly).
3. The challenge is **underspecified / partly broken** — this event has at least one other flagged
 case where "the grid source is not shipped" (`Just-Give-Me-The-Flag-Man`), so an unresolvable
 key is plausible.

## Best remaining leads (single highest-value first)
1. **Ask the organiser / find the author's encoder.** Details below strongly suggest a *purpose-built
 generator*; even one line of its source would resolve this. (HI Cyber Con 2026 is run by **Hidden
 Investigations** — `hiddeninvestigations.net`, blog + Discord + `@hisecuritylab`.)
2. **Compare the *rendered kerning* of the four overlay streams against the *visible* kerning of the
 same page** with the classic "Art of Kerning" detector (measure each glyph position vs. the
 position predicted by the font metrics, read the *deviation* stream). The boilerplate
 (`3 Tr` + `1 0 0 1 8 8 Tm` + CMU Serif Roman) is exactly that technique's shape — but the glyph
 strings here are empty, so a decoder that *re-inserts* the correct glyphs may be needed.
3. **Flag-style crib.** Every other HICybercon flag is a *leet sentence naming its own technique*
 (`hiCTF{c0b0l_p4ck3d_d3c1mal_...}`, `hiCTF{b34m_byt3c0d3_...}`, `hiCTF{m4th_c0ntr0l_fl0w_...}`).
 Paper-Trail's flag therefore almost certainly contains a leet phrase about kerning / invisible
 text / `n0_v1s1bl3_tr4c3`. That is a *strong* crib — but a *global* crib search over all the
 transforms above still failed, which is itself evidence for (1).

## Provenance of this file
Earlier passes (this directory): the planted layer was found and the "Art of Kerning"-style
boilerplate first isolated; a later pass obtained the Wayback original and proved the plant. This
pass re-proved it independently against a fresh original, examined the fonts/non-stream objects, and
added the sweep families listed above (all negative). Scratch tooling for this pass lives in
`/tmp/` (`aff2.py`, `bitmega.py`, `period.py`, `cribdrag.py`, `stride.py`, `bigint.py`, `filt.py`,
`hist.py`, …) and prior tooling in `extracted/`.

---

# Pass 2 (2026-11-01) — sibling-model hypotheses A–D tested: **HARD NEGATIVE (again)**

**Goal of this pass:** apply the *technique shape* of the organiser's solved sibling
(`../completed-challs/Whispers-in-the-Margin`: *whitespace bit rows → `chr(int(row,2))` → a STRING,
then that string was USED as a steghide passphrase*) to the 169-integer payload, per four bounded
hypotheses (A two-class bit rows, B header-per-array, C widths/totals, D passphrase reuse).
**Result: no reading of any bounded hypothesis yields readable text.** No flag;
no `FLAG.txt` written; nothing fabricated; nothing submitted.

## 0. Payload re-confirmed independently (13 s, cheap)
Re-downloaded the genuine original (`/tmp/wb3.pdf`, 500,136 B) and hashed every stream
(decompressed). Confirms the prior pass exactly:
* streams only in `chall.pdf`: **exactly the four overlays `(179,0)=295 B`, `(180,0)=294 B`,
 `(181,0)=256 B`, `(182,0)=165 B`**;
* streams only in the original: **none**;
* pages whose concatenated `/Contents` hash differs: **only indices 2, 5, 8, 11** — and that is
 solely because those pages' `/Contents` array *gains the new overlay*, not because the page body
 changed. All other 9 pages hash-identical.
⇒ the 169 integers really are the whole payload. (Script: `x22_diff.py`.)

## 1. Hypothesis A — two-class clustering → bit rows ❌ NEGATIVE
Class rules tried: `v>0`; `v<0`; `v&1`; `|v|>median(30)`, `>mean(46.8)`, `>64`, `>80`, `>100`,
`>128`; `v%3==1/2`; `v>=0`; `v[i]>v[i-1]`; `v[i]>v[i+1]`.
Row definitions: each TJ array (20 rows); each page's whole stream (4 rows); each run (20 rows).
Bit orders: MSB-first and LSB-first; both polarities; `chr(value+offset)` for offset ∈
{−100…+96} and value packed at widths 5–20; plus whole-stream packing into bytes at every 8-bit
rotation. Scored both by literal `hiCTF` and by an **English letter-frequency + common-word
scorer** (to catch anything a leet-score heuristic would miss). Scripts `x3_A.py`, `x4_bits.py`,
`x15_rows.py`, `x19_arr8.py`.
**Outcome:** the only "readable" rows are all-zero rows (= the same char repeated); no rule/width/
order/offset combination produces English or `hiCTF`. Top English scores ≈ 8–10 are chance-level
and the strings are visibly letter soup (`t(t. EgH. ….`T.(.$`-style).

## 2. Hypothesis B — the 3 leading numbers per array as a HEADER ❌ NEGATIVE (no structure)
Tabulated `(a,b,c)` vs run length `L` for all 20 arrays. **None** of `a`, `b`, `c` (nor `a+b+c`,
`|a|`, `|c|`, `a·b`, …) is monotone with or equal to `L`; the three "big" arrays have
`(24,24,174) L=20`, `(35,−18,21) L=20`, `(−24,−2,250) L=21` — no consistent
`(start, length, base)` relation. Tried `char=f(lead)` for all four lead-columns × mod maps
(26/36/52/62/95/256, abs, +128), and per-array cyclic-3-lead key over the run
(`(run[i] op lead[i%3])`, op ∈ XOR/ADD/SUB, shifts 0/1/2) → nothing. Script `x10_key.py`, `x6_score.py`.

## 3. Hypothesis C — widths / per-line totals ❌ NEGATIVE
Projections tried (each × {id, |v|, v+77, v+128, −v} × mod {26,36,52,62,94,95,128,256} +base):
per-array **sum, sum|v|, mean, min, max, #neg, #pos, length, run-length**; per-line first/last;
whole-stream sums. Ranked by the English scorer — best candidates are chance-level
(`lead2/p77/mod36+97` scores highest at 7.6 and is still letter soup). Scripts `x6_score.py`,
`x21_final.py`.

## 4. Hypothesis D — reuse any decoded string as a KEY ⛔ NOT APPLICABLE
No hypothesis produced a *string*, so there is no passphrase to try against `steghide` / `7z` /
`qpdf --password` / a Vigenère/XOR key. (Also: the container has no second artifact, no embedded
files, no appended data, and the PDF is unencrypted — so even a recovered passphrase would have no
lock to open *inside this artifact*.)

## 5. Additional families added this pass (all NEGATIVE — beyond the prior list)
* **Big-int digit codes over a much wider base range** (base = `maxdigit+1` and `+2` for
 digits ∈ {v, v+77}, both endians) → no `hiCTF`. (`x12_mega.py`)
* **Base-B digit packing** for B ∈ {3,4,5,6,7,9,10,11,13}, digits `= v mod B` and `(v+77) mod B`,
 MSB/LSB → no `hiCTF`. (`x14_base.py`)
* **base64 directly from `v mod 64`** (std + URL alphabets, offsets 0/64/77/128) → no `hiCTF`;
 likewise base32 from `v mod 32`. (`x16_misc.py`)
* **RLE-to-bits**: each number `v` expanded to `|v|` copies of its sign-class bit, whole stream
 packed to bytes (both polarities, both bit orders) → 0–2 printable bytes only; noise. (`x18_rlebits.py`)
* **Bit-length / popcount / digit-count features** of `|v|` as base-8/9/10/16 digits → no `hiCTF`.
* **Nibble packing** (`(v_i&15)<<4 | v_{i+1}&15`, both orders, from v / |v| / v+77) → no `hiCTF`.
* **Lag combinations** `v[i] op v[i+k]` for k = 1…39, op ∈ add/sub/xor, × 6 mod-maps → no `hiCTF`. (`x24_lag.py`)
* **Column-major (ragged) read** of the 20 arrays; **rank-order permutation** of the flat stream. (`x21_final.py`)
* **Rank / Lehmer-code permutations per array** (the permutation-within-array channel) interpreted
 as base-B integers for B ∈ {2…256} → no `hiCTF`. (`x23_perm.py`)
* **Compression** (zlib / raw-deflate / bz2 / lzma) of `(v&0xff)`, `v+77`, `|v|`, `v+128`, `255−v`
 byte streams → nothing decompresses. (`x12_mega.py`)
* **Printables in original order** for offsets {0,32,64,77,128} → inspected by eye, all gibberish.
* **Re-verified the font is not the channel**: `/F1 = LBCIAA+CMUSerif-Roman`, `/Differences` is a
 plain ASCII-identity subset (32 `/space` … 177), `/ToUnicode` codespace `<20>–<b1>`; the overlays'
 own `/F1` on page 2 is the same font. No custom code→glyph substitution to exploit. (`x5_font.py`,
 `x7_font2.py`)
* **Whole-file scans** for hidden literals / hex / base64 / XMP / odd dict keys: the only hex-looking
 32-char strings are the two `/ID` values (`e3b51a3ba231502d79c55593eb522037`,
 `6749db1175e3e659a640695dcc830c82`); everything else is standard paper metadata. (`x17_scan.py`)

## 6. Assessment (unchanged, now with stronger evidence)
The payload is a **high-entropy, non-repeating** integer sequence with **no per-value function of a
printable alphabet**, **no repeating-key structure** (IoC ≈ 0.005), and **no two-class / bit-row
reading** that yields text. Every bounded, artifact-internal decoding of the modelled
(sibling-style) family is negative. This is consistent with the prior pass's conclusion: the
transform most likely needs a **key/seed or generator parameter not present in the artifact**, or a
decode step the challenge hint (not shipped) would name. Recommended next action is unchanged:
**obtain the organiser's hint or the author's encoder** (HI CyberCon 2026, Hidden Investigations —
`ctf.hiddeninvestigations.net`; CTFd hint per-challenge). Public writeup searches (GitHub, CTF Base,
CTFtime event 3460 — *no tasks archived*) returned nothing for this challenge.

## 7. Reproducible tooling added this pass (all in this directory)
`x1_dump.py` (raw payload), `x2_raw.py` (raw stream text), `x3_A.py` … `x24_lag.py`,
`x5_font.py`/`x7_font2.py` (font), `x9_struct.py` (structural objects), `x11_render.py` (13×13
renders), `x20_hist.py` (distribution), `x22_diff.py` (independent stream diff vs fresh original).
**No transform above is worth re-running.**

## Pass 2026-11-01 (fresh re-verification) — still unsolved
* Re-verified from raw bytes: overlay strings are truly empty; no junk between objects, no
 whitespace stego outside streams, xref clean (only obj 0 free), ZIP clean (one LFH/CDH/EOCD).
* Literal-level diff of every dict/array value vs Wayback original: only number formatting
 (288 vs 288.0) and the new overlay /Contents refs. Overlays are the ONLY payload.
* /ID changed: original `[ED363C44…FF7F][1E3B3C44…5C7F]` vs chall `[e3b51a3b…][6749db11…]`.
* Split: 99 "short" values look uniform on -77..80 (likely decoy kerning); the three long runs
 from their 3rd value total exactly 64 bytes (21+21+22).
* Negative this pass: crib-difference search (all strides, mod 256), cursor-walk over page
 text (raw/layout/plain), pairwise + 3-way XOR/add/sub of long runs with shifts,
 AES-ECB/CBC, RC4, XOR of the 64-byte blob (all 6 orderings) with both /ID pairs, XMP UUIDs,
 md5/sha256 of themed words.

## Pass 2026-11-01 #2 (restart from zero) — still unsolved
* ZIP deflate stream: no trailing data, CRC matches, decodes byte-exact to chall.pdf.
* No duplicate object numbers, no /Length mismatches.
* Negative: ASCII-code digits in concatenated decimal string; header (a,b) as affine key params
 for the long runs; short numbers (own page / all / each page) as XOR/add/sub keystream for
 long runs at every offset; full affine (α,β mod 256) sweep × 24 stream orders × slices
 {flat,hdr,run,short,long,gap-triples,line totals} × {id,neg,cumsum,diff,rev} searching "CTF";
 long-run bytes as indices into page content-stream literals / PyMuPDF text (0/1-based).
* Visual: per-TJ row plot shows long runs are monotonic one-direction cursor sweeps, short
 lines are jitter around 0. No picture.

## Pass 2026-11-01 #3 ("CONTINUE") — still unsolved, new negatives only
* Re-inflated objects 179–182 straight from the raw PDF bytes (zlib): strings really are ``;
 178 is the new `/Info` (qpdf/pikepdf-style serialisation → overlays were added with pikepdf/qpdf).
* Cursor positions of the 60 empty strings (per-stream cumulative kerning, which carries across TJ
 arrays inside one BT) → `chr(pos mod 256)` / `chr(-pos mod 256)` → gibberish.
* Big-run bytes (61/64-byte selections) bit-packed as 21/24/25-wide grids (QR v1 idea) → no finder
 patterns, noise.
* 64-byte blob XOR/ADD/SUB with md5/sha1/sha256/sha384/sha512 of the Wayback original, chall.pdf and
 the zip, plus the original and chall `/ID`s, all 6 run orders → negative.
* Python `random.seed(s)` for s < 1e6 with randint over 11 ranges reproducing the first three
 values: 2 hits, both chance (4th value mismatches).
* Cursor-walk (±, start 0/end) and absolute indexing of the payload into each overlay page's own
 glyph-byte sequence (from its original content stream, via pikepdf) → gibberish.
* Pairwise `f(v[i], v[i+k])`, k=1..7, stride 1/2, f ∈ {add, sub, rsub, xor, mul, |a|+|b|, −sum}
 + every offset −128..128 mod 256, over 24 stream orders + leads-only + runs-only → no `iCTF`/`hiCT`.
* ZIP re-checked: only a standard NTFS-time extra field, no comment, no trailing data.
No flag. No FLAG.txt written.

# ✅ SOLVED (2026-11-01, pass #3): `hiCTF{n3w_ar34_fOr_hid!ng_d4t4_n4m3d_TJ}`
**Mechanism:** AES-128-CBC. **Key = trailer `/ID[0]`** (`e3b51a3ba231502d79c55593eb522037`),
**IV = `/ID[1]`** (`6749db1175e3e659a640695dcc830c82`). Both /ID elements were changed from the
archived original. qpdf normally keeps `/ID[0]`, so the author set them deliberately.
**Ciphertext** = the three long TJ arrays' numbers from the 3rd number onward (the 64 values in
1..254), concatenated in stream order 179 → 180 → 181 (21+21+22 = 64 bytes = 4 AES blocks).
The short kerning values (−77..80) are decoys.
Plaintext: `"CTF1" | u16 BE length (0x0028 = 40) | flag (40 B) | 8 B tag | PKCS#7 pad (10×0x0a)`.
The length field matches the flag exactly and the padding is valid, which confirms the decryption.
(The 8-byte tag `908a1a000ad4b36c` is not CRC32 of the flag. Unverified, and not needed.)
Reproduce: `python3 solve.py`. The earlier "AES with /ID" negative was a mis-test, probably the
wrong byte selection or key/IV assignment.
