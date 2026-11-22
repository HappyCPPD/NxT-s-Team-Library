# Omnitrix — SESSION 13 (2026-09-20) — ★ SOLVED ★ flag captured; the 12-session blocker was probe bugs, not the challenge

## FLAG
```
TISC{6r33n_n33dl3_0r_br41n5t0rm??}
```
Artifact: **`/congratulationsyougottheflag`** — mode `0111`, size `682696`, static stripped
ET_EXEC (exactly what the Dockerfile builds: `gcc -O2 -static -s -DFLAG=... /flag.c -o /flag.bin`,
`chmod 0111`, then `COPY --from=builder /flag.bin $FLAG_FILEPATH`).

Retrieved **twice**, on two live instances, same flag both times.

## The retraction (read this first)
`session12/README-SESSION12.md` concluded *"the flag artifact is very likely a **shared object to
dlopen**"*, because the live probe reported *"/ entries: lib64 and little else"* and *"no top-level
name contains 'flag'"*. **Both statements were artifacts of buggy probe code, not facts.** The flag
was a plain executable sitting at the root the whole time, and `wprobe2`'s own `has_flag_word`
would have matched it (`congratulationsyougottheflag` contains "flag").

## Root causes — three bugs in the enumeration probe
All three were in `wprobe2.c` (the "authoritative live recon" tool) and all three are fixed in
`wprobe3.c`:

1. **`static char DENTBUF[8192]` shared across recursive calls.** `list_dir` recursed *while still
 iterating* its `getdents64` buffer, so the child clobbered the parent's buffer mid-loop. Result:
 a truncated/garbled listing (locally reproduced: the walk stopped after the first subdirectory and
 emitted phantom paths). → this is the true origin of "lib64 and little else".
 **Fix:** `getdents64` buffer is now a per-invocation local.
2. **`wait4` called through the 3-arg syscall helper.** `wait4(pid,status,options,rusage)` needs
 `r10` set; the helper left a stale `r10`, so the kernel wrote a 144-byte `rusage` struct through a
 garbage pointer → memory corruption (locally reproduced: the relayed `OUTTXT`/`OUTHEX` came back as
 binary garbage while the length looked sane). Any "the probe relayed garbage" observation from
 sessions 12 was this.
 **Fix:** proper 4-arg helper `sc4` with a `register ... __asm__("r10")` operand; `rusage=0`.
3. **Deliberate blind spots.** `skip_path` refused `/lib/`, `/lib64/`, `/usr/lib/`, `/proc/`,
 `/sys/`, `/dev/`; `has_dot_so` refused any `*.so*` name; recursion depth was 1. A `FLAG_FILEPATH`
 landing in any of those would have been invisible even with bugs 1–2 fixed.
 **Fix:** walk everything (depth 4) with no name/path filters; only `/proc` and `/sys` are not
 recursed (their one-level listing is still printed).

## wprobe3 — the probe that works
`solve/session12/wprobe3.c` → `wprobe3.so` (20168 B; `DT_NEEDED libc.so.6`, only `strlen`/
`__stack_chk_fail`/`__cxa_finalize` undefined — the same import profile `content_filter` already
accepts). Inline syscalls only; `getenv` retained solely to keep the libc dependency.
- Prints `P3_ENTER`, `URANDOM ok|missing`, and `ENVIRON <verbatim /proc/self/environ>`.
- Full walk: `E <path> m<mode-octal> s<size> d<d_type>` for **every** entry, then `WALKDONE`.
- Uses `lstat` (not `stat`) so symlinks like `/dev/fd/8` are not followed → no recursion blow-up.
- `XEC <path> n<bytes> t<Y|N>` then `OUTHEX`/`OUTTXT` for **every exec-bit regular file**
 (`/omnitrix` excluded); falls back to dumping small readable files (`RD <path> ...`).
- Local unit-test hook: build with `-DW3_TEST` for a host-side driver against a fake root, and
 `-DW3_ROOT='"/some/root"'` to bound the walk.

## Live proof (both runs, unmodified stock binary)
Driver: `race_live3.py` (= `race_exploit5.py` with **full** probe-chunk capture instead of the old
"keep at most 3 chunks containing markers, drop TOP/NENT" filter) + `run_live17.sh`.

| run | instance | window | freeze | payloads | result |
|-----|----------|--------|--------|----------|--------|
| 17a | fresh | t=123s | sticky=True | `replay/w.so` 20168 B + `replay/go` 52 B both LANDED | **flag** |
| 17b | resumed | t=62s | sticky=True | both LANDED | **flag** (identical) |

The detect → freeze → inject → recall chain from §22.5/§23 was correct and needed no changes. The
only thing missing was a probe whose output you could trust.

## Live facts confirmed by wprobe3 (authoritative, verbatim)
- `ENVIRON`: `PATH=...`, `HOSTNAME=pwn-omnitrix`, `OMNITRIX_BIND=0.0.0.0:7878`,
 `KUBERNETES_PORT*`/`KUBERNETES_SERVICE_*`, `HOME=/`. **No `FLAG_FILEPATH`** → confirms
 `ARG FLAG_FILEPATH` is COPY-only, never exported; the path is *not* discoverable from the
 environment, so enumeration is mandatory (this is the intended shape of the challenge).
- Rootfs: `/lib64/ld-linux-x86-64.so.2`, `/lib/x86_64-linux-gnu/{libc,libgcc_s,libm}.so.6`,
 `/omnitrix` (m755 s1500312), **`/congratulationsyougottheflag` (m111 s682696)**,
 plus `/dev`, `/proc`, `/sys`, `/tmp/omnitrix`, `/etc/{hosts,hostname,resolv.conf}`.
- The environment is Kubernetes-backed (`pwn-omnitrix` hostname, `172.22.0.1` API).

## Files added this session
- `solve/session12/wprobe3.c` / `wprobe3.so` — the fixed enumerator (ship this, not wprobe2).
- `solve/session12/race_live3.py` — live driver with full capture.
- `solve/session12/run_live17.sh` — instance launcher + run wrapper (logs beside it).
- `solve/session13/p3_report_live17.bin` — the raw in-container walk dump containing the flag entry.
- `solve/session13/live17{,_launch}.log` — run 17b console + launcher output.
- `solve/FLAG.txt` — flag + artifact + provenance.

## Lesson (worth keeping)
When a long investigation's conclusion rests on "I enumerated X and saw nothing", **verify the
enumerator**. Here two independent implementation bugs in the recon tool manufactured a false
negative that survived twelve sessions and one wrong root-cause hypothesis. The
`merged_mask`/race/`content_filter`/OREP work was all correct and reusable; the tooling that
*reported the state of the world* was not.
