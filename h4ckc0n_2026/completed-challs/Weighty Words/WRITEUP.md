# Weighty Words

**Category:** Forensics · **Points:** 500 · **Author:** paramveer504

> Old tongues call picture a thousand words, Verily this scroll hath few words, yet it groaneth like a cart of stones

**Flag:** `d4rk{1t5_n0t_r8b?}`

## Summary

A 5-page PDF weighs 122 MB. The weight is a fake table inside the embedded
font. Undoing a byte shift of 3 gives an xz stream, which unpacks to a FITS
astronomy file. The flag is drawn among the stars of the science frame, visible
only in one Bayer sub-channel once the quantised background is masked out.

## 1. The PDF

`paper.pdf` is a ReportLab PDF with 5 pages of mock-archaic text listing
forensic techniques and disclaiming each one (kerning, metadata, incremental
updates, ICC profiles, LSB, attachments, JavaScript...). All of that is noise,
as are the three "ciphers" in section VIII:

- `VGhlIHNjcmliZSBsYXVnaHMgYXQgdGhlZQ==` → `The scribe laughs at thee`
- `Qrw khuh, jrrg uhdghu` → ROT3 → `Not here, good reader`
- `6e6f7420686572652c206e6f7420796574` → `not here, not yet`

The object layout shows where the size is:

```
19 0 obj << /Length1 122383664 /Length 122400820 /Filter /FlateDecode >>
```

Object 19 is the `/FontFile2` of the embedded `IM_FELL_English_Roman` TrueType
font. Four stray bytes follow `%%EOF`: `urw3`.

## 2. The font

Inflating object 19 and reading the TrueType table directory:

```
GSUX offset 59844 length 122323820
OS/2, cmap, glyf, head, hhea, hmtx, loca, maxp, name, post (normal sizes)
```

`GSUX` is not a real table (a nod to `GSUB`). It starts:

```
00 3a 7d 5b 5d 03 03 07 ...
```

The xz magic is `fd 37 7a 58 5a 00 00 04`; every byte here is that plus 3. The
ROT3 cipher in the text hints at the shift, and the trailing `urw3` is `rot0`
under the same shift.

```python
d = open('gsux.bin','rb').read
open('g.xz','wb').write(d.translate(bytes((i-3) % 256 for i in range(256))))
```

`xz -d` gives a 614,520,000-byte file.

## 3. The FITS file

| HDU | Name | Contents |
|-----|------|----------|
| 0 | primary | `OBJECT = 'Lighthouse Nebula'`, `TELESCOP = 'd4rk-scope'` |
| 1 | `PREVIEW` | 1024×256 float32 image |
| 2 | `SCI` | 16512×9288 float32, `BAYERPAT = 'GRBG'` |
| 3 | `LOG` | table: debias ok, flatfield ok, stack ok, calibrate skipped |

Two decoys:

- `PREVIEW` renders `d4rk{n1c3_try_but_n0}`.
- `SCI` has `COMMENT ZDRya3tuMWMzX3RyeV9idXRfbjB9`, base64 for the same string.

## 4. The science frame

Viewed whole, `SCI` is featureless noise. Splitting it into the four 2×2 Bayer
positions:

- Position (0,0) has mean ≈ 1.77; the other three sit near 0.
- The other three contain only a few dozen distinct values each, with no
 outliers anywhere.
- Position (0,0) contains exactly 13 background levels, `(1.02 + 0.03k)^3` for
 k = 0..12, each about 2.9 million times, plus about 33,000 pixels that are on
 none of those levels.

Masking out the 13 levels leaves only the off-level pixels:

```python
m = np.memmap('g.out', '>f4', 'r', offset=1056960+2880, shape=(9288,16512))
c = np.asarray(m[0::2, 0::2])
u, inv, n = np.unique(c, return_inverse=True, return_counts=True)
rare = (n < 1000)[inv].reshape(c.shape)
```

The result is about 1,500 small star blobs (4–5 px square) and one line of
text at roughly x 6100–6430, y 3000–3035 of the half-resolution channel:

```
d4rk{1t5_n0t_r8b?}
```

The text is added at only +0.005 in the cube-root domain, well under the 0.03
level spacing, so it is invisible in any normal stretch of the image.

## Notes

- The other three channels and the star positions were checked for local
 statistical anomalies and found to be uniform random filler.
- Tools: `pdfinfo`, `binwalk`, `xz`, Python with numpy/scipy/Pillow.
