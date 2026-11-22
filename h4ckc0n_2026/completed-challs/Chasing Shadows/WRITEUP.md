# Chasing Shadows

**FLAG:** `d4rk{2_3_8_7_11_16_17_23_19_13}` (see RESULT-chasing-shadows.md for the full proof)

Chained OSINT ("The Mirror Investigation", author Tarun, 200pt):

1. `Hidden In Plain Sight` flag = `fediverse` -> follow the Mastodon hint.
2. `https://mastodon.social/api/v1/timelines/tag/novavault` (public tag timeline; the
 search API needs auth) -> profile `@amehraCC704` ("Arjun Mehra", "NOVAVAULT - EMPLOYEE").
3. Wayback CDX for `mastodon.social/@amehraCC704*` exposes a **deleted** 8th status
 (`117501111466134851`): `Arjun Mehra: "Kabir Sharma is such a fool person!! :) …",`
 whose truncated link is `https://github.com/ECHO-704`.
4. GitHub `ECHO-704` repo `-` / `:).py`: each commit's decorative "NOVA VAULT" verifier
 recovers one **pair of digits**; the commit messages give the order
 ("first pair", "next pair", "last pair", and "this should come *before* the previous
 commit" fixing the 11:44/11:45 commit ahead of the 11:37 one).
 Pairs -> `2_3 8_7 11_16 17_23 19_13`.
5. Verified live: `Behind The Login` = "ECHO — Private Network"; POSTing the sequence to
 `/api/auth/pattern` returns `{"ok":true}` + an `echo_access` cookie, and the pattern is
 a legal 5x5 pattern-lock path (all steps Chebyshev-adjacent).

FLAG: `d4rk{2_3_8_7_11_16_17_23_19_13}`
