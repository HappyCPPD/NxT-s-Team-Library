---
title: "Reverse Image Search"
ctf: "platypwnies 2026"
date: 2026-11-14
category: osint
difficulty: easy
points: n/a
flag_format: "PP{...}"
author: "NxT_CTFs"
flags:
 - "PP{1-h4cK-7h3r3f0r3-1-4M::_no7qscF2yR0}"
---

# Reverse Image Search

## Summary

A vertical street photo taken from the bottom of a cobbled stair lane in a medieval old town. The
task has **two** answers in one submission: the location (within 5 m) **and** the name of the person
portrayed on a piece of street art on the wall next to the spot.

The lane is **Lühike jalg ("Short Leg"), Tallinn Old Town, Estonia** — the stair street climbing
from Rataskaevu up to the Lühike jalg gate tower (white limestone tower, red pyramid roof). The
artwork is **Plan B's 2025 stencil** on the wall beside the lane, captioned *"Ma maalin. Järelikult
ma olen."* ("I paint. Therefore I am.") — a portrait of **René Descartes** holding a spray can, a
pun on *cogito ergo sum*.

Accepted submission: location `59.4363241, 24.7416037` (Lühike jalg 5) **+ name `Rene Descartes`**
(plain ASCII — see the pitfall: the accented `René` was rejected).

Flag: `PP{1-h4cK-7h3r3f0r3-1-4M::_no7qscF2yR0}`. Credit to operator **RCA(R)** on the artwork ID.

## Solution / Exploit

### Step 1 — Metadata gives nothing, so this is pure visual OSINT

```bash
exiftool reverseimagesearch.jpg | egrep -i 'gps|date|make|model'
```

The file is 2304×4096 with a synthetic EXIF date (`1970:01:01`) and no GPS. Deliberately scrubbed.

### Step 2 — Reverse image search to get the city

Yandex CBIR on the full frame returned tags **"tallinn old town"** / **"estonia"**, and
`cbir_page=sites` returned Commons `File:Lühike Jalg.jpg`, `visit-plus.com/.../tallinn-luhike-jalg.jpg`
and the Ukrainian Wikipedia article "Люхіке-ялг" — all the same view up the stair lane. That is
enough to fix the city: **Tallinn, Estonia**.

The frame itself is a good fingerprint:

- cobbled stair lane climbing between tall medieval walls;
- on the left, a downpipe completely covered in stickers;
- on the right, an ochre plastered wall with tag graffiti;
- overhead, two hanging shop signs, both black with a red-square logo;
- straight ahead, a white limestone tower with a red pyramid roof.

### Step 3 — Pin the exact address from the hanging signs

The two black signs read **"ROOMS"** and **"ART GALLERY TRUUS"**. Galerii Truus describes itself as
being in the "Lühikese jala maja" (the Lühike jalg house), so the camera is standing at the **bottom
of Lühike jalg, at Lühike jalg 5**, looking up toward the gate tower. That also matches the geometry:
the tower is dead ahead and slightly uphill.

This gives the coordinate to submit:

```
59.4363241, 24.7416037 # Lühike jalg 5, Tallinn
```

The challenge requires being within **5 metres**, so a street-level pin at the bottom of the lane is
what you want — not the tower at the top.

### Step 4 — Identify the artwork and the person

The photo's own wall (right-hand ochre wall) carries only tags, and the sticker-bombed downpipe has
no named portrait — both are decoys. The "cool street art on the wall next to where this photo was
taken" is the **Plan B** piece on the adjacent wall of the same lane:

- **Artist:** Plan B (Estonian street artist).
- **Year:** 2025.
- **Caption on the piece:** *"Ma maalin. Järelikult ma olen."* — Estonian for "I paint. Therefore I
 am.", a riff on Descartes' *cogito ergo sum*.
- **Subject:** **René Descartes**, depicted as a stencil portrait holding a spray can.

So the person portrayed is **René Descartes**.

### Step 5 — Submit location + name

Submit the pin and the name in the same form. Accepted: `59.4363241, 24.7416037` + `Rene Descartes`.

### Step 6 — Flag

```
PP{1-h4cK-7h3r3f0r3-1-4M::_no7qscF2yR0}
```

## Flag(s)

```
PP{1-h4cK-7h3r3f0r3-1-4M::_no7qscF2yR0}
```

## Notes / Pitfalls

- **The accented form was rejected.** The challenge text says "the name may include diacritics",
 which primes you to type `René Descartes`. The checker rejected that and accepted plain
 **`Rene Descartes`**. If the accented name fails, submit the ASCII spelling before you start
 questioning the location — the location was right the whole time.
- **The wall in the photo is not the wall with the art.** The obvious reading — "the graffiti in my
 own frame" — is wrong. The tags in-frame are anonymous; the portrait is on the neighbouring wall
 of the same lane. Don't burn time OCR-ing the tags (`AMO`/`KRO`/`MO`/`HIN…`) or the pole stickers
 (`KORS`, `GBJKY`, `ULTRA`, one helmet-face sticker): none of them name a person.
- **Google Street View has no coverage on Lühike jalg.** It snaps to Raekoja plats, so you cannot
 verify the lane in Street View — the Commons/visit-plus reference photos are what confirm it.
- The two "ROOMS" / "ART GALLERY TRUUS" signs are the single strongest locator in the frame; if you
 only glance at the tower you end up pinning the wrong end of the street (and failing the 5 m rule).
- The name "Lühike jalg" literally means "Short Leg" — searching the English translation wastes a
 query; search the Estonian.

## Artifacts

`images/` in this folder:

| file | what |
|---|---|
| `reverseimagesearch.jpg` | original 2304×4096 challenge photo |
| `ris_signs.png`, `ris_signs.jpg`, `ris_signs2.png` | the "ROOMS" / "ART GALLERY TRUUS" hanging signs |
| `ris_gallery.png`, `ris_gallery.jpg` | the gallery sign / lane view |
| `ris_pole.png`, `rise_pole.png`, `ris_polesticker.png` | the sticker-bombed downpipe |
| `ris_rightwall.png`, `rise_right_wall.png` | the ochre wall with tag graffiti |
| `ris_graf1.png`, `ris_graf2.png` | close crops of the wall tags |
| `ris_sig1.png`, `ris_sig2.png` | the stair lane / gate tower |
