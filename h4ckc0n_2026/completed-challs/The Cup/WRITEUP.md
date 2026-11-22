# The Cup

**CTF:** h4ckc0n 2026 · **Category:** OSINT · **Author:** pr4njal

**Flag:** `d4rk{come_to_the_dark_side}`

## Challenge

A screenshot of a browser showing a raw YouTube banner image (`yt3.googleusercontent.com/…`): a top-down photo of a white mug of black coffee, cropped to a thin strip. "I am curious what's on the cup?"

## Solve

The text is printed on the inside rim of the mug and the banner crop cuts the middle of it away. What survives:

- far left: the bottom of a large capital `C`, then the bottom of a small round letter, so `Co…`
- far right: a clearly legible `…side`

A phrase starting `Co…` and ending `…side`, printed inside a mug of black coffee, is "Come to the dark side". Submitted in the flag format with underscores and it was accepted.

## What did not matter

The address bar (middle of the URL blanked), the "Paul - YouTube" neighbouring tab, the EsDeeKid picture-in-picture and the tab title "Vlys" (just the image filename) all look like a trail to the owning channel. We spent three sessions on reverse image search, Wayback and sweeping "Paul" channels by banner hash and never found it. None of that was needed.

Lesson: on a low-point OSINT with many solves, try the obvious reading of the artifact before hunting for its source.
