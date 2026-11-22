# RESULT — Hemimegaminx (Misc 100)

STATUS: SOLVED

FLAG:
d4rk{d1d_y0u_s0lv3_th3_H3m1m3g4minx_by_hand_???}

MECHANISM
The site (https://h4ckc0n-arcade.chals.io/hemimegaminx/) hands out an hourly-scrambled
Hemimegaminx state and accepts a move list (<=1000 moves) at POST /api/solve; the server
re-applies the moves and returns the flag when solved.

State model (from hemi-hemimegaminx.js / hemi-tables.json):
 state = edgePerm(15) + edgeOri(15) + cornerPerm(10) + cornerOri(10); moves = 6 faces x turns 1..4.
 Group order = 587631543342363147711283200000 (~5.9e29) -> brute force / MITM impossible
 (meet-in-the-middle depth 4+4 = 8 moves found no intersection).

Solution approach (group-theoretic word problem):
 1. Encode the puzzle as a permutation group of degree 60 (edge stickers 2*15 + corner stickers 3*10).
 face_perm(f) maps each sticker to its destination; verified consistent with applyMove/isSolved.
 2. Express the server state as a sticker permutation g (solved -> current).
 3. Ask GAP for a word in the generators via libgap:
 G = Group(gen_perms); phi = EpimorphismFromFreeGroup(G);
 f = PreImagesRepresentative(phi, g); LetterRepAssocWord(f)
 With ONLY the 6 face turns GAP returned a 3499-letter word (3137 moves after mod-5) - too long.
 4. Trick: give GAP a DENSE generating set = all 504 distinct elements reachable in <=2 face turns
 (each with its known <=2-move expansion). Transversals then become short and GAP's word is
 554 letters -> expanded and face-cancelled to 833 moves (< 1000 limit).
 5. Verified locally by simulating the move list on the server state -> solved; then inverted
 direction (the solved sequence is the inverse of the word representing the state).
 6. POSTed {challengeId, moves:[{face,turns}...]} -> {"ok":true,"flag":"..."}.

KEY OUTPUT
 POST /hemimegaminx/api/solve -> HTTP 200
 {"ok":true,"flag":"d4rk{d1d_y0u_s0lv3_th3_H3m1m3g4minx_by_hand_???}"}

ARTIFACTS
 hemi_work/hemi_perm.json (sticker permutation + 6 gens)
 hemi_work/hemi_dense.json (504 dense generators + expansions + target)
 hemi_work/hemi_dense_word.py (Sage/libgap word extraction)
 hemi_work/hemi_final.json (833-move solution)
 /tmp/hemi_expand.py, /tmp/hemi_submit.py (expand+verify, submit)
