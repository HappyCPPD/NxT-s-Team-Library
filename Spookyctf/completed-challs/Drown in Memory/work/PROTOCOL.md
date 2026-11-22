# Drown in Memory — reversed server protocol + measured mechanics

Host: https://d2xe63kuz25gcn.cloudfront.net (from Abyss/Config/DefaultEngine.ini [Abyss] ServerURL)
Only POST /v1/session and POST /v1/step exist; every GET is 403 at CloudFront.

## /v1/session {"build_sha256": <sha of Abyss-Win64-Shipping.exe>}
-> {token, cookie(guard), tick_hz:10, oxygen_max:55, tank_refill:20, phase:"cage", position, shark, ...}
 Send Bearer token + Cookie guard on every step. Sessions are real-time (server ticks at 10 Hz).

## /v1/step {"sequence":n, "direction":[x,y,z], "capacity":c, "guard":g,
 "sprint":bool, "hide":bool, "flashlight":bool, "start":true (first call only)}
Strict pydantic model: capacity <= 3 (422), no extra fields (422), out-of-order/replayed
sequence (409), NaN in direction -> 500. Directions are clamped to 1/axis, so no teleport.

## Measured
- walk 2.0 u/s, sprint 3.3 u/s (stamina 100, ~-9/s sprinting, recovers walking)
- oxygen ~1.0/s; start 35, cap 55, +20 per tank; 6 tanks => 155 s total air
- corridor x 0..176, y clamped +-20, z shallow (~+-6); tanks at x=25..150 alternating y=+-14
- shark: patrols y~0 at 2.8 u/s, z~1; modes patrol -> stalk (d~24) -> chase (d~18) -> search
- WIN CONDITION: leave the cage (start:true) -> phase "chase" -> collect 6 tanks in order
 (checkpoint increments, collection radius ~5) -> reach submarine (176,0,0) => phase "escaped"
 and the state carries "flag".

## The mechanic that matters
Recesses exist at each wreck BELOW the plane, e.g. tank(25,-14,0) -> cover (22.6,-16.3,-2.8):
near_cover+sheltered go true there, and with hide=true + flashlight=false the shark walks
past at d=16-18 WITHOUT detecting. Without cover, hiding only shaves the radius a little.
Being inside the pocket blocks +x (exits via +z / -y).

## Solver (solver.py)
Routes wreck-to-wreck along y=+-14, ducks to the nearest pocket and hides when a threat closes,
releases once the shark is moving away. Best run so far: checkpoint 2/6, death = oxygen while
holding too long -> still needs to bank tanks during the duck instead of freezing.

## Session 2 findings (hours of empirical mapping)
- Air is the binding constraint, not the shark: total air = 35 + 20*6 = 155 s, drain is
 a flat 1.0/s even when idle/sheltered. A full run needs ~90-120 s of travel, so hiding
 must be rationed - every second parked in a recess is a second off the clock.
- hide/flashlight do NOT change speed (measured: walk 2.00 u/s with and without hide).
- capacity is flavour only: oxygen_max stays 55.0 for capacity 1.5 and 3.0; 0.1 is rejected.
- Map extent: x goes slightly negative (observed x=-4) as well as to 176+; y clamps at +/-20;
 z clamps at about -1 in the open corridor. Recesses are the exception: you enter them by
 pushing down+outward AT a wreck's x, and there z reaches ~-2.8.
- Confirmed recesses (near_cover/sheltered true, shark walks past at d=15 undetected):
 (22.6, -16.3, -2.8) <- wreck of tank 1
 (47.6, 16.3, -2.8) <- wreck of tank 2 (also seen holding at ~54,16.3,-2.8)
- Confirmed tanks: CP1 ~(25,-14,0) [hit at 21.6,-12.1], CP2 ~(50,14,0) [hit at 49.3,13.2].
 Collection radius ~5.
- TANK 3 IS NOT WHERE THE ALTERNATION PREDICTS: (75,+14) and (75,-14) both fail, and a sweep
 of the +14 lane from x=50 to x=90 collects nothing. The remaining tanks must be mapped
 empirically (or read off the real client) before a winning route can be scripted.
- Abyss.umap in the pak is only 1890 bytes (a stub) - the course is server-generated, so the
 positions cannot be recovered from the shipped assets.

## Session 3: HUD strings recovered from the shipping exe (UTF-16 string block)
The client's own strings give the intended design (Abyss-Win64-Shipping.exe, ~0x8174xxx-0x8179xxx):
 - Objectives: "Collect all 6 oxygen tanks in order. Follow ship lights to the submarine."
 - Hide loop is GATED on a server flag: "HIDDEN: keep holding E with the light off. Wait for
 PATROL CLEAR before moving on." / "PATROL CLEAR: the shark is moving away. Release E and
 swim out through the open front." -> the 'patrol_clear' field is the go/no-go, not raw distance.
 - Cover: "Green COVER marks a shelter." / "IT SEES YOU. Find a wreck recess, light off, hold E."
 Controls: SHIFT sprint, SPACE/CTRL rise-dive, F light, E hold to hide in COVER.
 - Endgame: "Escape confirmed. Read the illuminated objects in order, left to right, top to bottom."
 and "SUBMARINE AIRLOCK SEALED - Read the recovery code on the illuminated blocks."
 -> after escaping, the flag is rendered in-world as illuminated objects; the API state also
 carries a 'flag' field.
 - SUIT LIMIT: "STOCK PROPULSION INSUFFICIENT - Inspect the paired propulsion calibration."
 "FINAL GAP EXCEEDS STOCK SUIT RANGE." "Service: propulsion calibration uses paired values.
 RELEASE H TO CLOSE." "calibration inconsistent / SUIT CALIBRATION RESET / Paired values did
 not match. Factory setting restored."
 => the last leg cannot be swum on stock air; you must calibrate propulsion via a service panel
 that takes TWO PAIRED VALUES.

## Calibration probing (negative results, all http 200 unless noted)
- request schema is exactly {sequence, capacity, guard, start, sprint, hide, flashlight, direction};
 any extra field -> 422, missing/invalid Cookie -> 401.
- calibration_ok stays False across: capacity 0.1..3.0 (full grid), capacity==|direction|,
 integer capacities 0..6, capacity as a 2-element list or "a,b" string (both 422 float_type),
 header variants, start=false, extra calibrate/calibration fields (422).
=> the calibration value cannot be set through the step API; it is almost certainly an in-world
 service-panel interaction, i.e. it needs the real client (or its exact panel position).

## Session 4: running the real client (Windows build) under Wine - attempted, blocked
Environment: wine 10.0 (Ubuntu), RTX 5060 (nvidia 595.99), Xvfb :99, prefix ~/.wine-abyss.
- The Shipping exe DOES start under Wine: with rendering it created a real 1280x720 "Abyss" window
 (verified via xwininfo) but rendered only a single flat colour, then died.
 /var/crash/...wine.1000.crash records Signal 11 (SIGSEGV) inside wine itself.
- Installed vkd3d-proton v3.1 (setup_vkd3d_proton.sh install) into the prefix and renamed the game's
 bundled Agility SDK (Binaries/Win64/D3D12 -> D3D12.shipped) plus WINEDLLOVERRIDES=d3d12,d3d12core,dxgi=n,b.
 Crash persists; UE writes no log at all (Saved/Logs empty), so it dies before/at RHI init.
- Headless (-nullrhi) DOES run (no SIGSEGV) but creates no window and never uplinks, so there is
 nothing to send a keypress to. The client waits at the "ENTER Begin" screen before opening the uplink.
- Prepared for a real client capture (both ready, removed afterwards to leave the tree as found):
 * /tmp/abyss_capture_server.py - logs every request (headers+body) to /tmp/abyss_client_capture.log
 * <Project>/Saved/Config/Windows/Engine.ini with [Abyss] ServerURL="http://127.0.0.1:8000"
 (Saved config outranks the packed DefaultEngine.ini; a loose Abyss/Config/DefaultEngine.ini does NOT).
 => as soon as any real client uplinks we will see its exact /v1/session + /v1/step bodies
 (i.e. the real calibration fields), and any course data it is given.

CONCLUSION: completing this challenge needs a working UE5.8 D3D12 stack (newer Wine/Proton with
DXVK+VKD3D-Proton, or a GPU-capable Windows VM) to either play it or capture the client. The API-only
bot can hold CP2/6 but cannot navigate the wreck obstacle course or reach the calibration panel.
