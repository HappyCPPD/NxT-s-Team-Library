# The Vault Protocol

**Flag: `d4rk{s3cr3t_flll4ggg}`**

Rev, 200 pts — stripped non-PIE x86-64 C++ ELF `vault` (1.1 MB).
Prompts `Enter the flag: `, requires exactly 25 input bytes, then runs a
6-stage byte transform and compares against a hard-coded 25-byte target
(OR-reduction of all byte diffs → `Correct!` @0x40c570 / `Wrong.` @0x40c190).

Pipeline: `in --(^5-byte key i%5)--> b1 --f1..f6--> transformed == C`

- key (0x4d8bb0) = `5a c3 17 9e 2b`
- f1 (0x406300) rotl8(b[i], (i%7)+1)
- f2 (0x406480) running cumulative sum mod 256
- f3 (0x406500) permutation `out[(3+10k+7j)%25] = in[5k+j]`
- f4 (0x406a40) S-box substitution
- f5 (0x406640) reverse rolling `al=rol8(al,3)^b[i]; b[i]=al`
- f6 (0x4067c0) keystream xor `k0=0x54, k[i]=5*k[i-1]+0x11`
- C = `rodata[0x4d8a80:0x4d8a90] ‖ rodata[0x4d8bd8:0x4d8be0] ‖ 0x62`

Every stage is invertible, so C was inverted back to the flag.

**Decoys:** `f4` ships dead code (0x406ab9) that builds an identity+6-patch
S-box from rodata; the real table lives at `0x50e7e0` built by a global
constructor (one-shot guard byte at `0x50e7c0` is already 1). Using the rodata
table gives garbage. Also `not_the_A`, `d4rk{`, `H4CK-TH3-PL4N` etc. are
immediate-move fragments of dead strings in `.text`, not the flag.

Proof: `python3 vaultprotocol_solve.py` (forward validated against a live
gdb capture) prints the flag; `printf 'd4rk{s3cr3t_flll4ggg}c0de\n' | ./vault`
→ `Correct!` (exit 0), while a 1-char mutation → `Wrong.` (exit 1).

Full details + artifacts: `RESULT-vaultprotocol.md`.
