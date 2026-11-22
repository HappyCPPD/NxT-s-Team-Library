# RESULT - d4rkm0n r3d

STATUS: SOLVED

FLAG:
d4rk{l3t_th3_cr3d1ts_r0ll_HELLLL_Y3AHHHH}

Verification: static decryption only. The ROM was not played to the credits in an emulator.

## MECHANISM

1. `game.gbc` is a rebuilt Pokemon Red (UE). Plain `strings`, charset-decoded text dumps and
 single-byte xor/add searches for `d4rk` found nothing.
2. Built a clean reference from `pret/pokered` with rgbds 1.0.4. Its SHA-1 is
 `ea9bcae617fdf159b045185467ae58b2e4a48b9a` (the known-good Red ROM).
3. Byte diff: 24 differing ranges. All but one are pointer fix-ups caused by a single
 0xDF-byte insert in bank 0x1D, inside `Credits.showTheEnd` (`TheEndTextString` moved
 from 1d:4229 to 1d:4308).
4. The insert adds a routine at 1d:4232 (file 0x74232), called right after "THE END" is drawn:
 - `CopyVideoData` 3 tiles from 1d:42d8 to $97A0 -> custom glyphs for tile ids
 0x7A `_`, 0x7B `{`, 0x7C `}` (not in the stock charset).
 - copies a 32-byte key from 1d:42b8 to $D002.
 - loop, c = 0..43: `[$D030+c] = [$428C+c] ^ [$D002 + (c & 31)] ^ c`.
 - `FillMiddleOfScreenWithWhite`, then `PlaceString` of $D030 at $C405.
5. Reproducing the loop offline:

```
$ python3 -I d4rkm0n-r3d-solve.py game.gbc
raw : a3fab1aa7babf9b37ab3a7f97aa2b1f9a3f74eb3b27ab1f6abab7a87848b8b8b8b7a98f9804e878787877c50
flag: d4rk{l3t_th3_cr3d1ts_r0ll_HELLLL_Y3AHHHH}
```

 The two 0x4E bytes (after `cr3d1` and `Y3A`) are on-screen line breaks and 0x50 is the
 string terminator; both are dropped from the flag.

Intended route is presumably beating the Elite Four and watching the credits.

## ARTIFACTS

- `d4rkm0n-r3d-solve.py` - decrypt script (reads `game.gbc`)
- Reference build (pokered checkout, rgbds, `pokered.gbc`) lived in a session scratchpad and
 is not kept here; rebuild with `make` in a `pret/pokered` clone to redo the diff.
