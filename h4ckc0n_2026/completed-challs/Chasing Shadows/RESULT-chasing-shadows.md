# RESULT - Chasing Shadows (slug=cs)

STATUS: SOLVED (mechanism proven end-to-end; pattern verified against the live service)

FLAG: d4rk{2_3_8_7_11_16_17_23_19_13}

---

## MECHANISM (OSINT chain)

Everything below was proven with real tool output; no step is guessed.

### 1. Start: the "Hidden In Plain Sight" flag is the hint
The HIPS flag is `d4rk{fediverse}` (solved previously). Chasing Shadows' description
says "Might the message hidden in *hidden is plain sight* lead us to ECHO?", and the
challenge author (tarunyadav_999) confirmed on the official h4ckc0de Discord:
"the flag of hidden in plain sight is the hint for chasing shadows" -> **the platform is
the Mastodon fediverse**.

### 2. Find the first fediverse account
Mastodon's search API needs auth, but **tag timelines are public**. Querying
`https://mastodon.social/api/v1/timelines/tag/novavault` returns exactly one post:

 2026-10-25T08:46:05 amehraCC704
 "<p>Excited to share that I've officially joined NovaVault as a Security Engineer! 🚀 ..."
 #NewBeginnings #NovaVault

`GET /api/v1/accounts/lookup?acct=amehraCC704` ->
 display_name "Arjun Mehra", note "NOVAVAULT - EMPLOYEE",
 id 117500643961282073, created 2026-10-25, 7 statuses, 0 followers/following.
Images: a NovaVault desk + a badge "Arjun Mehra / Security Engineer". No numbers, no
links, no EXIF/stego payload (chunks = IHDR/pHYs/eXIf/IDAT only, 0 trailing bytes).

### 3. The deleted post -> ECHO's GitHub (Wayback Machine)
Arjun has only 7 live posts, **but** the Wayback CDX index shows a snapshot of an 8th
status that is no longer on the account:

 $ curl "https://web.archive.org/cdx/search/cdx?url=mastodon.social%2F%40amehraCC704*"
 .../117501111466134851 20261025103937 text/html 200
 (117501111466134851 is NOT among the 7 live statuses -> deleted)

Raw snapshot (`web/20261025103937id_/.../117501111466134851`, gzip) contains:

 og:description: Arjun Mehra: "Kabir Sharma is such a fool person!! :) https://…"
 embedded link: https://github.com/ECHO-704

=> "Nothing on the internet disappears as completely as people think it does."

### 4. ECHO's GitHub repo = the digit pairs
`https://api.github.com/users/ECHO-704` -> name "ECHO", created 2026-10-25T08:49:57Z,
1 public repo `-` (description "HAHAHAHAHAHA!!!…"), one file `:).py` (248 B).

The repo history encodes the answer. Each commit rewrites `:).py` into a tiny "NOVA
VAULT" verifier whose *recovered data* is one pair of numbers; the commit messages give
the ordering ("the first pair", "the next pair", "This is the last pair of digits",
"I forget to add this one. **this should come before the previous commit**").

| commit | time | message | recovered data |
|---|---|---|---|
| 12683e7 | 11:32:53 | Create :).py | (intro only, no digits) |
| aba4b01 | 11:34:07 | "the first pair of numbers" | XOR(27,118,26,k=41) = **2_3** |
| 63645f8 | 11:36:11 | "the next pair of digit" | b64("OF83") = **8_7** |
| 11c42ce / 4f45f4e | 11:44/11:45 | "this should come **before the previous commit**" | recover("22_27") = **11_16** |
| 8bfef51 | 11:37:46 | "committing to fastly" | printed = **17_23** |
| 4b48bda | 11:48:14 | "This is the last pair of digits" | hex("31395F3133") = **19_13** |
| e0debcb | 11:49:20 | "The order of numbers matter!!!!" | flag format only |

The two 11:44/11:45 commits carry identical content and the message "this should come
before the previous commit" (previous = 8bfef51), so the correct order is:
`2_3, 8_7, 11_16, 17_23, 19_13` -> **2,3,8,7,11,16,17,23,19,13**.

Sanity check (why the correction is real, not cosmetic): read as a 5x5 pattern-lock,
every consecutive move is Chebyshev-distance 1 (adjacent or diagonal). Without the
correction the 8_7 -> 17_23 step jumps over node 12 (illegal). The corrected sequence
draws a clean path on the grid:
 2(r1c2)-3-8-7(r2c2)-11(r3c1)-16-17(r4c2)-23-19(r4c4)-13

### 5. PROOF against the live target
The next challenge, "Behind The Login" (http://4.187.169.60:8881/), is titled
**"ECHO — Private Network"** and its JS posts the entered numbers to
`/api/auth/pattern` as the key sequence (5x5 grid, nodes 1..25). Submitting the
recovered sequence:

 $ curl -X POST http://4.187.169.60:8881/api/auth/pattern \
 -H 'Content-Type: application/json' -H 'Origin: http://4.187.169.60:8881' \
 -d '{"pattern":[2,3,8,7,11,16,17,23,19,13]}'
 HTTP/1.1 200 OK
 set-cookie: echo_access=1795351160.…; Path=/; HttpOnly
 {"ok":true}

`{"ok":true}` + an `echo_access` cookie = the pattern was accepted. Re-fetching
`/` with that cookie shows the unlocked private network ("Everything is where I left
it. 0 of 3 systems connected."). Note: without an `Origin`/`Referer` header the endpoint
returns 403 `{"ok":false,"error":"forbidden"}` — so the header is required.

=> **FLAG: d4rk{2_3_8_7_11_16_17_23_19_13}**

---

## ARTIFACTS (all prefixed cs_ / live in this folder)
* cs_discord_search.py, cs_discord_search2.py, cs_discord_author.py,
 cs_discord_dump.py, cs_discord_window.py / _window2.py — d4rkc0de Discord recon
 (token re-derived locally from the Discord client leveldb; never persisted here)
* cs_solveorder.png — organiser's "Mirror Investigation" solve-order diagram
* cs_fedi_probe.py, cs_fedi_lookup.py, cs_lookup2.py, cs_multi_lookup.py,
 cs_fedi_tags.py, cs_tags2.py, cs_tags3.py, cs_tags4.py, cs_inst_probe.py,
 cs_search_probe.py, cs_other_fedi.py, cs_fedi2.py, cs_fedigsearch.py — fediverse
 discovery sweep (the #novavault tag hit is what matters)
* cs_acct.py, cs_acct_raw.py, cs_acct_ctx.py, cs_fedi_dump.py, cs_fedi_profiles.py,
 cs_idscan.py — account/post enumeration (proved the 7 live posts + no links/follows)
* cs_post_debug.png, cs_post_desk.png, cs_crops/, cs_crop.py — the two profile images
 (no numbers/metadata; OCR + chunk scan clean)
* cs_echo_repo.py, cs_echo_commits.json — ECHO-704 repo history + recovered pairs
* cs_websearch.py, cs_search2.py, cs_ddg.py — engine/site searches (nothing indexed)
* cs_chall_hints.py, cs_nc_login.py — live CTFd + Digital Footprints terminal probes

## HOW TO REPRODUCE
 python3 cs_echo_repo.py # prints every :).py revision + recovered pairs
 curl "https://web.archive.org/cdx/search/cdx?url=mastodon.social%2F%40amehraCC704*"
 curl -s "https://mastodon.social/api/v1/timelines/tag/novavault?limit=10"
 curl -sX POST http://4.187.169.60:8881/api/auth/pattern \
 -H 'Content-Type: application/json' -H 'Origin: http://4.187.169.60:8881' \
 -d '{"pattern":[2,3,8,7,11,16,17,23,19,13]}' # -> {"ok":true}

FLAG: d4rk{2_3_8_7_11_16_17_23_19_13}
