# Challenge

**Category:** REV | **Difficulty:** MEDIUM

## Scenario
A suspicious process crashes immediately under a debugger. It appears to run a self-check before processing any input. Bypass the integrity guard and recover the embedded token.

> **Note:** The binary implements anti-debugging gates.
> Running it directly under GDB/strace will trigger the integrity check.
> You must bypass or disable the anti-debug checks before analysing the flag logic.

## Recommended tools
- `strace ./challenge`
- `radare2 (aaa; pdf @ sym.main)`
- `ltrace`
- `python3 (LD_PRELOAD bypass or static NOP patch)`

## Files
| File | Description |
|------|-------------|
| `challenge` | ELF binary (x86_64) — static analysis target |
