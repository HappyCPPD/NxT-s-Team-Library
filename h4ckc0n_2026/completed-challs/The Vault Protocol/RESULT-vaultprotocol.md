# RESULT — The Vault Protocol (Rev, 200 pts)

STATUS: SOLVED

FLAG: d4rk{s3cr3t_flll4ggg}

## MECHANISM

`vault` is a stripped x86-64 ELF (C++, dynamically linked, no PIE, .text at
0x402640). It prompts `Enter the flag: `, reads one line, and requires the
input to be **exactly 25 bytes** (`cmp [rsp+0xc8],0x19` @0x40bd80). The input is
then pushed through a 6-stage byte transform and compared against a hard-coded
25-byte target; a horizontal OR-reduction of all byte differences decides
`Correct!` (0x40c570) vs `Wrong.` (0x40c190).

### The check pipeline

```
in (25B) --[ xor K5[i%5] ]--> b1 --f1--> f2 --> f3 --> f4 --> f5 --> f6 --> transformed
compare: transformed[0..23] == C[0..23] && transformed[24]^0x62 == 0
```

* **XOR key** (5-byte, repeating, `i % 5`) at `0x4d8bb0` = `5a c3 17 9e 2b`
 (index computed by the compiler's `/5` magic 0xcccccccccccccccd).
* **f1** `0x406300` — `rotl8(byte_i, (i%7)+1)`
* **f2** `0x406480` — running cumulative sum mod 256 (`b[i] += b[i-1]`)
* **f3** `0x406500` — permutation: `out[(3 + 10k + 7j) % 25] = in[5k + j]`
* **f4** `0x406a40` — byte substitution (S-box) `out = SBOX[in]`
* **f5** `0x406640` — reverse rolling transform `al=rol8(al,3)^b[i]; b[i]=al`
* **f6** `0x4067c0` — keystream XOR, `k0=0x54`, `k[i]=5*k[i-1]+0x11` (mod 256)
* **Target C** = `rodata[0x4d8a80..0x4d8a90]` (16B) ‖ `rodata[0x4d8bd8..0x4d8be0]`
 (8B) ‖ `0x62` =
 `eb95045b560e2aae6a408360c9d52939 fe6deada9ea0e758 62`

### Two decoys worth noting

1. **Fake S-box code.** `f4` contains a block at `0x406ab9..0x406be6` that
 `movaps`-stores 256 bytes from rodata (`0x4d8980`, which is just the
 identity table `00 01 02 … ff`) into `0x50e7e0` and then patches 6 entries.
 That block is **dead**: it is guarded by a one-shot flag at `0x50e7c0`
 which a global constructor has already set to `1`, so execution jumps
 straight to the mapping loop. Using the rodata identity table yields
 garbage. The real S-box is built at load time by a constructor.
2. **Decoy strings in `.text`.** `not_the_A`, `d4rk{`, `flag`, `H4CK-TH3-PL4N`,
 `AAAA-BBBB-…` are immediate-move fragments of dead comparison strings, not
 the flag. `--verbose` / `--dump-debug` flags exist but only print
 `[vault] init ok` / `[vault] debug dump unavailable in this build`.

The real S-box was captured live (see artifacts) and is a bijection, so the
whole chain is invertible. Inverting C through `f6⁻¹…f1⁻¹` and then XORing the
5-byte key again gives the flag.

## PROOF

Forward implementation validated against a live gdb capture (input = 25×'A'):

```
$ python3 vaultprotocol_solve.py
[+] forward matches live gdb capture for 25*'A'
[+] EXPECT : eb95045b560e2aae6a408360c9d52939fe6deada9ea0e75862
[+] flag : d4rk{s3cr3t_flll4ggg}c0de
[+] roundtrip: True
[+] ascii : True
```

Live gdb capture used for validation (`AFTER_F6` = final transformed value):

```
AFTER_XOR 1b8256df6a1b8256df6a1b8256df6a1b8256df6a1b8256df6a # 'A' ^ K5
AFTER_F1 360ab2fd4dc641ac7f53b15095efd46c1465fb9a8d0559fea6
AFTER_F2 3640f2ef3c0243ef6ec172c257461a869afffa9421267f7d23
AFTER_F3 261aef36fac23c7f866e409457027d9ac1f221464323ff72ef
AFTER_F4 058cf47b13f7e2a40f9deab99134277a5cb32b5b612d58cdf4
AFTER_F5 9432d764e31e3dfbeb9c20591cb1b0f211a9430dca750b6af4
AFTER_F6 c0874d77935f6b44279172f274a83e2555cc494eaa84cd8548
```

The binary accepts the recovered flag (and rejects a one-character mutation):

```
$ printf 'd4rk{s3cr3t_flll4ggg}c0de\n' | ./vault
Enter the flag: Correct! # exit 0
$ printf 'd4rk{s3cr3t_flll4ggg}c0df\n' | ./vault
Enter the flag: Wrong. # exit 1
```

## ARTIFACTS

| file | purpose |
| --- | --- |
| `vaultprotocol_solve.py` | forward + inverse pipeline, prints the flag (self-checks vs gdb capture) |
| `vaultprotocol_dump_transforms.gdb` | gdb script dumping every intermediate stage for input 25×'A' |
| `vaultprotocol_dump_sbox.gdb` | gdb script dumping the real 256-byte S-box at `0x50e7e0` |
| `vaultprotocol_output.txt` | captured solver output |
| `vaultprotocol_run.txt` | captured binary runs (Correct! / Wrong.) |

Reproduce: `cd "The Vault Protocol" && python3 vaultprotocol_solve.py`
