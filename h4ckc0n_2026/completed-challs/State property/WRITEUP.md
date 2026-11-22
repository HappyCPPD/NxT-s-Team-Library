# State property

**CTF:** H4ckc0n 2026 | **Category:** OSINT | **Points:** 100 | **Author:** pr4njal

> Well, it infact was state property.
>
> flag format: `d4rk{xx.xxxxxxx,yy.yyyyyyy}`

**Flag:** `d4rk{37.1960469,-78.1451758}`

## The image

`state_property.webp` is a Google Street View screenshot (2432x1438). The
metadata is stripped apart from an Apple display ICC profile and a
`UserComment` of "Screenshot", so there is no GPS to read.

What the scene gives:

- a two-lane rural road with a white edge line
- a pond right beside the road, mowed bank, crop field behind it
- a wooden utility pole with a meter box, service lines running along the road
- a block of hardwoods on the right
- two small white signs on the far bank, unreadable at any upscale
- a `© 2026 Google` watermark, so it is the current capture

Nothing in the frame names a place. Reverse image search only returns
lookalike rural roads, because the screenshot is the author's own.

## The hint is the solve

"Well, it in fact was state property" is a line from a viral fishing video.
Two anglers are fishing a roadside pond when a man in a white pickup pulls up
and runs them off:

> "He who told you could fish here?" / "I thought it was state property." /
> "This ain't no state property. This is priiiivate property." / "Lock em up!"

Searching the quote finds the video. Two things in it place the pond:

1. A caption early on reads **NOTTOWAY COUNTY VA**.
2. The man says the owner is Trey Taylor of Crewe Tractor, and the short
 version of the clip cuts to a fishing-forecast app with a saved spot named
 "Lock em up pond. Tray Taylor Crewe Tracktor. Priiiiiivate property!" The
 coordinates under the name are readable in a 720p frame:

 **37°11.766' N, 078°08.742' W** = 37.19610, -78.14570

Reverse geocoding that point gives Watsons Wood Road, Crewe, Nottoway County,
Virginia. The pond sits on the west side of the road.

## Finding the exact panorama

The flag wants seven decimals, which is the precision Google Maps puts in a
Street View URL, so the answer is the panorama's own position and not the pond.

I queried the Street View metadata endpoint (`maps/photometa/si/v1`) around
the pond. It returned 21 panoramas along that stretch, including several
captures from different years stacked within a few metres of each other
(2009, 2016, 2018, 2021, 2023 and the current one). I pulled a thumbnail of
each looking north-west and compared them with the screenshot.

Only one matches on every detail (cloud pattern, mowed bank, the fitting on
the service line next to the pole, tree shapes):

| | |
|---|---|
| Pano ID | `2Sl4oaj53fo2qZ8TrZZINg` |
| Address | 1089 Watsons Wood Rd, Crewe, Virginia |
| Position | 37.19604691789024, -78.14517581859454 |

Truncated to seven decimals that is `37.1960469,-78.1451758`.

The nearest wrong answer is the older capture `wgzVCZPERY0q0n7Bz5JOqw` at
37.1960383, -78.1451758, which shows the same view without the fitting on the
line and with different clouds.

## What went wrong the first time

The first pass treated the hint as a description of the land and went looking
for state-owned ponds, landing on the Piedmont State Hospital area near
Burkeville. That is about 6 km from the real spot, close enough to feel
promising and far enough that a pond-by-pond Street View scan never hit it.
The hint was a quote, and quoting it was the whole challenge.

## Takeaways

- When an OSINT description reads like something a person said, search it as
 a quote before reading it as a clue about the place.
- Check every frame of a source video, including app screens and overlays.
 The coordinates were on screen for about a second.
- For "exact coordinates" flags, answer with the panorama position, and
 compare all the captures at that spot. Historical panoramas sit a metre or
 two apart and each has different seventh-decimal coordinates.
