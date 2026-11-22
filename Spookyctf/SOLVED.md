# SpookyCTF 2026 — solved ledger

Raw flags live in `.flags` (git-ignored) — referenced here as `.flags#<challenge>`.
Status: `PROVEN` = a reproducer artifact exists in the challenge folder and emits the exact
flag; `REPORTED` = flag taken from the folder's WRITEUP.md, not re-verified by me since.

| challenge | category | status | proof artifact | flag ref | date |
|---|---|---|---|---|---|
| Drown in Memory | misc | PROVEN | completed-challs/Drown in Memory/work/solve_calibrated.py (+ PROTOCOL.md) | .flags#drown-in-memory | 2026-11-08 |
| Arachnophobia | ? | REPORTED | completed-challs/Arachnophobia/WRITEUP.md | .flags#arachnophobia | 2026-11-07 |
| Cyberphobia: Formatting Nightmare | web | REPORTED | completed-challs/Cyberphobia_ Formatting Nightmare/WRITEUP.md | .flags#cyberphobia-formatting | 2026-11-07 |
| Cyberphobia: Overflowed Bits | pwn | REPORTED | completed-challs/Cyberphobia_ Overflowed Bits/WRITEUP.md | .flags#cyberphobia-overflow | 2026-11-07 |
| Cyberphobia: SpOoKy KeYsTrEaMs | crypto | PROVEN | completed-challs/Cyberphobia: SpOoKy KeYsTrEaMs/solve.py | .flags#cyberphobia-keystream | 2026-11-07 |
| Diagraphephobia | crypto | REPORTED | completed-challs/Diagraphephobia/WRITEUP.md | .flags#diagraphephobia | 2026-11-07 |
| Eisoptrophobia | ? | REPORTED | completed-challs/Eisoptrophobia/WRITEUP.md | .flags#eisoptrophobia | 2026-11-07 |
| Elves can be Spooky Too | rev | REPORTED | completed-challs/Elves can be Spooky Too/WRITEUP.md | .flags#elves | 2026-11-07 |
| Frankenstein's Password Generator | crypto | REPORTED | completed-challs/Frankenstein's Password Generator/WRITEUP.md | .flags#frankenstein | 2026-11-07 |
| Gelotophobia | ? | REPORTED | completed-challs/Gelotophobia/WRITEUP.md | .flags#gelotophobia | 2026-11-07 |
| Heads will Roll | ? | REPORTED | completed-challs/Heads will Roll/WRITEUP.md | .flags#heads-will-roll | 2026-11-07 |
| Hemophobia | ? | REPORTED | completed-challs/Hemophobia/WRITEUP.md | .flags#hemophobia | 2026-11-07 |
| I Feel Like Someone's Watching Me | ? | REPORTED | completed-challs/I Feel Like Someone's Watching Me/WRITEUP.md | .flags#watching-me | 2026-11-07 |
| J_b Application | web | REPORTED | completed-challs/J_b Application/WRITEUP.md | .flags#jb-application | 2026-11-07 |
| Klediophobia | ? | REPORTED | completed-challs/Klediophobia/WRITEUP.md | .flags#klediophobia | 2026-11-07 |
| MIA | osint | REPORTED | completed-challs/MIA/WRITEUP.md | .flags#mia | 2026-11-07 |
| Nosocomephobia | osint | REPORTED | completed-challs/Nosocomephobia/WRITEUP.md | .flags#nosocomephobia | 2026-11-07 |
| Numerophobia | crypto | REPORTED | completed-challs/Numerophobia/WRITEUP.md | .flags#numerophobia | 2026-11-07 |
| Peering Eyes | forensics | REPORTED | completed-challs/Peering Eyes/WRITEUP.md | .flags#peering-eyes | 2026-11-07 |
| Phasmophobia | audio/osint | REPORTED | completed-challs/Phasmophobia/WRITEUP.md | .flags#phasmophobia | 2026-11-07 |
| read the rules | misc | REPORTED | completed-challs/read the rules/WRITEUP.md | .flags#read-the-rules | 2026-11-07 |
| Stash the Hash | crypto | REPORTED | completed-challs/Stash the Hash/WRITEUP.md | .flags#stash-the-hash | 2026-11-07 |
| The Haunted Portrait | misc | REPORTED | completed-challs/The Haunted Portrait/WRITEUP.md | .flags#haunted-portrait | 2026-11-07 |
| The Model Knows | misc/ai | REPORTED | completed-challs/The Model Knows/WRITEUP.md | .flags#the-model-knows | 2026-11-07 |
| The Phantom Login | web | REPORTED | completed-challs/The Phantom Login/WRITEUP.md | .flags#phantom-login | 2026-11-07 |
| Tormented Tanny | misc | REPORTED | completed-challs/Tormented Tanny/WRITEUP.md | .flags#tormented-tanny | 2026-11-07 |
| Xenoglossophobia | misc | REPORTED | completed-challs/Xenoglossophobia/WRITEUP.md | .flags#xenoglossophobia | 2026-11-07 |

## Not a real challenge
- `Quinn's Secret Treasure` — the flag `spooky{lets_g3t_cr4zy_pudd1n}` in that folder is a
 fabricated/self-made puzzle, NOT a SpookyCTF board challenge (confirmed by the user). Deliberately
 excluded from `.flags`; do not spend time on it.

## Still open at event root
- Hashphobia (misc, hash recon) — OSINT-flavoured by design.
- The Logical Way (crypto, 7z + hashcat).
