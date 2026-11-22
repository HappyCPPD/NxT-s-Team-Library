# Hemimegaminx — writeup

Site: https://h4ckc0n-arcade.chals.io/hemimegaminx/ (Misc, 100 pts)

## Goal
Load the hourly scramble (`GET /api/challenge` -> {id, expiresAt, state}) and submit a solving
move sequence (`POST /api/solve` {challengeId, moves:[{face,turns}]}). Max 1000 moves. Server
returns the flag when the state reaches solved.

## Puzzle model (from the shipped JS)
6 face positions, 15 edges, 10 corners (icosahedron modulo antipodes). State =
edgePerm[15], edgeOri[15], cornerPerm[10], cornerOri[10]. A move is (face 0..5, turns 1..4 = +72k deg).
Group order = 5.9e29 — far too big for BFS/meet-in-the-middle.

## Attack: group word problem with a dense generating set
1. Represent the puzzle as a permutation group of degree 60 (edge stickers = 2 per edge,
 corner stickers = 3 per corner). `face_perm(f)` sends each sticker to its destination.
2. Convert the server `state` into the sticker permutation `g` (solved -> current).
3. Use GAP (via sage libgap):
 `phi = EpimorphismFromFreeGroup(G); w = PreImagesRepresentative(phi, g); LetterRepAssocWord(w)`
 - with the 6 face turns only, the word is 3499 letters (~3137 moves) — over the limit.
 - **fix:** hand GAP a *dense* generating set: all 504 distinct elements reachable within 2
 face turns (each with its known <=2-move expansion). The BSGS transversals become short, so
 the returned word is only 554 generators. Expanding + cancelling adjacent same-face turns
 gives **833 moves**.
4. Verify by simulation on the server state (the solve word is the inverse of the word for `g`).
5. Submit; server replies `{"ok":true,"flag":"d4rk{d1d_y0u_s0lv3_th3_H3m1m3g4minx_by_hand_???}"}`.

**Flag:** `d4rk{d1d_y0u_s0lv3_th3_H3m1m3g4minx_by_hand_???}`

## Lesson
When a permutation-puzzle service gives the model and accepts a bounded-length solution,
don't search the state space. Ask a group-theory engine (GAP `PreImagesRepresentative`) for a
word, and if the word is too long, feed it a **dense generating set of short elements** — the
BSGS transversals shrink and so does the output word.
