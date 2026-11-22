# Crate CTF 2026 — Writeups

One folder per challenge, each with a `WRITEUP.md` plus the related files (source, images, archives).

| Challenge | Category | Flag |
|-----------|----------|------|
| [xmlkontroll2](xmlkontroll2/WRITEUP.md) | Web | `cratectf{varför_skriver_jag_mitt_lösenord_så_här?}` |
| [hemglass](hemglass/WRITEUP.md) | Misc / Audio | `cratectf{sm4aRRigt_med_glass}` |
| [tabadabort](tabadabort/WRITEUP.md) | Web | `cratectf{ovanlig_http_metod}` |
| [identitetskris](identitetskris/WRITEUP.md) | Web / Forensics | `cratectf{flera_sorters_filer}` |
| [audio-forensics](audio-forensics/WRITEUP.md) | Forensics / Stego | `cratectf{kunde_inte_höra_den_komma}` |
| [OwlsAndDragons-I](OwlsAndDragons-I/WRITEUP.md) | Forensics / Stego | `cratectf{th4_AMaz1ng_hEdGehog}` (Part II WIP) |

## Techniques at a glance
- **xmlkontroll2** — XML injection: CDATA breakout (`]]>`) to inject `<isadmin>true</isadmin>`.
- **hemglass** — Recognising the Hemglass jingle; notes/durations from the SID 6581 reconstruction source.
- **tabadabort** — Undocumented `DELETE /api/users/me` (found via `OPTIONS`) + `GET /api/recovery/<id>`.
- **identitetskris** — Flag split across 5 file formats (CSS → PNG → JSON → PDF/TXT → MP3).
- **audio-forensics** — ID3 clues → ZIP appended at EOF (AES) + password drawn in the spectrogram.
- **OwlsAndDragons-I** — Lossless PNG hiding `zTXt`-SVG → base64 PNG/7z + XOR-0x13 JPEG; 7z password in a PDF appended to an embedded PNG.
