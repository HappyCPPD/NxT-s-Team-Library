# CLMP/1.1 — ColdLink Case Management Protocol

**Device family:** ColdLink CaseManager CM-900
**Transport:** TCP, line-oriented, UTF-8, `\n`-terminated.
**Default control port:** 7601
**Default historian port:** 7602 (read-only event feed, no authentication)

> ColdLink Refrigeration Systems — internal service documentation.
> For authorized service partners only.

### Connecting to a hosted instance (TLS / SNI)

On the hosted CTF instance both endpoints are **TLS-terminated and SNI-routed**
to your team's instance; they are not reachable as plain TCP. Connect over TLS
and present the endpoint's own hostname as the SNI server name:

```
openssl s_client -quiet -connect <HOST>:<PORT> -servername <HOST>
```

`<HOST>:<PORT>` are the host/port of the endpoint from the challenge page
(the control service is the "Challenge" endpoint; the feed is the "Historian
log feed" endpoint), and `-servername` must equal `<HOST>` so SNI routes you to
your instance. To drive the Python toolkit against a TLS endpoint, run a local
plaintext→TLS tunnel and point the toolkit at the local port:

```
socat TCP-LISTEN:7601,reuseaddr,fork OPENSSL-CONNECT:<HOST>:<PORT>,snihost=<HOST>
python3 coldlink_tech.py --host 127.0.0.1 --port 7601 cases
```

**Local testing only (`docker compose up`):** the local compose stack has no
TLS in front of it, so plain TCP applies directly — use the toolkit's
`--host/--port` against `127.0.0.1` and `nc` for the historian feed, with no
`openssl`/`socat` wrapper.

---

## 1. Session & framing

On connect, a CM-900 controller emits a greeting, then waits for commands:

```
CLMP/1.1 ColdLink CaseManager CM-900
SERIAL CLX-900-SN-4417
NONCE 9f3c...<32 hex>
READY
OK greeting
```

Every command returns zero or more `DATA ...` lines followed by a terminal
line that begins with `OK` or `ERR`. A client reads until it sees that
terminal line. `QUIT` closes the session.

## 2. Technician authentication

The CM-900 uses a per-connection challenge/response. The controller presents
its `SERIAL` and a random `NONCE` in the greeting. The technician toolkit
answers:

```
AUTH <serial> <token>
```

where `<token>` is derived from the ColdLink **field master key** that is
provisioned into the technician toolkit (see `coldlink_tech.py`,
`auth_token`). The same key is used across the CM-900 fleet.

- Success: `OK role=technician`
- Failure: `ERR bad-auth`

All commands other than `AUTH`, `HELP`, `PING`, `QUIT` require a successful
`AUTH` first; otherwise they return `ERR need-auth`.

## 3. Case registers

```
CASES
```

Returns one line per refrigerated case:

```
DATA case=<n> name=<label> temp=<C> set=<C> mode=<cool|defrost> trip=<0|1>
```

| field | meaning |
|-------|-----------------------------------------------------|
| temp | current case temperature (°C) |
| set | setpoint (°C) |
| mode | `cool` = holding to setpoint, `defrost` = heating |
| trip | `1` while a compressor trip lockout is in effect |

`MODE <case> cool|defrost` requests a manual mode override for one case.
Note that an **enabled schedule re-asserts case modes on every controller
cycle**, so a manual override will not stick while a schedule drives it.

## 4. Schedule registers

Schedules are the controller's standing rules. Each cycle the controller
applies every enabled schedule entry.

```
SCHED LIST -> DATA sched=<id> name=.. action=.. enabled=..
SCHED GET <id> -> full entry incl. note
SCHED SET <id> <k=v> [<k=v>..] -> modify (fields: enabled, action)
SCHED DEL <id> -> remove an entry
```

Recognized `action` values:

| action | effect |
|-----------------|-----------------------------------------------------|
| `cool_all` | hold every case to its setpoint |
| `force_defrost` | drive every case into continuous defrost |
| `noop` | no effect |

`enabled` accepts `1/0`, `on/off`, `true/false`, `yes/no`.

## 5. Maintenance macros

Macros are background automation that the controller runs on timers,
independently of the live schedule. They are a common source of
"it came back by itself" behavior after a manual change.

```
MACRO LIST -> DATA macro=<id> name=.. enabled=.. period=.. action=..
MACRO GET <id> -> full entry incl. target + note
MACRO ENABLE <id>
MACRO DISABLE <id>
```

| action | meaning |
|-------------------|----------------------------------------------------------|
| `noop` | no effect |
| `ensure_schedule` | on each `period`, re-enable the macro's `target` schedule if a technician disabled or removed it |

## 6. Compliance status

```
STATUS
```

Returns the controller's cold-chain compliance evaluation:

```
DATA compliant=<0|1> cases_cold=<n>/6 held=<s>s reason=<...>
```

When the site is fully compliant — all six cases below the ceiling,
sustained for the required hold window, with no rule or macro re-forcing
defrost — the controller additionally returns:

```
DATA flag=hiCTF{...}
```

The compliance ceiling is 5 °C and the sustained hold window is 60 seconds.
The `reason` field lists everything still blocking compliance.

## 7. Historian feed (port 7602)

A read-only, unauthenticated event stream. On the hosted instance it is the
"Historian log feed" endpoint and is reached over TLS/SNI as described under
"Connecting to a hosted instance" above (e.g. `openssl s_client -quiet
-connect <HOST>:<PORT> -servername <HOST>`); on a local `docker compose up`
stack it is plain TCP (`nc 127.0.0.1 7602`). On connect it replays recent
events and then streams live ones. Event records look like:

```
seq=<n> ts=<s> event=<type> <extra fields...>
```

Event types include `door_open`, `compressor_trip`, `sched_deleted`,
`macro_state`, `macro_apply`, and `hold_reset`. The feed is the fastest way
to see *why* a change you made did not persist.
