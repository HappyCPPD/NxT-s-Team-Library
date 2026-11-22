# identitetskris ("identity crisis")

- **Category:** Web / Forensics / Multi-stage
- **Target:** `http://identitetskris.challs.crate.nu/`
- **Hint:** *"Part of the flag has been left on the server, the rest should be nearby."*
- **Flag:** `cratectf{flera_sorters_filer}` ("several kinds of files")

## Challenge
A decoy "Tomato World" site. The flag is split into **five pieces, each in a different file
FORMAT** — the "identity crisis" is that every fragment lives as a different file type, and each
one points to the next.

| Part | Format | Location | Content |
|------|--------|----------|---------|
| 1 | CSS comment | [`flag.css`](flag.css) (`.nothing{}` rule at the end) | `cratectf{` |
| 2 | PNG (handwritten) | [`flag.png`](flag.png) | `flera` |
| 3 | JSON structured data | [`flag.json`](flag.json) (object #2, `Part_3` field) | `_sort` |
| 4 | PDF / TXT ("printing") | [`flag.pdf`](flag.pdf) / [`flag_part4.txt`](flag_part4.txt) | `ers_f` |
| 5 | MP3 (spoken) | [`flag.mp3`](flag.mp3) | `iler}` |

## Walkthrough
1. `index.html` loads `flag.css`. At the bottom of the CSS, a `.nothing{}` rule comments
   *"Part 1 of the flag: `cratectf{`"* and references `/flag.png`.
2. **`flag.png`** shows handwritten "Part 2: **flera**" and footer text
   *"current format: image → next format: structured data"*.
3. **`flag.json`** (json-generator filler) hides `"Part_3": "_sort"` in object #2, plus
   *"next: the next fragment has been prepared for printing."*
4. **`flag.pdf`** / **`flag.txt`** both give *"Part 4: `ers_f`"* and
   *"next: listen carefully for the last part."*
5. **`flag.mp3`** is a spoken voice saying the final piece — **`iler}`** — completing the word
   **filer** ("files").

Assembled: `cratectf{` + `flera` + `_sort` + `ers_f` + `iler}`

## Flag
```
cratectf{flera_sorters_filer}
```
("flera sorters filer" = *several kinds of files* — the flag scattered across many file types.)

## Note
The final MP3 segment required actually listening — it's speech, not a text-in-spectrogram
(the spectrogram shows voice formants). Pieces 1–4 were all extracted programmatically.
