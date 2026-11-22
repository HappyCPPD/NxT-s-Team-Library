# Simple Maze

_TODO_

---

## SOLVED — `d4rk{hollows_the_maze}`

**Misc, 100 pts, 293 solves.** Handout: `d4rkmaze.png` (3120×507 RGB).

### TL;DR
The maze is a **perfect maze** (9546 cells, 9545 open passages, one connected
component → the path is unique). Solving it and drawing the solution path shows
that **the path itself traces block letters**: `D4RK HOLLOWS THE MAZE`.
The text under the image gives the flag format
(`d4rk{...}`, words joined by `_`, per the example `` `d4rk hello world` is
`d4rk{hello_world}` ``), giving:

```
d4rk{hollows_the_maze}
```

### How
1. **Grid:** threshold `gray<128`; grid lines at `x = 11+12k` (258 cols) and
 `y = 11+12k` (37 rows) → 12 px cells. Maze body 258×37.
2. **Walls:** sample 7 px along each 12-px edge at the grid line; wall if ≥50 %
 dark → `H` (north edges) / `V` (west edges).
3. **Ends:** border openings are only at bottom col 0 (`START`) and bottom
 col 257 (`FINISH`).
4. **Solve:** BFS (row 36, col 0) → (row 36, col 257) = **2235 moves**.
 Edge count == nodes−1 ⇒ spanning tree ⇒ this path is *the* path.
5. **Read:** render the cell-centre polyline without walls → letters
 `D4RK HOLLOWS THE MAZE` (verified with per-word zoom crops).
6. **Format:** first word `d4rk` = prefix, rest lower-cased + `_`-joined.

### Case note
The in-image hint is self-inconsistent: the regex `d4rk{^[A-Z]+$}` says
uppercase, the example is lowercase. Chose **lowercase** because the example is
the concrete input→output rule and every other flag in this event is lowercase
(`d4rk{quantum_echo_reuse_breaks_the_pad}`, `d4rk{movie1_movie2_movie3}`); the
`[A-Z]+` most likely describes the uppercase block letters the maze is drawn in.
Uppercase variant would be `d4rk{HOLLOWS_THE_MAZE}`. No submission available
(event over) to disambiguate.

### Proof artifacts
`simplemaze_work/path_overlay.png` (path in red over the maze),
`simplemaze_work/path_solid.png` (thickened path = readable text),
`simplemaze_work/path_seg0..4.png`, `word_w1..w4.png`,
`simplemaze_work/dirs.txt` (2235-move direction string),
`simplemaze_work/parse.py` + `solve.py`.
Full detail: `RESULT-simplemaze.md`.
