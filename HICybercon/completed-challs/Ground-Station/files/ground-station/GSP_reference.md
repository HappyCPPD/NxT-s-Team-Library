# GSP/1.0 — Ground Station Protocol (GSC-7 controller)

**Device:** GSC-7 Ground Station Controller (fueling/cooling controller)
**Transport:** TCP, line-oriented, UTF-8, `\n`-terminated.
**Control port:** 7603
**Telemetry port:** 7604 (read-only event feed, no authentication — flavor only)

> Fictional vendor documentation for a simulated launch-support controller.
> This is a validation exercise: confirm the controller will run the fueling/
> cooling test safely before the test is authorized.

---

## 0. Connecting (hosted vs. local)

GSP/1.0 is a plain line-oriented TCP protocol, but **how you reach the
controller differs between the hosted competition instance and a local test
stack.** The platform shows a `HOST` and `PORT` for each exposed endpoint
(control and telemetry separately).

**Hosted instance (TLS / SNI).** The platform's instancer terminates TLS in
front of the service and routes by SNI (Server Name Indication). You must
therefore speak TLS and present the host as the SNI server name — **plain
`nc` / plain TCP will not connect.**

Manual session:

```
openssl s_client -quiet -connect <HOST>:<PORT> -servername <HOST>
```

To keep using a plain-TCP client (e.g. `gsc_tech.py`), bridge it through a
local TLS tunnel and connect the client to the local plaintext port:

```
socat TCP-LISTEN:7603,reuseaddr,fork OPENSSL-CONNECT:<HOST>:<PORT>,snihost=<HOST>
python3 gsc_tech.py --host 127.0.0.1 --port 7603
```

**Local testing only (`docker compose up`).** The local compose stack has no
TLS front end, so plain TCP applies directly:

```
python3 gsc_tech.py --host 127.0.0.1 --port 7603
```

---

## 1. Session & framing

On connect the controller emits a greeting and then waits for commands:

```
GSP/1.0 GSC-7 Ground Station Controller
UNIT GS-ALPHA-07
NONCE <16 hex> # 8-byte per-session challenge
READY
OK greeting
```

Each command returns zero or more `DATA ...` lines followed by a terminal line
beginning with `OK` or `ERR`. Read until that terminal line. `QUIT` ends the
session. All commands except `AUTH`, `HELP`, `PING`, `QUIT` require a prior
successful `AUTH` (otherwise `ERR need-auth`).

## 2. Access (challenge-response)

```
AUTH <response-hex>
```

The controller presents a per-session `NONCE`. The engineer's client answers
with the 8-byte **response** the controller's firmware access routine computes
for that nonce. The field maintenance client does **not** compute this for you;
the response derivation lives in the controller firmware image shipped with
this toolkit (`gsc-fw.bin`). Recover the derivation by analyzing that image,
then compute and submit the response for the live session nonce.

- Success: `OK access=engineer`
- Failure: `ERR bad-auth`

The firmware image is a maintenance/diagnostic build. On boot it prints an
`image-sig=` line (the access routine applied to a fixed internal vector) —
a useful anchor for confirming your reconstruction. It is not an oracle: the
live service issues a fresh random nonce each session.

## 3. Ladder program (PROG)

The controller runs a small ladder program each scan. Each **rung** drives one
output **coil** from an expression over the signals below. Rungs are evaluated
top to bottom; a rung may reference a coil set earlier in the same scan.

```
PROG LIST -> DATA rung=<coil> expr=<expression> (one per coil)
PROG GET <coil> -> that rung
PROG SET <coil> <expr> -> replace that rung's expression (parsed + validated)
```

**Signals**

| name | kind | meaning |
|---------------|--------|------------------------------------------------|
| FILL_LEVEL | sensor | propellant fill, 0–100 % |
| TANK_TEMP | sensor | tank temperature, °C |
| TANK_PSI | sensor | tank pressure, kPa |
| COOLANT_PSI | sensor | coolant-loop pressure, kPa (rises when pumping)|
| START | cmd | test sequence running (1 during a test) |
| ESTOP | cmd | emergency stop (0 nominal) |
| COOLANT_PUMP | coil | run coolant loop |
| VENT_VALVE | coil | open tank vent (relieves pressure) |
| INTERLOCK_OK | coil | fueling precondition satisfied |
| FUEL_VALVE | coil | admit propellant |

**Expression language:** `AND`, `OR`, `NOT`, parentheses; comparisons
`>= <= > < == !=`; arithmetic `+ - *`; numeric literals; signal names.
Booleans are 1/0. Unknown signal names or malformed expressions are rejected.

## 4. Control narrative (nominal safety program)

The validated controller **shall** satisfy the following. Use this to confirm
the live program has not been altered.

- **C1 Coolant.** The coolant loop shall run throughout the test
 (`COOLANT_PUMP` while `START`).
- **C2 Vent.** The tank vent shall relieve pressure during the test
 (`VENT_VALVE` when `TANK_PSI` is elevated, nominally ≥ 50 kPa).
- **C3 Fueling interlock.** Fueling shall be **inhibited** unless the tank is
 within the safe fueling envelope: **tank temperature ≤ 45 °C** and **tank
 pressure ≤ 100 kPa**. `INTERLOCK_OK` enforces this precondition.
- **C4 Fuel valve.** `FUEL_VALVE` shall be gated on `START`, not `ESTOP`,
 `INTERLOCK_OK`, and `FILL_LEVEL < 98`.

**Hard limits (enforced by the test rig, not the program):** a test run is
aborted as unsafe if `TANK_TEMP` exceeds **60 °C** or `TANK_PSI` exceeds
**120 kPa** at any scan. A nominal program keeps the tank inside C3's envelope
so these limits are never reached while filling to the 98 % target.

## 5. Program backup & integrity watchdog

The controller keeps a backup copy of the program and an integrity watchdog.

```
BACKUP STATUS -> DATA live_checksum=.. backup_checksum=.. trusted_checksum=.. arm_will_restore=<0|1>
BACKUP GET -> the backup program (rung list)
BACKUP SAVE -> copy the live program into the backup slot (updates trusted checksum)
WDOG STATUS -> DATA enabled=.. trigger=.. action=.. trusted_checksum=..
WDOG SET enabled=0|1
```

The watchdog's integrity check runs **at test arm** (when `RUNTEST` is issued):
if it is enabled and the live program's checksum does not match the trusted
checksum, it **restores the live program from the backup** and aborts the arm.
Inspect `BACKUP GET` and `WDOG STATUS` if a program change does not take effect.

## 6. Running the validation test

```
RUNTEST -> arms (watchdog integrity check) then, if armed, runs the
 deterministic fueling/cooling simulation.
STATUS -> DATA solved=.. last_test=.. live_checksum=.. wdog_enabled=..
```

`RUNTEST` responses:

- `DATA result=ABORT reason=watchdog_integrity_restore ...` — the watchdog
 reverted your change; nothing ran.
- `DATA result=FAIL reason=<overtemp|overpressure|incomplete>_...` — the test
 ran but violated a safety limit or did not complete.
- `DATA result=SUCCESS ...` followed by `DATA flag=...` — a clean, safe,
 complete fueling test. The flag is issued only here.

## 7. Telemetry feed (port 7604)

Read-only, unauthenticated event stream (connect and read). Replays recent
events then streams live ones: `prog_set`, `backup_save`, `wdog_state`,
`wdog_restore`, per-scan `telem` during a test, `safety_abort`,
`test_complete`. Flavor and debugging aid; it gates nothing.

Reach it the same way as the control service (see §0):

- **Hosted instance (TLS / SNI):** it is a separate SNI-routed endpoint with
 its own `HOST`/`PORT`. Plain `nc` will not work; use
 `openssl s_client -quiet -connect <HOST>:<PORT> -servername <HOST>`, or
 tunnel it with
 `socat TCP-LISTEN:7604,reuseaddr,fork OPENSSL-CONNECT:<HOST>:<PORT>,snihost=<HOST>`
 and then `nc 127.0.0.1 7604`.
- **Local testing only (`docker compose up`):** plain TCP, `nc 127.0.0.1 7604`.
