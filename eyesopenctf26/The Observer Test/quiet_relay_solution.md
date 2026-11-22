# Solution — ptrace/RDTSC anti-debugging gates + XOR flag decode

## Encoding parameters
- Operation: `xor_rotating`
- Key length: 4
- Keys: `['0xc7', '0x4a', '0x9e', '0x31']`

## Extraction (Python)
```python
from itertools import cycle
keys = ['0xc7', '0x4a', '0x9e', '0x31']
# Read cipher bytes from .rodata (radare2: px @ obj._cipher)
cipher = bytes([...]) # replace with actual cipher bytes
flag = bytes(c ^ k for c, k in zip(cipher, cycle(keys)))
print(flag.decode)
```

## Full analysis path
1. Run `strace ./challenge` → `ptrace(PTRACE_TRACEME, ...)` call detected immediately
2. radare2: `aaa; pdf @ sym.main` → spot call to `_is_debugged` + jnz exit branch
3. Static bypass: locate the `jnz` after `_is_debugged` and NOP it (2 bytes: 0x74/0x75 → 0x90 0x90)
4. Dynamic bypass: `LD_PRELOAD` a shared lib that overrides `ptrace` to always return 0
5. Once inside: `pdf @ sym.check` → standard XOR loop, extract `_cipher[]` XOR `_keys[i%4]`