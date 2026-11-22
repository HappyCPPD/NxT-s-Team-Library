# CoilVM — MetaCTF September 2026 Flash CTF

## Challenge

> Something inside the coil watches every choice you feed it, tightening or slackening in response before it lets the next test through. Rush it and it forgets nothing kindly. Wind it just right, all the way to the end, and it finally lets go of what it's been holding.

We get a single stripped x86-64 ELF binary called `coilvm`.

## Triage

```
$ file coilvm
coilvm: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), dynamically linked, stripped

$ strings coilvm | grep -i c01l
C01L_VM_d3c0y_d0_n0t_b3l13v3_th15_str1ng

$ echo test | ./coilvm
nope
```

The decoy string is a red herring (it even tells us so). The binary reads input from stdin and prints either `nope` or a decrypted flag.

## Reverse Engineering

### Architecture overview

The binary implements a custom virtual machine using **SIGTRAP signals** as its execution engine. The "coil" is a chain of 36 `int3` (0xCC) instructions interleaved with self-modifying XOR blocks. Each `int3` triggers a SIGTRAP handler that processes one byte of input.

### Main function (0x401631)

Main does four things:

1. **Make the code writable** — calls `mprotect` with RWX on the page containing the int3 chain
2. **Init phase** — sets a flag, runs the int3 chain once to record all 36 fault addresses into an array
3. **Read input** — reads exactly 36 bytes from stdin into a buffer at `0x404200`
4. **Verify phase** — initializes FNV-1a hash state to `0x811c9dc5`, clears a fail flag, and runs the int3 chain again

After verification, if the fail flag is clear and all 36 positions were checked, it decrypts and prints the flag. Otherwise it prints `nope`.

### The SIGTRAP handler (0x401196)

The handler receives the faulting context via `ucontext_t` and extracts the RIP (instruction pointer at the fault). It operates in two modes based on a global flag:

**Init mode:** Simply stores each fault RIP into an array (36 entries at `0x4040c0`).

**Verify mode:** This is where input checking happens.

1. **Anti-debug timing check** — uses `rdtsc` to measure cycles since the last trap. If the delta exceeds `0x4000000` (~67M cycles, indicating a debugger), the hash is corrupted with `XOR 0xa5a5a5a5` before proceeding. The challenge description's "rush it and it forgets nothing kindly" hints at this.

2. **RIP lookup** — searches the init-phase array for the current fault RIP. The found index becomes the step number (0–35), identifying which input byte to check.

3. **Byte verification** — for step `i` with current hash `h`:
 ```
 expected = (h & 0xFF) ^ verify_table[i]
 check: rol8((h & 0xFF) ^ input[i], (h >> 5) & 7) == expected
 ```
 If the check fails, the fail flag is set (but execution continues — every byte is still processed).

4. **Hash update** — FNV-1a: `h = (h ^ input[i]) * 0x1000193`

5. **Self-modification** — computes `(new_hash & 0x7F) ^ 0x90` and writes it to the byte at `0x404050`, which the XOR blocks between int3 instructions use to mutate an accumulator. This doesn't affect verification but makes static analysis harder.

### Decryption (0x401797)

When all 36 bytes pass, the final hash value seeds a decryption loop that produces a 47-byte output string. For each output position `d` (0–46):

```python
idx1 = d % 36
h = (h ^ input[idx1]) * FNV_PRIME # continue FNV-1a

idx2 = (1 + 5*d) % 36 # stride-5 permutation
rotated = rol8(input[idx2], (h >> 7) & 7)

output[d] = ((h >> 11) & 0xFF) ^ decrypt_table[d] ^ (d & 0xFF) ^ rotated
```

The flag is longer than the input because:
- The input bytes are reused cyclically (`% 36`)
- The FNV hash provides additional entropy for decryption
- The stride-5 index (`1, 6, 11, ...`) scrambles which input bytes contribute to rotation

## Solution

Since the hash is deterministic and each byte is checked sequentially, we can solve forward: at each step, the hash state is known, so we can algebraically invert the verification check to recover the input byte.

```python
def ror8(val, n):
 n &= 7
 return ((val >> n) | (val << (8 - n))) & 0xff

verify_table = bytes([
 0x2f, 0x3b, 0xb3, 0x3a, 0xb6, 0x86, 0x9a, 0xd7,
 0xbf, 0xa0, 0x74, 0x61, 0x1b, 0x0f, 0xa2, 0x06,
 0xec, 0xe4, 0xc3, 0x8f, 0x79, 0x38, 0x40, 0xcf,
 0x9c, 0x0f, 0xb7, 0x14, 0x95, 0xb4, 0x65, 0xee,
 0x9e, 0x74, 0x0c, 0x35
])

hash_val = 0x811c9dc5
input_bytes = []

for step in range(36):
 h_lo = hash_val & 0xff
 rot = (hash_val >> 5) & 7
 expected = h_lo ^ verify_table[step]
 input_byte = h_lo ^ ror8(expected, rot)
 input_bytes.append(input_byte)
 hash_val = ((hash_val ^ input_byte) * 0x1000193) & 0xFFFFFFFF
```

```
$ printf 'n4nom1tes_eat_y0ur_symb0lic_execut0r' | ./coilvm
SkillBit{n4nom1tes_eat_y0ur_symb0lic_execut0r}
```

## Flag

```
SkillBit{n4nom1tes_eat_y0ur_symb0lic_execut0r}
```
