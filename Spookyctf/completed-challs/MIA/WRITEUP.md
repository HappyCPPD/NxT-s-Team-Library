# MIA — Writeup

**Category:** OSINT · **Points:** 750

## Flag
`spooky{Friedhof_Bad_Harzburg}`

## Given
`Unknown_Photo.png` — a staged photo of a freshly dug, grave-shaped trench
with a shovel, in a mulched planting bed. No EXIF/GPS (exiftool shows only
PNG headers), no appended data after IEND — pure visual OSINT.

## Clues
- A small black enamel **"Grabpflege"** (grave-care) marker with a flower
 graphic — the kind cemetery gardeners place on tended graves → the scene
 is a **cemetery**.
- Two printed items resting on a flat stone:
 - An official hiking **Wegweiser / info leaflet** titled **"Burgberg-Plateau"**
 with the **"BAD HARZBURG"** town wordmark and destinations incl.
 *"Kreuz des Dt. Ostens"* and *"Kaiserweg"* — both specific to the Großer
 Burgberg in Bad Harzburg.
 - A region card with an orange sunset skyline + lynx and the word **"Harz"**
 (regional branding; confirms the Harz).

## Reasoning
The leaflet pins the **historical site** the informant wanted to visit: the
Großer Burgberg in Bad Harzburg (Große Harzburg ruins / Canossasäule). Per the
task the captor "brought them somewhere **nearby to hide**" — so the flag is the
**hiding place**, not the historical site. The "Grabpflege" grave sign marks the
hiding place as a **cemetery**, and the main cemetery of Bad Harzburg is the
**Friedhof Bad Harzburg** (Geißmarstraße 10).

## Key trap
Easy to burn attempts on the plateau monuments — Große Harzburg, Canossasäule,
Krodo-Altar, Kreuz des Deutschen Ostens. Those are the *historical site*, not
where the body was hidden. The answer is the nearby cemetery.
