# RESULT — State property (OSINT 100) — UNRESOLVED

STATUS: BLOCKED on tooling (not on understanding)

## Artifact
state_property.webp (2432x1438, WebP, XMP says exif:UserComment = "Screenshot",
Apple ICC profile; NO GPS, NO camera EXIF). A Google Maps Street View screenshot.
Scene: two-lane paved road with white edge line (no centre line), a pond immediately
LEFT of the road with a small wooden dock on its bank, a wooden utility pole with a
transformer + meter box on the road side, power lines receding along the road, green
(corn) field beyond the pond, loblolly pines on the right. Two small white signs on
posts at the pond's far bank — text NOT legible at any upscale.

Challenge hint: "Well, it infact was state property." Flag: d4rk{xx.xxxxxxx,yy.yyyyyyy}
= the exact Street View panorama camera coordinate (7 dp).

## What was tried
- EXIF/XMP: stripped (screenshot); no GPS.
- OCR / 6x upscaled crops of the two pond signs: unreadable.
- Reverse image search (Yandex CBIR via skill ris.py): only generic tags
 (`golf course`, `road`, `commons wikimedia`, `intersection`, `park`) — image is NOT
 indexed (author's own screenshot).
- OSM/Overpass: ponds near Piedmont State Hospital (Burkeville VA, ~37.19,-78.20,
 prior lead) enumerated with nearest roads.
- Google Street View metadata endpoint
 (`maps/photometa/si/v1`) now returns the empty result `)]}'[[5],[]]` for EVERY
 point including ones that worked earlier today -> pano discovery + thumbnail
 rendering is currently refused from this host. Blocks the whole automated SV-compare
 approach.

## Lead / current best hypothesis
Region: rural Virginia around the Piedmont State Hospital / Burkeville area
(lat ~37.15-37.21, lon ~-78.10..-78.24). The target's straight bank + a state-owned
pond (hint "state property") is consistent with the "Piedmont State Hospital Dam"
pond. NOT verified — the matching pano was not found.

## What would unblock it
A clean egress. Confirmed blockers on this host (2026-11-15):
- `computer_use` CANNOT drive the session: cua-driver refuses both background
 ("no focus-free input backend") and foreground
 ("Wayland compositor does not expose a verified, target-addressable activation
 adapter for window ...; refusing global input").
- X11 fallback also dead: Firefox/Chrome are Wayland-native, so `xdotool` (which
 works, DISPLAY=:0) lists only Steam/Spotify/mutter — the browsers are not X11
 windows and there is no active X11 window. `ydotool`/`wtype`/`xte` not installed.
- Google Lens is IP-captcha'd from here: `lens.google.com/uploadbyurl?url=<catbox>`
 redirects to /sorry showing `IP address: 115.66.218.203` (the host's own IP).
- Yandex CBIR by-URL (browser-rendered) returned only resemblance hits — rural US
 road/pond pages, incl. two VIRGINIA pages (Locust Grove, Orange County VA;
 Indian Heritage RV Park, Martinsville VA) — plus NJ crash photos. No exact match.

=> The solve is a Google Lens run from a clean IP (user's phone). Lens names the
 place, then the Street View pano coordinate is read off the Maps URL.
Remaining option on-box: install `wtype`/`ydotool` (needs sudo) to type into the
Wayland browser — still subject to the same IP captcha, so it does not fix Lens.
