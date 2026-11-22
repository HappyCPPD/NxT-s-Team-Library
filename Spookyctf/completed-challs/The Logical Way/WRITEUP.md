# The Logical Way — crypto (677 pts) — SOLVED

**Flag:** `spooky{vtosh_katur_nirak}`

> "A Vulcan has left their final message to the world before dying. They had spent
> centuries thinking of nothing but logic. Can you uncover their final message?"
> Format: `spooky{hello_world}` · Task: `My_Message_to_you.7z`

---

## 1. Crack the 7z

`My_Message_to_you.7z` is 7zAES over an LZMA2 stream, containing a single
`My Message to you.zip`. The archive headers are not encrypted (filenames are
visible), only the data — so the password must be cracked.

```bash
7z2hashcat My_Message_to_you.7z > hash.txt # (LZMA2-aware build)
hashcat -m 11600 -a 0 hash.txt rockyou.txt
```

Password = **`LOGIC`** (fittingly).

> ⚠️ **Gotcha — hashcat false positive.** hashcat mode 11600's LZMA2 ("type 2")
> kernel only partially verifies, so it happily reports wrong passwords. An earlier
> run surfaced `LOALOA93`, which *fails* real extraction. Always confirm a 7z crack
> by actually decrypting:
> ```python
> import py7zr
> py7zr.SevenZipFile('My_Message_to_you.7z', 'r', password='LOGIC').extractall('out')
> ```
> (The `7z`/`py7zr` CLIs can also mis-report "data error" on valid passwords due to
> version quirks — verify with a manual AES-CBC + LZMA2 decrypt + CRC32 check if unsure.)

## 2. The inner payload

`My Message to you.zip` → `LOGIC.pdf`: two pages of **Vulcan calligraphy** — 177
ornate glyphs. Each glyph is a separate image XObject drawn via the content stream.

Extraction (PyMuPDF):
- Walk each page's content stream, tracking the `cm` matrix, and record every
 `/Img Do` draw in **stream order** (= reading order) with its (x, y) and XObject.
- Cluster glyphs by their **smask pixel hash** → **21 distinct symbols**.
- Keep the stream order (within-row left-to-right); do NOT re-sort purely by x.

This yields a 177-char monoalphabetic ciphertext.

## 3. Solve the substitution

Hill-climb with **real English quadgram statistics** (practicalcryptography's
`english_quadgrams.txt`).

> ⚠️ The quadgram file keys are UPPERCASE — lowercase them (or uppercase your
> candidate) or every lookup hits the floor and scoring is flat (no gradient).

Recovered key:
```
A=t B=h C=o D=s E=e F=w G=d H=n I=f J=l K=p
L=r M=i N=c O=v P=u Q=a R=g S=k T=y U=m
```

Decoded message:

> *those who do not follow the principles of vulcan logic will fail* `vtosh katur nirak`
> *do not pity those who do not follow logic help them see reason*
> **turn the vulcan into english and wrap it with underscores to see reason**

## 4. Follow the instruction (the key insight)

The decoded text is **a hint, not the flag**. The last line says exactly what to do.

- The glyph **x-spacing encodes word boundaries** (larger gaps between glyphs = spaces).
- The message is mostly English words written in Vulcan script, *except* one genuine
 Vulcan-language phrase: **`vtosh katur nirak`** (`v'tosh ka'tur` = "Vulcan without
 logic", from Star Trek: Enterprise, plus `nirak`).
- "Turn the vulcan into english" = transliterate that phrase (script → Latin letters);
 "wrap it with underscores" = join the words with `_`.

→ **`spooky{vtosh_katur_nirak}`** ✅

## Lessons
- Verify 7z cracks by real extraction — mode 11600 gives false positives.
- Use real quadgrams (lowercased keys) for monoalphabetic solving, not dictionary stats.
- When a decode produces a coherent instruction, **follow it literally** — and check
 character/glyph *spacing* for hidden word boundaries.
