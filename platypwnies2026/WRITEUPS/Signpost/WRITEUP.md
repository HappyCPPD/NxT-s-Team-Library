---
title: "Signpost"
ctf: "platypwnies 2026"
date: 2026-11-14
category: osint
difficulty: medium
points: n/a
flag_format: "PP{...}"
author: "NxT_CTFs"
flags:
 - "PP{any0ne-w4nts-to-h1k3-n0w?::Cs8V7v9KiL7o}"
---

# Signpost

## Summary

A single full-resolution phone photo of a yellow alpine fingerpost stuck in a summit cairn
field, with prayer flags and blue paint on the rock. The task is "where was this photo taken?"
and you answer by dropping a pin on a live map tool. The image has **no GPS in EXIF** — it is a
modern iPhone shot with location tagging stripped — so the solve is entirely visual OSINT:
identify the fingerpost *system* (yellow blades + red-white pole = Austrian Alpenverein), read the
destination name off the yellow blade, then find the specific pass where that destination's trail
crosses a cairn-strewn saddle.

The answer is **Beiljoch (Peiljoch), 2 672 m, Stubaier Alpen, Tirol, Austria** — a saddle on the
**Stubaier Höhenweg** between the **Dresdner Hütte** and the **Sulzenauhütte**. The accepted
coordinate was the OSM/Nominatim node `46.9922748, 11.154114`.

The single thing that cost the most time: we first misread the blade as **"Dreingher Hütte"** and
spent a long detour in **Salzburg** (Pinzgau/Pongau) because Yandex's CBIR tags pushed us there.
The blade actually reads **"Dresdner Hütte"** — a Stubai hut, in **Tirol**, ~200 km away and in a
different Bundesland. Once the first letter was read correctly, the whole search collapsed to one
Wikipedia/OSM lookup.

## Solution / Exploit

### Step 1 — Pull the metadata, confirm there is no shortcut

```bash
exiftool -a -G1 signpost.jpg | egrep -i 'gps|date|make|model|software'
```

What we got (abridged, this is the real header):

```
[EXIF] Make : Apple
[EXIF] Model : iPhone 15 Pro
[EXIF] DateTimeOriginal : 2026:09:09 08:20:23
[EXIF] OffsetTimeOriginal : +02:00
[EXIF] ImageWidth : 4284
[EXIF] ImageHeight : 5712
[MPF] ... (Live Photo: a second embedded image)
```

No `GPSLatitude` / `GPSLongitude`, no `GPSTimeStamp`. The file is a Live Photo (MPF container with
a second frame), and the header is otherwise bare — so nothing to geolocate from metadata. This is
deliberate: the challenge wants you to *look* at the photo.

### Step 2 — Reverse image search to get the country and the sign system

Full frame through Yandex CBIR. The useful signal was not a matching photo but the *tagging*:

```
mountain pass, hiking trail
... cbir_page=sites ->
 Commons: Wegweiser_Larmkogelscharte.jpg
 Commons: Rohrauer-Wegweiser.jpg
 Commons: Badener_Hütte_Wegweiser_2020c.jpg
 Commons: Guidepost_Vorder_Rüti...
 categories: "Signs in Bramberg am Wildkogel", "Bezirk Zell am See",
 "Bezirk St. Johann im Pongau",
 "Hiking and footpath fingerposts in Lend"
tag on sign-crop run: "salzburg state"
```

Two things to take from that: **Austria**, and **yellow blades on a red/white striped pole =
Austrian Alpine Club (ÖAV) fingerpost**. The Salzburg tag is what sent us down the wrong path
(see Pitfalls) — it reflects where the *reference images* live on Commons, not where this photo
was taken.

The scene itself is a strong fingerprint:

- dozens of hand-stacked slate/schist cairns covering a grey scree saddle;
- strings of Tibetan prayer flags tied across the rocks;
- blue paint sprayed/daubed on the rock face;
- one yellow arrow blade on a pole that is completely covered in stickers;
- a small white handwritten sign on top of the pole.

### Step 3 — Read the yellow blade (rotate it, don't squint at the original)

The blade is shot almost edge-on and upside-down in the frame. The trick that made it legible was
to crop tight and rotate 180°:

```python
from PIL import Image
im = Image.open("signpost.jpg")
c = im.crop((1880, 2280, 3020, 3500)) # the yellow blade cluster
c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
c.rotate(180).save("/tmp/blade_rot180.png")
```

On the rotated crop the blade reads **`Dresdner Hütte`** in the gothic/script face ÖAV uses, with
small print underneath in the same style as `ÖAV Sektion ... 822`. The second yellow blade in the
frame is blank/embossed on the visible face.

### Step 4 — Turn the hut name into a saddle

`Dresdner Hütte` is an ÖAV hut in the **Stubaital** (Stubaier Alpen, Tirol), at ~2 302 m. It is a
stage on the **Stubaier Höhenweg** (Stubai High Trail). The next stage south-east crosses a
cairn-marked saddle above the hut — the **Beiljoch**, also written **Peiljoch**, **2 672 m**. That
saddle is exactly what the photo shows: bare scree, cairn field, prayer flags, and an ÖAV fingerpost
pointing down toward the **Sulzenauhütte** on the other side. There is no summit cross and no
building — it is a pass, not a peak.

### Step 5 — Get the coordinate and submit it

The challenge accepted an OSM/Nominatim node. Look the pass up:

```bash
curl -s -A "ctf-osint/1.0" \
 "https://nominatim.openstreetmap.org/search?q=Peiljoch&format=json&limit=5" \
 | python3 -c 'import json,sys; [print(x["lat"], x["lon"], x["display_name"]) for x in json.load(sys.stdin)]'
```

The matching node returns:

```
46.9922748 11.154114 Beiljoch, Stubaier Höhenweg, Tirol, Österreich
```

Submit `46.9922748, 11.154114`. Accepted, flag granted.

### Step 6 — Flag

```
PP{any0ne-w4nts-to-h1k3-n0w?::Cs8V7v9KiL7o}
```

## Flag(s)

```
PP{any0ne-w4nts-to-h1k3-n0w?::Cs8V7v9KiL7o}
```

## Notes / Pitfalls

- **The blade does not read "Dreingher Hütte."** That was our first read off the low-res crop, and
 it is a trap: "Dreingher" is not a hut in Austria. It sent us into the Salzburg Pinzgau/Pongau
 fingerpost category that Yandex kept returning (`Wegweiser_Larmkogelscharte`, `Rohrauer-Wegweiser`,
 `Badener Hütte`, Lend, Bramberg am Wildkogel) — a whole afternoon of searching for a hut that does
 not exist. The gothic `D` + `resdner` compresses badly at low resolution; crop **then** upscale
 **then** rotate, in that order.
- **Yandex's `cbir_page=sites` tags are about the reference image's location, not yours.** The
 "salzburg state" tag came from Commons photos of *similar* Austrian fingerposts. Treat CBIR tags
 as "which country's sign system is this", never as "which state".
- **Tolerance matters.** The obvious Wikipedia coordinate for the pass, `46.99222, 11.15444`, was
 **rejected** — it is ~35 m from the OSM node and outside the picker's radius. Use the OSM node
 (`46.9922748, 11.154114`), not the Wikipedia infobox.
- **The location picker is rate-limited to 3 submissions/minute** and the challenge text explicitly
 forbids brute-forcing it. Two failed attempts burn 40 seconds; be sure before you click.
- The "hiking adventure" framing plus a summit-cairn photo invites you to look for a *peak*. It is a
 **pass/saddle (Joch)** — no summit register, no cross. Searching "Gipfel" was a dead end.
- The Live Photo's second frame and the sticker-covered pole add nothing; the readable evidence is
 the yellow blade, the prayer flags, and the cairn field.

## Artifacts

`images/` in this folder contains the original photo and the crops used above:

| file | what |
|---|---|
| `signpost.jpg` | original 4284×5712 iPhone 15 Pro photo (the challenge asset) |
| `signpost_signs.png`, `signpost_signs_big.png` | both yellow blades, upscaled |
| `signpost_yellow.png` | the readable `Dresdner Hütte` blade |
| `signpost_pole.png` | the sticker-covered pole |
| `signpost_white.png`, `sp_white2.png` | the small white handwritten sign on top |
| `sp_left.png`, `sp_left_rot.png` | left blade, raw and rotated 180° |
| `sp_right.png`, `sp_sign.png`, `sp_smallprint.png` | right blade and the small print line |
| `sp_area.png`, `sp_both.png`, `sp_top.png` | wider context: cairn field, prayer flags, blue paint |
