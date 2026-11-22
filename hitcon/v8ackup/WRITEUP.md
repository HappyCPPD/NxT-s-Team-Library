# v8ackup (HITCON CTF) — technical writeup [IN PROGRESS — no flag yet]

Status: exploit chain fully proven under gdb; live win not yet obtained.
Local flag is `hitcon{TEST_ME}`; remote flag not yet retrieved.

## Challenge

`d8` (V8 10.2.154.26 + `v8.diff`) run under `V8ACKUP_CHALLENGE=1`. The patch adds
to the d8 global object `store(name)`, `use(name)`, `show` backed by a sqlite3
file (`/data/store.sqlite`, persisted across connections). Each connection is a
fresh d8 process (xinetd), 180 s wall clock, `--jitless`
(so no JIT/WASM RWX — must ROP/execve).

- `store(name)`: serialize the named global (structured-clone) and delete it.
 One-byte strings are stored as sqlite TEXT (via `sqlite3_bind_text`), everything
 else via `v8::ValueSerializer` (BLOB), `kind=0` text / `kind=1` value.
 `recorded_size = value.size`, ≤ 2048.
- `use(name)`: kind=1 → `ValueDeserializer`; kind=0 → external one-byte string:
 `buffer = new char[stored_size]; resource = new EntryResource(buffer,
 recorded_size); ... memcpy(buffer, payload, count); NewExternalOneByte(resource)`.

## Bug 1 — deterministic OOB read

`store` builds the TEXT value with `WriteOneByte(..., NO_NULL_TERMINATION)` so
`recorded_size` = the full JS string length, but sqlite's `quote` truncates the
stored text at the first NUL, so `stored_size = length(CAST(data AS BLOB))` = the
pre-NUL prefix. `use` then makes an external string of length `recorded_size`
backed by a `stored_size` buffer → `charCodeAt` reads up to `recorded_size -
stored_size` bytes past the chunk. Fully deterministic, ~2048 bytes, repeatable.

## Bug 2 — OOB write (race)

`use` opens **two** sqlite connections; `buffer` and `resource` are allocated
*between* query1 (`recorded_size, length(data), kind`) and query2 (`data`, whose
length is `count`). A second JS process flipping the row between the two queries
makes `count > stored_size`, so `memcpy(buffer, payload, count)` overflows the
`stored_size`-sized buffer. `count ≤ 2048`.

## Exploit chain (all verified in gdb)

1. Leak `d8` base (a real string vtable, low-12 = `0xcc8`) and `libc` base from
 the deterministic OOB read window; leak a controlled `Uint8Array` backing
 store address (`TAB`) via the same window. `libc` gives `setcontext = +0x40fe0`
 and `execve = +0xd4ad0`.
2. Build a payload into `TAB`: a fake vtable `V` (slot **+0x38 = setcontext**),
 `/readflag\0TEST\0ME\0` + argv, an fpstate, and a ucontext frame; and a
 collision-free lattice of frames inside the overflowed buffer.
3. Race the overflow so an `EntryResource`'s `vptr` becomes `V`; then
 `NewExternalOneByte` executes `mov 0x38(%rax),%rax; mov %rsi,%rdi; call *%rax`
 → `setcontext(rdi=resource)` → `execve("/readflag",["/readflag","TEST","ME"],0)`
 → flag.

**Verified**: a gdb injection that overwrites the resource at the breakpoint made
d8 print `process ... is executing new program: /readflag`.

## EntryResource / dispatch facts (measured)

```
res+0x00 = vptr (d8+0xdc2cc8) res+0x18 = size_ (= recorded_size)
res+0x08 = 0 res+0x10 = bytes_ (char* buffer)
D = resource - buffer (buffer chunk = align(stored_size+8,16))
dispatch: d8+0xf57a4 `mov 0x38(%rax),%rax` ; d8+0xf5858 `mov %rsi,%rdi; call *%rax`
ucontext fields for setcontext(res): rsp@+0xa0 rip@+0xa8 rdi@+0x68 rsi@+0x70
 rdx@+0x78 fpregs@+0xe0 mxcsr@+0x1c0
ValueSerializer `{key: Uint8Array}` header H = 0x10
```

## Blocker

`D` is **regime-stable** (D=0x70 held 545 consecutive calls; D=0x250 for 416;
D=0xc50 for 1514) but a random regime is often `0xc50` which is *unreachable* by
a ≤0x800 overflow (frame spans +0x1c0). The reachable modes (0x70 ~24%, 0x250
~11%) are covered by the current lattice, but the OOB window cannot reliably
identify the *current* call's resource (old resources look identical), so a
gate can't yet be trusted. See HANDOFF.md "THE REMAINING BLOCKER" for the
concrete next steps (unique per-call `recorded_size`; tcache drain to force
adjacency; stack-pivot gadget to shrink the frame).
