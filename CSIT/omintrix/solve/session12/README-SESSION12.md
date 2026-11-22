# Omnitrix — SESSION 12 HANDOFF (2026-09-20) — live RCE proven, flag artifact identification is the only gap

Supersedes nothing in `../HANDOFF.md`; this is §23 material. Read `../HANDOFF.md` §1–22 first
(protocol, auth, gate arithmetic, strand container `OREP`/form `scan`+band `engage`).

## TL;DR
- Everything earlier work proved LOCALLY in §22.5 is correct and I reproduced it end-to-end on the
 stock binary several times (`TISC{local_test_flag_deadbeef}`).
- **RCE is now proven ON THE LIVE INSTANCE**: `omnitrix_probe` was dlopen'd and executed inside
 the real container and relayed its own output back over our socket.
- The only remaining gap: locating/using the live flag artifact. It is NOT at any "flag"-named
 path, the container ENVIRON is empty, and execve of all guessed paths yields nothing.
 ⇒ strong hypothesis (matches the challenge hint "inherited something that was never supposed to
 be part of it"): the flag artifact is a **shared object** the server is meant to `dlopen`, not a
 standalone executable. It must be enumerated and dlopen'd, not execve'd.

## What was wrong with earlier work's live approach (and the fixes)
1. **Runs were too short / no window arithmetic.** The mask-open window live is rare and *short*
 (`hot_open` 0 for the first ~150 s of churn, then a few %). earlier work's 150 s run ended right as
 windows began. → churn for the WHOLE instance window.
2. **Big payloads lose the race.** The mask gate is evaluated in the worker *when it processes the
 task*, so a 20 KB `.so` inject often arrives after the window has closed, while a 52-byte
 container lands. Observed live: container landed, `.so` did not.
3. **→ Fix: detect → freeze → exploit** (`race_exploit5.py`): a tiny-inject detector finds a window;
 ALL mode-change churn is then stopped (mask stays 0x3f4 because only op-0x50 applies rewrite it);
 verified "sticky" by another tiny inject; then the 20 KB `.so` + container are injected leisurely
 and the recall loop runs. Both payloads landed live with this.
4. **Tooling bugs fixed:** inject workers desynced permanently after a timeout (read stale lease
 replies as inject replies) → now reconnect on any unclassified reply; the probe blocked writing
 the flag to non-reading churn sockets → probe now sets O_NONBLOCK on every fd before writing.
5. **The old probe silently returned on live.** Its `getenv("FLAG_FILEPATH")` is NULL and its
 candidate list missed — because the live image is `FROM scratch` and the Dockerfile's
 `ARG FLAG_FILEPATH` is used ONLY as the `COPY` destination, i.e. **never exported as ENV**.

## Live recon facts (authoritative, from the probe running in-container)
- `ENVIRON` is ~empty (no FLAG* variable at all) → `getenv("FLAG_FILEPATH")` is `(null)`.
- `/dev/urandom` present.
- `/` entries observed: `lib64` and little else; **no top-level name contains "flag"**.
- `execve` of `/flag.bin`, `/flag`, `/flag.txt`, `/app/flag.bin`, `/srv/flag.bin`,
 `/opt/flag.bin`, `/data/flag.bin`, `/ctf/flag.bin`, `/home/flag.bin` → all `total=0 token=N`.
- The in-container walk output was **partially lost** in the last live run (my report-saver only
 kept chunks containing marker strings). That is fixed in `race_exploit5.py` (now saves every
 chunk). A clean live listing has NOT yet been captured — that is step 1 below.

## Verified local results (same code paths)
- `race_exploit5.py` + `wprobe2.so` on the stock binary: window detected at t≈0 s, `sticky=True`,
 both payloads LANDED, probe ran, flag relayed:
 `OUTTXT token: <16hex>|send the same token back: TISC{local_test_flag_deadbeef}|`
- Deterministic route without the race: run `run/omnitrix_patched` (3-byte NOP at file off 0x5e46b
 forces `merged_mask |= 0x150`) and use `test_det.py` — full chain in seconds.
- The mask race is NOT parallelism-dependent: it still fires with the server pinned to ONE CPU
 (`taskset -c 0`); it survives 80 ms RTT (latency proxy). So single-vCPU instances are fine —
 the live limiter is window *duration/frequency*, not core count.
- `op-0x50` immediately after `op-0x20` frequently returns `no such lease` — the lease is cached
 asynchronously; sleep ~0.25–0.3 s between issuing a lease and using it.

## FILES (persistent copies in this dir)
- `race_exploit5.py` — THE live driver (detect → freeze → inject → recall). Env: `NRACE THROTTLE STAT`.
- `race_exploit3.py` — earlier hammer-style driver with counters (useful reference).
- `race_stick.py`, `race_stick2.py`, `tunnel_diag.py` — window oracle / diagnostics.
- `wprobe2.c/.so` — self-reporting probe: announces itself, env/urandom/recon, exec candidates,
 hex+text relay, O_NONBLOCK writes. **use as the payload**
- `wprobe3.c` — verbose verifiable walk (`E d0 <path> type= mode= size=`, `DIR ... nent=`),
 `-DDEPTH_LIMIT=0` for a flat local listing. Compile: `gcc -shared -fPIC -O2 -o wprobe3.so wprobe3.c`
- `test_det.py` — deterministic downstream test vs the patched server.
- `cpuprobe.py`, `serialize_proxy.py`, `latency_proxy.py` — the experiments that ruled out
 core-count and tunnel-serialisation as causes.
- `run_live15.sh` / `run_live16.sh` — fresh-instance launcher + run wrappers (read the lyla creds
 from `../../omnitrix-credentials.txt`; pkill first).
- `hook.so` (dlopen logger, LD_PRELOAD for local), `run/theflag.bin` (local test flag),
 `run/flag.bin` (mode 0111 copy), `run/omnitrix_patched` (mask-forcing build).
- `p2_report_live.bin` — last live probe dump (partial listing).

## NEXT STEPS (in order — steps 1–2 need no live instance)
1. **Get a clean live listing.** Run `race_exploit5.py` on a fresh instance with an instrumented
 probe: walk `/` with `DEPTH_LIMIT 1`, print every entry with mode+size, hexdump the first bytes
 of every regular file, and print each `getdents64` return count. In a `scratch` image the whole
 filesystem is ~5 entries, so the listing is tiny and unambiguous.
2. **Handle all three artifact shapes** in the same probe: (a) execve + 16-byte token dance
 (done); (b) `dlopen(path, RTLD_NOW)` + `dlsym` for the symbol the server itself looks up
 (`omnitrix_probe`, from §17.1/§22.2) and for generic names; (c) read+hexdump of any small file.
 Prefer dlopen: with an empty ENVIRON the "inherited" hint points at an inherited/shared object.
3. Re-run the live driver with the winning probe. One instance ≈ 5 min; `race_exploit5.py` reliably
 detects + freezes + lands both payloads, so a single window is enough.
4. Cleanup: `pkill -9 -f lyla-client; pkill -9 -f launcher` after each attempt (they hold the port).

## ENV / OPS NOTES
- Local run: `RUST_LOG='omnitrix=error' OMNITRIX_BIND=127.0.0.1:PORT FLAG_FILEPATH=<flagbin>
 LD_PRELOAD=hook.so ./omnitrix > /var/tmp/omni.log 2>&1` (background; it will die if its parent
 shell goes away — restart with `exec` and verify with `ss -ltn | grep PORT`).
- The vault is shared: `/tmp/omnitrix/codon/replay/` — clear it between local experiments
 (`rm -rf /tmp/omnitrix/codon/replay/*`).
- Flag submissions are attempt-limited: do NOT shotgun; converge on one answer.
- `/tmp` is a RAM tmpfs (wiped on reboot) — hence the copies in this directory.