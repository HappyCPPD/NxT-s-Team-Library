# Rachet

**Category:** reverse engineering
**Flag:** `SkillBit{st4t3_1s_th3_0n1y_k3y!}`

## The challenge

> The vault's dial turns one way only. Each click sets the next, and a single wrong turn means starting again from the first.
>
> The old keeper never wrote down the sequence, only the mechanism.

The zip drops a single file, `ratchet`, 14,472 bytes.

```
ratchet: ELF 64-bit LSB pie executable, x86-64, dynamically linked, stripped
```

Stripped, tiny, and the only two strings that matter are `wrong` and `correct`. Running it with anything gives `wrong`, so the answer is a 32-byte input it compares against something computed internally.

## Reading main

`objdump -d -M intel` on the entry point is short. main reads 0x40 bytes from stdin and then does two quick checks before it bothers calling anything:

```
call read@plt
cmp rax, 0x20 ; must read more than 32 bytes
jle wrong
cmp BYTE PTR [rsp+0x20], 0xa ; byte 32 must be '\n'
jne wrong
```

So the real payload is the first 32 bytes. After that main seeds state and walks a chain of 32 near-identical functions at 0x1310, 0x1360, 0x13a0 ... 0x1c00, threading one register through all of them:

```
mov edi, 0x243f6a88 ; initial carry
mov DWORD PTR [rip+...], 0x85a308d3 ; the "dial" in .data:0x4018
mov BYTE PTR [rip+...], 0x0 ; mismatch flag at .data:0x4014
call 0x1310
mov edi, eax ; each check's return feeds the next
call 0x1360
...
```

Both 0x243f6a88 and 0x85a308d3 are Blowfish pi digits. Flavor, not load-bearing.

## What one check does

Take the first one, 0x1310:

```
movzx edx, BYTE PTR [rsi] ; edx = input[0], also saved in cl
mov ecx, edx
xor edx, edi ; edx = input[0] ^ carry
mov eax, edx
shl eax, 0x7
shr edx, 0x19
or eax, edx ; rol32(input[0] ^ carry, 7)
add eax, 0x4f1bbcdc
add eax, 0x4f1bbcdd ; ... + 0x9e3779b9, split in two adds
mov edx, DWORD PTR [rip+..] ; edx = dial
shl edi, 0x15
shr edi, 0x18 ; edi = (carry >> 24) & 0xff -- part of next carry
xor edx, 0xac5c0ab9 ; dial ^= K_0
rol edx, 0x3 ; dial = rol32(dial, 3)
mov DWORD PTR [rip+..], edx ; store the new dial back
shr edx, 0xb ; edx = new_dial >> 11
xor edi, edx
cmp cl, dil ; input[0] == required byte?
je ok
mov BYTE PTR [rip+..], 0x1 ; else set mismatch flag at 0x4014
```

Two moving parts per step: a global dial that only ever rotates forward (`dial = rol32(dial ^ K_i, r_i)`), and a carry that starts as the previous check's return value. The byte the program wants at position i is computed from the carry going in and the freshly rotated dial, and it does not depend on the byte you supply. Get one byte wrong and the carry you thread into step i+1 is wrong, so every later comparison fails too. That is exactly the hint: the dial turns one way, one wrong click and you start over.

Across the 32 functions the constant rotation amount, the XOR key, the shift used to build the next carry, and the final XOR differ, and a few use `ror` or `cmp cl,dl` instead of `cmp cl,dil`. Transcribing 32 copies of that by hand and getting a shift direction wrong somewhere is the obvious way to waste an afternoon.

## Recovering the bytes

I stopped reading and emulated instead. Unicorn loads the ELF's PT_LOAD segments as-is, so the function bodies run for real and I never have to guess whether a step used `dl` or `dil`.

Per position I brute force all 256 candidates against the real code and keep the one that leaves the mismatch flag at 0x4014 clear. The dial has to be rewound to its saved value before each trial, because a losing candidate still advanced it. The winning run also hands back the correct next carry in eax.

```python
from unicorn import *
from unicorn.x86_const import *
from elftools.elf.elffile import ELFFile

BIN = "ratchet/ratchet"
elf = ELFFile(open(BIN, "rb"))

mu = Uc(UC_ARCH_X86, UC_MODE_64)
mu.mem_map(0x0, 0x10000, UC_PROT_ALL)
for seg in elf.iter_segments:
 if seg["p_type"] == "PT_LOAD":
 mu.mem_write(seg["p_vaddr"], seg.data)

STATE = 0x4018 # dial
FLAGB = 0x4014 # mismatch flag
BUF = 0x80000
mu.mem_map(0x80000, 0x1000, UC_PROT_ALL)
mu.mem_map(0x90000, 0x2000, UC_PROT_ALL)

FUNCS = [0x1310,0x1360,0x13a0,0x13e0,0x1420,0x1470,0x14c0,0x1510,0x1550,0x1590,
 0x15d0,0x1620,0x1670,0x16c0,0x1710,0x1760,0x17b0,0x1800,0x1850,0x1890,
 0x18d0,0x1920,0x1970,0x19b0,0x1a00,0x1a40,0x1a90,0x1ae0,0x1b20,0x1b60,
 0x1bb0,0x1c00]

mu.mem_write(STATE, (0x85a308d3).to_bytes(4, "little"))

def run(fn, edi, bufbytes):
 mu.mem_write(BUF, bytes(bufbytes))
 sp = 0x91000
 mu.reg_write(UC_X86_REG_RSP, sp)
 mu.mem_write(sp, (0x9f000).to_bytes(8, "little"))
 mu.reg_write(UC_X86_REG_RDI, edi & 0xffffffff)
 mu.reg_write(UC_X86_REG_RSI, BUF)
 try:
 mu.emu_start(fn, fn + 0x50, count=500)
 except UcError:
 pass
 return mu.reg_read(UC_X86_REG_EAX), mu.reg_read(UC_X86_REG_EDX)

edi = 0x243f6a88
out = bytearray
for i, fn in enumerate(FUNCS):
 st = mu.mem_read(STATE, 4)
 found = None
 for c in range(256):
 mu.mem_write(STATE, bytes(st))
 mu.mem_write(FLAGB, b"\x00")
 b = bytearray(out) + bytes([c]) + b"\x00" * (0x40 - len(out) - 1)
 eax, edx = run(fn, edi, b)
 if mu.mem_read(FLAGB, 1) == b"\x00":
 found = c
 good_eax = eax
 break
 assert found is not None, f"no byte for pos {i}"
 out.append(found)
 edi = good_eax & 0xffffffff

print("recovered:", bytes(out))
```

```
recovered bytes: b'SkillBit{st4t3_1s_th3_0n1y_k3y!}'
hex: 536b696c6c4269747b73743474335f31735f7468335f306e31795f6b3379217d
```

32 positions times 256 candidates is a few thousand emulated function bodies, done in well under a second.

## Checking it against the real binary

The recovered bytes came out printable, so the input is the flag. Running the actual binary confirms it, and flipping the last character confirms the check is real:

```
$ printf 'SkillBit{st4t3_1s_th3_0n1y_k3y!}\n' | ./ratchet
correct
$ printf 'SkillBit{st4t3_1s_th3_0n1y_k3y?}\n' | ./ratchet
wrong
```

## Notes

The state is the whole trick. Because the required byte at each position depends only on the carry and the dial, and the dial never rotates backwards, the comparisons are independent once you have the running state. You can peel the input off one byte at a time instead of solving 32 equations at once. The carry thread is what makes a wrong byte poison everything after it, which is what the ratchet metaphor is describing.
