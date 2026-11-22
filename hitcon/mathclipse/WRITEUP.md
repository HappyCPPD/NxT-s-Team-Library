# WRITEUP — HITCON CTF: `mathclipse`

> **Not yet solved.** This file is a placeholder. See `HANDOFF.md` for the full state of
> knowledge (primitive, reachable graph, call sites, ruled-out list, live leads).

## Summary (to fill in when solved)

- **Category:** misc
- **Flag:** *(unknown)*
- **Mechanism:** *(the single trick — 71 solves suggests a short/dumb swap we keep missing)*
- **Payload:**
 ```
 (exact JSON line)
 ```

## Notes

The challenge is a 2-slot **swap** primitive over the object graph reachable from the `math`
module (max 6 getattr/getitem steps per slot, `<= 19` total). Still holding two confirmed
landmarks — **shell exec** (`_io.open_code ↔ posix.system`, command always `<dir>/<name>.py[c]`) and
a **real file-reader** (`builtins['license']` `_Printer`, called by the storm; reads a path relative
to CWD=`/app`) — but neither lands on the flag inside budget.

See `HANDOFF.md` §6 (the exact gap) and **§11** (this session's deltas: the 10-step
`sys.getrecursionlimit` printer arm, two corrections to the module-set/printer-output claims, the
18,528-payload sweep that returned 0 hits, and the live `builtins['open']`→`tokenize` angle).
Earlier "leading candidates" (0-arg shutdown `sys.stdout.flush`, `sys.meta_path`) are now ruled out.
Reproducible scripts are snapshotted in `solve/`.
