# hilly billy

- **CTF:** h4ckc0n 2026
- **Category:** Misc
- **Points:** 300 (2 solves when we picked it up), one attempt only
- **Author:** pr4njal
- **Flag:** `d4rk{C_2}` (accepted)

## Challenge

> I am lost, please locate me on the map so I can request help
>
> flag format: `d4rk{letter_number}`

One file, `hilly_billy.webp` (1280x640). The left half is a contour map with rows labelled A–E and columns labelled 1–5. The right half is a 3D render of what the lost person sees: a rounded olive hill on the left, a taller brown hill climbing off the right edge, and a small tan cone far away in the gap between them.

No metadata, no stego. It is a pure "match the view to the map" puzzle.

## What the answer is

The viewer stands on grid intersection **C2**, looking south-east.

![photo vs render from C2](c2_view.png)

| In the photo | On the map |
| --- | --- |
| Left hill: rounded, olive, flat top | West end of the arc-shaped 300 m ridge around C3 |
| Small tan cone in the gap | The isolated 350 m hill at D3, about 1.5 cells away |
| Right hill: brown, bumpy, rising off the edge | The D1–D2 massif: 350 m lobe, 400 m ridge, then the 550 m peak |

## Two observations that made it tractable

**The labels sit on the grid lines, not in the cells.** A–E and 1–5 are each drawn exactly on a line, so "letter_number" names one of 25 intersections. I assumed the camera was placed on one of them.

**The render is coloured by height.** Low ground is green, mid slopes olive, high ground brown/tan. So the left hill is lower than the right hill, and the distant cone is at least as high as the left one. This is what broke the ties later.

## Solve

Eyeballing gave me two or three plausible spots and I only had one submission, so I rebuilt the terrain and rendered it.

### 1. Rebuild a heightmap from the contours

- Thresholded the map at grey < 207 (after 3x upscale) to keep only the dark 50 m index contours and drop the faint 10 m ones (`solve/seg.py`).
- Labelled connected components of those lines (`solve/comp.py`), then assigned an elevation to each by hand, reading the printed labels (`solve/hm.py`). About 80 components.
- The rings around the 550 m peak merged into one blob, so I threw that component away and drew the 350–550 m rings as polylines.
- Filled between the lines by relaxing Laplace's equation with the contour pixels held fixed, then a light Gaussian blur (`solve/solve.py`). Gaps where labels break a line do not matter with this method.

My first attempt segmented the *regions between* contours instead. That failed because every label gap leaks one region into the next. Assigning heights to the lines themselves was the fix.

### 2. Match the skyline

- Extracted the skyline from the photo (first non-blue pixel in each column).
- For a position on the map, computed the horizon elevation in every direction, then least-squares fitted the photo's skyline over heading, field of view, vertical scale and horizon row (`solve/match.py`, `solve/fit.py`, `solve/fit2.py`).

Skyline shape alone was **not** decisive. Best RMS per intersection:

| Intersection | RMS (px) | Heading |
| --- | --- | --- |
| C3 | 6.3 | 341° |
| C4 | 6.4 | 77° |
| C2 | 7.3 | 133° |
| E3 | 7.4 | 350° |
| everything else | 8.5+ | |

### 3. Render the finalists and look

Rendering the top four in perspective with height colouring (`solve/persp.py`) settled it:

- **C3, C4:** two hills and a gap, but nothing in the gap.
- **E3:** has a distant peak in the gap, but the taller, browner hill is on the left. Colours reversed.
- **C2:** olive hill left, tan cone in the gap, brown stepped hill rising to the right edge. Only one with all three.

As a cross-check, the unconstrained search over the whole map put the best fit for this same view on the C line about a quarter-cell east of C2.

## Caveats

The render from C2 is a qualitative match, not a pixel match. In the real image the hills loom much larger and the foreground slopes away, where mine is flat. I had to guess the vertical exaggeration and FOV, and interpolating from 50 m contours flattens every hilltop. I submitted on the strength of the left/cone/right arrangement plus the colour ordering, and said so before spending the attempt.

## Files

- `c2_view.png` – photo, render from C2, and the map with the view cone marked
- `solve/` – the scripts above, as run. They have hard-coded paths to the original image and write intermediates (`dark.npy`, `clab.npy`, `cons.npy`, `z.npy`, `prof.npy`) to the current directory, so edit the paths before re-running. Order: `seg.py 207` → `comp.py` → `hm.py` → `solve.py` → `match.py` → `fit.py` / `fit2.py` → `persp.py` / `show.py`. Needs numpy, scipy, Pillow, matplotlib.
