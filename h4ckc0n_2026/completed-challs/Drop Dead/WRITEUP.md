# Drop Dead — Forensics 100 (h4ckc0n 2026)

**FLAG:** `d4rk{f0r31gn_s1x?}`

**Final URL (answer):**
```
https://hljuqfqgsdycotnhdndt.supabase.co/storage/v1/object/public/image/Screenshot%20from%202026-11-09%2017-32-54.png
```
`sha256 == 9f2bce0edb56e82e2e5ecf5e9585f9fb19495c6767f1dd1920742986119ca0f8` ✓ (matches README).

## Steps
1. **JPG stego.** Description "a foreign six, travelers call it 6^2" → base **36**.
 `steghide extract -sf dead_drop.jpg -p 36` yields a huge base36 string.
2. **base36 → XZ → ext4.** `int(s,36).to_bytes` is an `.xz`; decompress → a 32 MiB ext4 image.
 `debugfs rdump` the whole tree.
3. **README** pins `sha256 of the final url`. The URL is hidden as 5 numbered fragments,
 each in a different esolang/stego channel, each with a decoy twin:
 - **Part 1** — `etc/krb5.keytab` (realm *D4RKC0DE.LOCAL*): key fields, concatenated by
 **ascending kvno**, form a single-cell Brainfuck program → `1:https://hljuqfqgsdycotnhdndt`.
 (The `BACKUP.LOCAL` keytab is Ook! and decodes to a fake host — decoy.)
 - **Part 2** — the Supabase domain `.supabase.co`.
 - **Part 3** — `usr/share/fonts/misc/vga8.fon` hidden string, **reversed** →
 `/storage/v1/object/public/`. (`term.fon` is **Deadfish** and gives the decoy
 `/storage/v1/object/sign/`.)
 - **Part 4** — `research/session_0427.nwb` looks like calcium-imaging HDF5, but the
 `calcium_frame/data` dataset is a **Piet** program (`codel_size=8` attribute, 18 Piet
 colours). Running it prints `4:image/` → bucket `image`.
 - **Part 5** — the **deleted** `prints/bracket.gcode`: each `G1 … E<int>.<frac>` line hides a
 byte in its fractional digits; the data channel reversed → `Screenshot%20from%202026-11-09%2017-32-54.png`.
4. Concatenate parts 1–5 and confirm the sha256. The `.bash_history` line
 `print('https://example.com/storage/v1/object/public/image/test.png')` is the template hint.

**Decoys:** backup keytab (Ook host), `tune.mid`, `old_bracket.gcode`, `photo.png`, `report.pdf`,
and the Deadfish `/sign/` path.
