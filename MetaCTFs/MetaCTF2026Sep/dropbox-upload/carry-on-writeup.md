# Carry On

**Category:** Forensics / Steganography 
**Flag:** `SkillBit{0n3_f1l3_c4n_c4rry_4n0th3r}`

## Challenge

We're given a PNG image (`checkpoint-plan.png`) of a security screening hall layout. The flavor text says the file is "heavier than the picture it shows" — hinting at hidden data appended to the image.

## Solution

Checking the end of the file with `xxd` reveals a ZIP archive appended after the PNG's IEND chunk:

```
$ xxd checkpoint-plan.png | tail -5
...
0000fe40: 4b01 0214 0314 0000 0008 0000 bd37 5d3b K............7];
...
0000fe70: 652e 7478 7450 4b05 0600 0000 0001 0001 e.txtPK.........
```

The `PK` magic bytes and the filename `note.txt` are clearly visible. Since ZIP readers scan from the end of a file, the PNG opens normally in image viewers while tools like `unzip` see a valid archive:

```
$ unzip checkpoint-plan.png
Archive: checkpoint-plan.png
 inflating: note.txt
```

The extracted `note.txt` is a shift-handover memo for a security checkpoint. Buried in the operational notes is the flag, disguised as a diagnostic recovery key:

```
The recovery key is SkillBit{0n3_f1l3_c4n_c4rry_4n0th3r}
```

## Flag

```
SkillBit{0n3_f1l3_c4n_c4rry_4n0th3r}
```
