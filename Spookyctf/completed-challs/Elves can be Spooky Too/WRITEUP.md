# Elves can be Spooky Too

**Category:** pwn/rev | **Flag:** `spooky{phdr_in_ehdr_c2d021cc4fc5}`

## Approach
The service demanded an x86-64 ELF that prints its own exact bytes to stdout and exits 0, within a 112-byte limit — impossible for a textbook ELF. The trick: overlap the program header inside the ELF header.

- ELF64 header is 64 bytes; a PT_LOAD phdr is 56 bytes → 120 bytes minimum, over budget.
- Set `e_phoff = 56` so the phdr starts inside the header. The phdr's `p_type`/`p_flags` are read from `e_phnum`/`e_shentsize`/`e_shnum`/`e_shstrndx` bytes, giving PT_LOAD (1) and R|X (5).
- Code lives in the ignored `e_shoff`/`e_flags`/`e_ehsize` bytes at offsets 40–51, with a short jump into the ignored `p_paddr` field at 80–87.
- The code performs `write(1, 0x400000, 112)` then `exit(0)` — a self-printing quine.

## Reproduction
```bash
python3 build_tiny64.py # emits 112-byte ELF
./tiny64 > out.bin && cmp out.bin tiny64 # byte-identical, exit 0
```
Server response: "PASS exact quine, exit 0, 112 bytes".
