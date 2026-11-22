# boxdletter

- **Event:** h4ckc0n 2026
- **Category:** Misc — 484 points, 11 solves
- **Authors:** pr4njal, ishan._.
- **Description:** "dec0d3 da b4rc0des" — flag format `d4rk{movie1_movie2_movie3}`
- **Files:** `movie1.png`, `movie2.png`, `movie3.png`

**Flag:** `d4rk{newton_sorcerer_patema_inverted}` (confirmed correct)

## TL;DR

Each image is a "movie barcode": one pixel column per second of a film, each
column filled with that second's average frame colour. The image width is the
film's runtime in seconds. Identify each film by correlating the barcode
against thumbnails of candidate films, using the exact runtime as a filter.

| File | Width (s) | Runtime | Film |
|---|---|---|---|
| movie1.png | 6281 | 1:44:41 | Newton (2017) |
| movie2.png | 7291 | 2:01:31 | Sorcerer (1977) |
| movie3.png | 5930 | 1:38:50 | Patema Inverted (2013) |

## 1. What the images are

All three PNGs are 500 px tall with no metadata, no extra chunks and no
trailing data. Every column is a single flat colour (vertical standard
deviation is exactly 0), so the only information is one RGB value per column.

The widths (6281, 7291, 5930) look like durations in seconds, about 105, 122
and 99 minutes. That reading was confirmed later: the correct copy of each
film has a file length equal to the barcode width to the second.

So the task is: given the mean colour of every second of a film, name the film.

## 2. The title hint

"boxdletter" is "letterboxd" with the halves swapped. The author handle
`pr4njal` is a Letterboxd username, and that profile has 48 watched films.
One of them is *Patema Inverted*, which gave the first identification.

The profile only solves one of the three. *Newton* and *Sorcerer* are not on
it, and no Letterboxd account was found for the second author.

## 3. Building a matcher

The barcode gives a colour per second. Two public sources give roughly the
same thing for a known film without downloading it:

- **archive.org** generates one thumbnail per minute for every uploaded
 video (`<item>.thumbs/<name>_000060.jpg`, `_000120.jpg`, ...). The number
 in the filename is the timestamp in seconds.
- **YouTube** storyboards: `yt-dlp -j <url>` lists `storyboard` formats,
 which are sprite sheets of evenly spaced frames.

For each thumbnail, take the mean RGB. Compare it to the barcode averaged
over a few columns at the same timestamp, and compute the normalised
cross-correlation (NCC) over the whole film, with a small offset search to
absorb different studio-logo lengths.

 def ncc(a, b):
 a = a - a.mean(0); b = b - b.mean(0)
 return (a*b).sum / (np.linalg.norm(a) * np.linalg.norm(b))

Calibration on known answers:

- correct film: 0.85 to 0.97
- wrong film: 0.05 to 0.35

The gap is wide enough that there is no ambiguity once the right film is
tested. `boxd_ia_match.py` is the archive.org version,
`boxd_yt_storyboard.py` the YouTube version.

## 4. Movie 3 — Patema Inverted

Found on pr4njal's Letterboxd. Two archive.org copies are exactly 5930 s
long and score 0.93 and 0.89.

## 5. Movie 1 — Newton

The barcode opens with a flat light block followed by a yellow-toned logo,
which reads as an Indian censor certificate and an Eros / Colour Yellow
ident. Testing roughly 105-minute Hindi films from that distributor gave
*Newton* (2017) at 0.95 to 0.97 against a 6272 s YouTube upload.

## 6. Movie 2 — Sorcerer

This one took most of the time. What the barcode shows:

- 18 s of black at the start and no bright studio logos
- muted khaki and dark brown for the first 60%
- about 18 minutes of teal then deep blue at 60–72%
- olive green at 72–88%
- a second short deep-blue block, then 44 s of pure black at 92%
- only about 3 minutes of end credits

Nothing on the author's profile matched, so the search had to be done blind.
The useful observation was that the barcode width equals the file length
exactly, which turns runtime into a strong filter:

1. Download the public IMDb dataset (`title.basics.tsv.gz`,
 `title.ratings.tsv.gz`).
2. Keep films with a runtime of 121 or 122 minutes and at least 800 votes:
 870 films.
3. For each title, search archive.org and keep video files within 100 s of
 7291 s.
4. Score each kept file's thumbnails against the barcode.

`boxd_ia_brute.py` does steps 3 and 4. *Sorcerer* (William Friedkin, 1977)
came out at 0.89 on a 7290.65 s file. Nothing else passed 0.36.

Full check:

 $ python3 boxd_ia_match.py -tmovie1,movie2,movie3 "Sorcerer 1977"
 sorcerer-1977_202501 len 7291 1=0.08 2=0.90 3=0.21
 sorcerer.-1977.1080p.-blu-ray...-rarbg len 7291 1=0.07 2=0.85 3=0.21
 sorcerer-1977 (different cut) len 7215 1=0.16 2=0.65 3=0.12

In hindsight the barcode fits the film: the dark prologue vignettes, the
night-time truck drive and rope-bridge crossing in the rain (the blue
block), and the jungle (the green).

## 7. Flag

Titles lowercased, spaces to underscores, no years, in file order:

 d4rk{newton_sorcerer_patema_inverted}

## What did not work

- **Pre-built barcode galleries.** About 5,400 reference barcodes were
 scraped from fan sites. Only *Patema Inverted* was in them.
- **The author's Letterboxd for movies 1 and 2.** Kahaani fits the runtime
 and sits in pr4njal's "thrillers" list, which made it a tempting wrong
 answer; it scores 0.15.
- **Accounts pr4njal follows.** One had logged *Newton*; its 1,300-film
 list had no match for movie 2.
- **Guessing from the palette.** The Sky Crawlers, Sympathy for Mr.
 Vengeance, The Ghazi Attack, Tumbbad and others all scored under 0.35.
- **Wide YouTube sweep.** Searching for uploads within 30 s of 7291 s found
 about 200 candidates, none matching, and got the IP rate-limited by
 YouTube for roughly an hour.

## Lessons

- Check whether image dimensions encode something. Here width = seconds,
 and exact runtime was the filter that made a blind search possible.
- Validate the matcher on a known answer before trusting any "ruled out".
 An early version of the comparison was broken and produced false
 exclusions.
- Subsampled scores are noisy. Using every third thumbnail gave false
 scores up to 0.58; always re-run the full comparison on a candidate.
- When OSINT hints run out, a public dataset plus a hard numeric filter
 beats guessing.

## Files

- `boxd_ia_match.py` — archive.org thumbnail matcher
- `boxd_ia_brute.py` — brute force over a title list
- `boxd_yt_storyboard.py` — YouTube storyboard matcher
- `boxd_search.py`, `boxd_match.py`, `boxd_dl*.py`, `refs/` — earlier
 reference-gallery approach
