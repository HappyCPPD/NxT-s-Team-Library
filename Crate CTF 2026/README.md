# CTF Writeups — crate-ctf session

Solved challenges, one folder each. Every folder has a `writeup.md` plus the related files.

| # | Challenge | Category | Flag |
|---|-----------|----------|------|
| 01 | [XML-kontroll 2](01-xmlkontroll2/writeup.md) | Web | `cratectf{varför_skriver_jag_mitt_lösenord_så_här?}` |
| 02 | [Hemglass speldosa](02-hemglass/writeup.md) | Misc / Audio | `cratectf{sm4aRRigt_med_glass}` |
| 03 | [tabadabort](03-tabadabort/writeup.md) | Web | `cratectf{ovanlig_http_metod}` |
| 04 | [identitetskris](04-identitetskris/writeup.md) | Web / Forensics | `cratectf{flera_sorters_filer}` |
| 05 | [Audio Forensics (file.mp3)](05-audio-forensics/writeup.md) | Forensics / Stego | `cratectf{kunde_inte_höra_den_komma}` |
| 06 | [OwlsAndDragons I](06-owlsanddragons-1/writeup.md) | Forensics / Stego | `cratectf{th4_AMaz1ng_hEdGehog}` (Part II WIP) |

## Techniques at a glance
- **01** — XML injection: CDATA breakout (`]]>`) to inject `<isadmin>true</isadmin>`.
- **02** — Recognising the Hemglass jingle; notes/durations from the SID 6581 reconstruction source.
- **03** — Undocumented `DELETE /api/users/me` (found via `OPTIONS`) + `GET /api/recovery/<id>`.
- **04** — Flag split across 5 file formats (CSS → PNG → JSON → PDF/TXT → MP3).
- **05** — ID3 clues → ZIP appended at EOF (AES) + password drawn in the spectrogram.
- **06** — Lossless PNG hiding `zTXt`-SVG → base64 PNG/7z + XOR-0x13 JPEG; 7z password in a PDF appended to an embedded PNG.

_Note: a separate "chef's recipe" color-swatch challenge was in progress and isn't written up here yet._
