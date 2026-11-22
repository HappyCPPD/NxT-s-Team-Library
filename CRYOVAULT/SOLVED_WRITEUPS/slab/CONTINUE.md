# SLAB — CONTINUE (SUPERSEDED — the challenge is SOLVED; see HANDOFF.md / WRITEUP.md)
# Kept for the record: this was the resume brief written before the solve. The stack-scan
# path below was a dead end; the flag came from hijacking report's function pointer.


Challenge: `slab` (CRYOVAULT/ISFCR 2026, NotKnox). Target `nc 0.cloud.chals.io 20535`.
Flag `isfcr{...}`. Binary NOT provided — black-box only. Last earlier work session
`d8504d14-d43f-4b45-bbb4-07072faf4c51` died on the account session limit mid-scan.

## Primitive (CONFIRMED, working)

Index parsing mismatch gives arbitrary OOB read/write at note granularity:

- bounds check uses `atoi` -> `atoi("0x10") == 0` (passes)
- array access uses `strtol(...,0)` -> `strtol("0x10") == 16` (index 16)

So `read 0x10`, `read -0x1` hit past/before the notes array. Note i lives at
`SLOTS + 96*i` where `SLOTS = 0x4b6b00` (non-PIE). Reads/writes are 96-byte aligned only.

`fastread.py` in this dir implements the fast arbitrary-read path:
- `FR` connects, sets up slots, writes `SLOTS^KEY` (`KEY=0x618d5153e0045e29`)
 into slot 0, reallocs so note1 aliases the writer.
- `FR.read11([addr,...])` returns the 96-byte window at up to 11 addresses per
 connection ("edit 1 <12 pointers>" then `read u`), ~0.28s/read. `None` on failure.
- Reconnect on EOFError. Long *background* runs stall — server throttles; run
 foreground single-connection chunks.

## What the last session established (the lead to finish)

- Read the ELF program headers at 0x400000 to get exact segments:
 `.text` 0x400000–0x4867fd, `.rodata` 0x487000–0x4afbf0, `.data/.bss` 0x4b09c8–0x4bd1e8.
- User code references a tight rodata pointer cluster 0x487228–0x4872e2. Dumped it and
 found the key string **`flag.txt`** at **0x4872d4** (alongside `[chall] slab on
 127.0.0.1:%d`, `arena full`, `idx %d`).
- The code that references it does `read(fd, rsp, 0xa0)` into a **stack buffer**
 (site at 0x402307). So the flag content should sit on the process/main stack.
- Stack pointers leak at 0x4b6a20/0x4b6a28 (e.g. `0x7fff6394bf7c`) — glibc's saved
 argv/envp strings near the top of the stack.
- Already ruled out: argv/envp environment (just PATH/HOSTNAME/TERM/HOME, no FLAG=),
 BSS after the notes globals (zeros), `.data` (pointer tables), glibc rodata,
 "full used stack" (claimed no hit).

## Next steps (in order)

1. **Re-derive the exact stack buffer address rather than blind range scans.**
 Read the code around 0x402307 and the enclosing function; note whether the read
 happens in `main` *before* the fork/accept loop or per-connection. If before the
 fork, every child inherits the flag bytes at a *fixed* offset from the leaked
 argv/envp pointer — read that offset directly instead of scanning.
2. **Fix the alignment blind spot.** `read11` only returns 96-byte-aligned windows;
 a ~40-byte `isfcr{...}` string straddling a window boundary is missed. If the flag
 truly is on the stack, probe at a byte-shifted view too (shift the notes base via
 the writer slot, then re-scan) so no string can hide on a boundary.
3. When the byte offset of the flag buffer (relative to the leaked stack pointer) is
 known, just read `rsp` and the next ~0x100 bytes and grep for `isfcr`.
4. Fallbacks if the stack is genuinely empty: dump the `.rodata` window at
 0x487000–0x488000 (smallest) and then the whole .rodata in one connection; check
 whether a compiled-in default flag string exists (the read may be a decoy).

## Files

- `fastread.py` — the arbitrary-read engine (use this, it works).
- `scanrange.py`, `fscan.py`, `fast.py`, `rscan.py`, `scan2mem.py`, `stackleak.py` —
 scan/probe variants around the same primitive.
- `HANDOFF.md` — full state; `WRITEUP.md` — session-1 narrative (some claims debunked).

## Rules

- Black-box; do not assume a binary exists locally.
- Run scans in the FOREGROUND in single-connection chunks; background runs stall.
- One clean execution shot — converge, don't shotgun dozens of scripts.
