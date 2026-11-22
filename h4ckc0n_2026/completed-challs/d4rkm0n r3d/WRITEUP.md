# d4rkm0n r3d

_TODO_

## Summary

Solved: `d4rk{l3t_th3_cr3d1ts_r0ll_HELLLL_Y3AHHHH}` (static decryption, not confirmed in an emulator).

The ROM is Pokemon Red rebuilt from the `pret/pokered` disassembly with one addition. Diffing
against a clean pokered build shows a 0xDF-byte insert in bank 0x1D, in the credits code after
"THE END". The new routine at file offset 0x74232 loads three custom font tiles (`_`, `{`, `}`),
then decrypts 44 bytes at 0x7428C with `out[i] = enc[i] ^ key[i & 31] ^ i` (32-byte key at
0x742B8) and prints the result with the game's `PlaceString`. The plaintext is in the game's
text charset rather than ASCII, so string searches miss it.

Details and proof output are in `RESULT-d4rkm0n-r3d.md`; the script is `d4rkm0n-r3d-solve.py`.
