# RESULT — return by d34th (Rev, 300 pts, 246 solves)

STATUS: SOLVED

FLAG: d4rk{r3turn_0f_r3m_40}

## Inputs the binary wants
- `argv[1]` (TRACKING_ID) = `woah_a_rezero_mystery` — hardcoded `VALID_TRACKING` in the binary.
- `Recovery code>` (stdin, 16 chars) = `4312324114232134` — the unique 4x4 lattice.

## MECHANISM

`parcel_delivery.exe` is a PE32+ built by MinGW-w64 g++ 16.1.0 and **ships full DWARF
debug info**, so function names survive. `objdump -d --demangle` gives:

```
1400014b0 verify_line(unsigned char, unsigned char, unsigned char, unsigned char)
140001568 check_lattice(std::string const&)
14000181f handle_death(int)
1400018f3 main
140001b64 __tcf_ZL14VALID_TRACKING (dtor of VALID_TRACKING)
140001b82 __tcf_ZL13RE_ZERO_FACTS
```

### 1. Tracking ID (`main` @ 0x1400018f3)
`main` builds a `std::string` from `argv[1]` and compares it to the global
`VALID_TRACKING` (`std::operator!=`, 0x140004520). The string literal lives at
`.rdata` 0x140006741:

```
$ python3 -c "d=open('parcel_delivery.exe','rb').read;print(d[0x3e00+(0x140006741-0x140006000):][:32])"
b'woah_a_rezero_mystery\x00...'
```

→ TRACKING_ID = `woah_a_rezero_mystery` (this is the invoice tracking ID from the
"Love is a secret key" web challenge; the binary is authoritative — it is the exact
literal it compares against).

### 2. The "lattice" (Recovery code) — `check_lattice` @ 0x140001568
- Input must be **length 16**, every char in `'0'..'4'`.
- 4 cells are pinned by `sudoku[]` (`std::array<unsigned char,16>` @ .rdata 0x140006000)
 XORed with `DEATH_KEY` (`__static_initialization_and_destruction_0` sets
 `DEATH_KEY = RE_ZERO_FACTS.size & 0xff`; the RE_ZERO_FACTS table holds **40**
 Re:Zero trivia strings ⇒ `DEATH_KEY = 0x28`):

 ```asm
 140001634: movzbl DEATH_KEY,%eax
 14000163b: xor %edx,%eax ; sudoku[i] ^ DEATH_KEY
 14000163d: not %eax
 14000163f: mov %al,-0x21(%rbp) ; t
 140001642: cmpb $0x0,-0x21(%rbp)
 140001646: je skip ; t==0 -> cell unconstrained
 ... cmp %eax,%edx ; else input[i]-'0' must == t
 ```

 `sudoku = d7 d7 d6 d7 d7 d7 d7 d7 d7 d3 d7 d4 d7 d7 d7 d3` ⇒
 forced cells `{2:'1', 9:'4', 11:'3', 15:'4'}` (all other bytes XOR to 0xff ⇒ unconstrained).

- Every **row** and every **column** of the 4x4 grid must satisfy `verify_line`
 (0x1400014b0): `a+b+c+d == 10`, `a*b*c*d == 24`, `a²+b²+c²+d² == 30`.
 That uniquely characterises the multiset `{1,2,3,4}` ⇒ the grid must be a 4x4
 Latin square on digits 1–4.

 With the 4 forced cells, brute force gives **exactly one** solution:
 ```
 lattice (Recovery code): 4312324114232134
 ```

### 3. Flag derivation (`main` @ 0x140001a7c)
On a valid lattice, `main` prints `FLAG: d4rk{`, then for i in 0..15 prints
`ENCRYPTED_INNER[i] ^ input[i]` as a char, then `}`:

```asm
140001a80: lea ENCRYPTED_INNER,%rcx ; .rdata 0x140006010
140001a8f: movzbl (%rax),%eax ; enc[i]
140001a9f: call std::string::operator[] ; input[i] (ASCII digit)
140001aa7: xor %ebx,%eax ; enc[i] ^ input[i]
140001ab6: call operator<<(ostream&, char)
```

`ENCRYPTED_INNER = 46 00 45 47 41 5c 6b 01 57 6b 40 00 5f 6e 07 04`
XOR `4312324114232134` (ASCII) ⇒ `r3turn_0f_r3m_40`.

## PROOF — real run under Wine
Needed MinGW runtime DLLs (pulled from Ubuntu `gcc-mingw-w64-x86-64-posix-runtime`
and `mingw-w64-x86-64-dev`, placed next to the exe): `libgcc_s_seh-1.dll`,
`libstdc++-6.dll`, `libwinpthread-1.dll`.

```
$ printf '4312324114232134\n' | wine parcel_delivery.exe woah_a_rezero_mystery
[+] Tracking verified: woah_a_rezero_mystery
Recovery code>
[★] The lattice glows. The memories return...
FLAG: d4rk{r3turn_0f_r3m_40}
```
(full output saved in `wine_run.txt`, exit code 0)

The checker also accepts an empty `Recovery code>` on EOF with no flag, and a wrong
ID prints "The parcel scanner does not recognise that tracking ID." — matching the
disassembly.

## VERIFICATION (ad-hoc, not a test suite)
A throwaway harness (`<verification script>`, since deleted)
re-derived everything **without reusing `solve_lattice.py` constants**: it walked the real
PE section table to find `.rdata`, read `ENCRYPTED_INNER` / `sudoku` / `VALID_TRACKING`
from the file, counted `RE_ZERO_FACTS` literals in the binary to get `DEATH_KEY = 40`,
brute-forced the Latin square independently, then executed the exe under Wine. Result:

```
TRACK='woah_a_rezero_mystery' ENC=46004547415c6b01576b40005f6e0704 SUD=d7d7d6d7d7d7d7d7d7d3d7d4d7d7d7d3 DEATH_KEY=40 (40 facts)
forced: {2: 1, 9: 4, 11: 3, 15: 4}
lattice=4312324114232134 derived FLAG=d4rk{r3turn_0f_r3m_40}
wine stdout: [+] Tracking verified: woah_a_rezero_mystery | Recovery code> | [★] The lattice glows. The memories return... | FLAG: d4rk{r3turn_0f_r3m_40}
VERIFIED: static derivation == wine run == expected flag (wine exit 0)
```

Three independent routes agree: static byte derivation, `solve_lattice.py`, and the live
Wine execution.

## ARTIFACTS
- `solve_lattice.py` — reconstructs lattice + flag from the static bytes
- `disasm.txt` — `objdump -d --demangle` of the whole binary
- `wine_run.txt` — captured Wine run printing the flag
- `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, `libwinpthread-1.dll` — MinGW runtime needed to run the exe

## NOTES
- The web challenge `/love/track` takes `username` + `order_id` and issues a tracking
 ID; the binary hardcodes the expected value, so no web exploitation was required
 here (that chain belongs to the "Love is a secret key" challenge).
- Flag format matches the brief's exception note: `d4rk{...}`.
