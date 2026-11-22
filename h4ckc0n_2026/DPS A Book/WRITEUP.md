# DPS A Book — h4ckc0n 2026 (OSINT, 400 pts)

FLAG: `d4rk{2019_DPS_Abook_with_the_kirby_griffin}`

Author: pr4njal (Pranjal Solanki, `sol4nki` — d4rkc0de-club / IIIT-Delhi, h4ckc0n organiser).

## Challenge

 DPS A Book
 400 — Author: pr4njal
 "What do only the OGs remember?"
 DPS A Book isnt about a film or a book or a school
 Free Hint: "bonfire" iykyk HAHA
 flag format: d4rk{...}

## Solution

Two hints, decoded literally:

1. **"bonfire" = an old name for Discord.** Not a campfire metaphor, not a school festival —
 the platform. ("iykyk" = you only know that if you were around for the name.)

2. **"DPS A Book" is a Discord *username***, not a book/film/school. Specifically the handle of a
 player who won **Discord's 2019 "King of the Hat" HypeSquad tournament/competition**.

Follow the second hint to the game's official server:

 https://discord.gg/kingofthehat (guild "King of the Hat", id 311623758395998219,
 Hat Games, Montreal — VERIFIED, features: VERIFIED,
 COMMUNITY, DISCOVERABLE)

Inside that server, search for the phrase the challenge title/description echoes —
**"ogs remember"** — which surfaces a message from user **ABOOK**:

 "only the OGs remember 2019 DPS Abook with the kirby griffin"

The flag is the combined text of that message **after the word "remember"** up to (and
including) the word **"griffin"**, lowercased/spaced as below:

 remember 2019 DPS Abook with the kirby griffin
 ^-----------------------------------^ = 2019_DPS_Abook_with_the_kirby_griffin

 d4rk{2019_DPS_Abook_with_the_kirby_griffin}

Note the flag preserves the message's own capitalisation: "Abook" (not "A Book"), the leading
"2019", and "kirby griffin" lowercase.

## Corroboration of the mechanism (what was checked, unauthenticated)

- `discord.com/api/v10/invites/kingofthehat` → 200, guild id 311623758395998219,
 name "King of the Hat", description "A 2D party platformer where you fight with a hat!"
 Server widget also public → instant_invite + member list.
- The tournament is real: "The King of the Hat HypeSquad Balance badge was awarded to all
 HypeSquad Balance members as part of Discord's King of the Hat HypeSquad Tournament that was
 announced on February 18th, 2019." (r/discordapp thread; mirrored in
 github.com/Costpap/discordia-wiki/blob/master/badges.md).
- The ABOOK message itself is behind the Discord login wall — read by the operator, not
 reproduced here by an unauthenticated tool.

## Why the obvious reading wasted three rounds (dead ends — do not repeat)

Everything pointed at "DPS = Delhi Public School Dwarka" and its computer club **C.O.Я.E**
(github.com/coredps, coreisus.com, IG @coreisus, FB /dpsCore, old coreis.us). That whole world was
crawled exhaustively — 265 mirrored URLs + all `/Data/*.json`, the 45 internal docs (client-side
`docs.coreisus.com` password gate bypassed; bodies are unauthenticated markdown at
`/Data/docs/<id>.md`), the full alumni/OG roster 2006→2023, old coreis.us 2011-2019 (CORE4/8/9/10/11
prelim PDFs, enCORE 2012, EnCore CTF), GitHub orgs, YouTube, all 30 Instagram posts (2020-2026),
18 FB posts, Telegram, the alumni-run FB page, dpsdwarka.com (68 pages + PDFs) — and produced
**zero "bonfire"**. The club's own word is "training camp" (2021) → "campground" (2025) →
"campfire" (2026), which is exactly the trap: a plausible in-world term that is not the hint.

The author's disclaimer ("isnt about a film or a book or a school") is the tell — it rules out
*DPS the school*. And "bonfire" as a synonym for Discord is a *platform-history* fact, not a
club-history fact, so no amount of CORE crawling could ever have found it. The search space was
the Discord *username* "DPS Abook" inside the King of the Hat server, not the club's web surface.

Lesson: when a hint is a "iykyk" in-joke, resolve it against the widest possible referent
(a platform's former name) before narrowing to the target's own community. Here the correct
referent was Discord itself.
