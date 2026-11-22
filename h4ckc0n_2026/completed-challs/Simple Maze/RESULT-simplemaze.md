# RESULT — Simple Maze (Misc, 100 pts, 293 solves)

**STATUS: SOLVED (corrected)**

**FLAG: `d4rk{how_was_the_maze}`**

## MECHANISM
`d4rkmaze.png` is a perfect maze whose unique solution path traces block letters.
The prior solve rendered the path correctly (see simplemaze_work/path_solid.png) but
MISREAD the glyphs as "HOLLOWS THE MAZE". Re-reading the rendered solid path and
zooming the ambiguous groups:

- Full path reads: `D4RK HOW WAS THE MAZE`
- zcheck_how.png -> "H O W" (O is a closed box, not Q)
- zcheck_maze.png -> "...A Z E" (final word MAZE)

The earlier "HOLLOWS" was the collapse of the two words "HOW WAS" into one.
Spaces -> underscores inside the flag braces.

## ARTIFACTS
- simplemaze_work/path_solid.png (solved path, letters legible)
- simplemaze_work/zcheck_how.png, simplemaze_work/zcheck_maze.png (zoom confirmations)
