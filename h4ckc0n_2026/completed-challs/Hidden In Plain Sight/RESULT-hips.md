# RESULT - Hidden In Plain Sight (slug=hips)

STATUS: SOLVED

FLAG: d4rk{fediverse}

## MECHANISM

The artifact `What_Was_That.png` (1620x1620, 3 flat colours + 3 red dots) contains
NO embedded payload. Proof it is purely visual:

* `exiftool` -> only eXIf description/artist. `binwalk` -> PNG + eXIf + IDAT only.
 No bytes after IEND. `zsteg -a`, `steghide`, LSB bit-planes -> nothing.
* Exact reconstruction test: I rebuilt the image by pasting the canonical
 (digit, background-parity) tile into every cell. Residual = 5156 px, and ALL of
 them lie within 80 px of the red dots (script `work/hips_recon.py`). So the image
 is exactly: checkerboard + digit tiles + 3 red dots. Nothing else.

### What it actually is
A 9x9 grid that *looks* like a Sudoku but is not one (rows contain duplicates), placed
on a checkerboard. The real structure, verified in code:

1. Every 3x3 box contains exactly the digits 1..k (k = number of filled cells in
 that box), each once. e.g. box(1,1) = [1 . 5 / 2 . 4 / . 3 .] = {1,2,3,4,5}.
2. Inside a box the digits 1..k are laid out so that each consecutive pair (d, d+1)
 is one step apart -> the numbers are the **stroke order of a connect-the-dots letter**.

So each 3x3 box is one hand-drawn capital letter; the nine boxes spell the word.

### The rule from the author's hint
eXIf ImageDescription = `Don't Jump when their is the red, otherwise you should!`

* A **straight (orthogonal)** step between d and d+1 is always drawn.
* A **diagonal / jumping** step is *skipped* ("don't jump"),
 **except** when the segment between the two cell centres passes exactly through one
 of the three **red dots** – then it IS drawn ("otherwise you should").
* Red dots are at grid lattice points (x,y) = (4,5), (5,5), (2,8).

The three red dots are used as follows (this is what makes the reading unique):
* the 2→3 and 3→4 diagonals of the centre box pass through (4,5) and (5,5);
* the 7→8 diagonal of the bottom-left box passes through (2,8).

Without the red rule the letters would be F E O/O Z/U ... = nonsense; with it they are
F E D I V E R S E.

### The letters (connect-the-dots, left-to-right, top-to-bottom)
Read the 9 boxes row-major. ASCII rendering produced by `work/hips_ascii.py`
('#' = drawn stroke cell, 'o' = a visited point with no stroke):

```
box(0,0) k=7 box(0,1) k=9 box(0,2) k=8 box order -> letters row-major:
 ##### ##### # ###
 # # # #
 # ### # ### # . # F E D
 # # # #
 # . . ##### # ### I V E
 R S E
box(1,0) k=7 box(1,1) k=5 box(1,2) k=9
 ##### # . #
 # # => FEDIVERSE
 . o . # . # (same as box(0,1) = E)
 # # (red diagonals)
 ##### . # .
box(2,0) k=8 box(2,1) k=9 box(2,2) k=9
 # ### #####
 # # #
 # ### ##### (same as box(0,1) = E)
 # # (red diag) #
 # . # #####
```

Letters: F(box00) E(box01) D(box02) I(box10) V(box11) E(box12) R(box20) S(box21) E(box22)

=> **FEDIVERSE**

"Word is meaningful here" -> `fediverse` is a real English word. Flag: `d4rk{fediverse}`.

## HOW TO REPRODUCE
```
cd "Hidden In Plain Sight"
python3 work/hips_recon.py # proves only the red dots + digit tiles exist
python3 work/hips_ascii.py # prints the 9 letters as ASCII art -> FEDIVERSE
python3 work/hips_letters2.py # draws work/hips_letters_rule.png (letters; red = dot-diagonals)
```

## ARTIFACTS (all in ./work/, prefixed hips_)
* hips_recon.py / hips_residual2.png - proves no hidden data (residual == red dots)
* hips_ascii.py - ASCII rendering of the 9 connect-the-dots letters
* hips_letters2.py / hips_letters_rule.png - rendered letters with the red-dot rule
* hips_letters_final.png - annotated letters (stroke order numbers, red diagonals)
* hips_snakes.png, hips_boxpix.png - supporting visualisations of the 1..k snakes
* hips_mines.py, hips_fillapix*.py, hips_bits.py, hips_brute.py, hips_boggle.py,
 hips_jump.py, hips_poly.py, hips_lines.py, hips_path*.py, hips_sym.py, hips_mirror.py
 - negative results (rules out minesweeper / fill-a-pix / sudoku / bit encodings /
 letter-grid word search / jump-maze / polybius / etc.)

FLAG: d4rk{fediverse}
