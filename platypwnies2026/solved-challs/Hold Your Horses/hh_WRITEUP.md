# Hold Your Horses — web — Platypwn 2026

Solver: author (earlier work). Status: SOLVED, not submitted.
Instance: http://10.83.0.51:80 (needs the pp2026 WireGuard tunnel).
Flag: `PP{h0ld_y0ur_byt3s_n0t_y0ur_h0rs3s::HEWRVNeikRno}`

## TL;DR

A TOCTOU in the betting path lets you place a bet *after* the race has started.
The `favorite` horse runs at 2x speed, so the mid-race leader is deterministically
the winner. Bet the leader all-in each race and your stack doubles:
9 → 18 → 36 → 72 → 144 → 288 → 576 ≥ 500 → VIP → flag. 6 races, 6 wins, 0 losses.

## Handout

`web.horseracing.zip` — a Rust **axum** app (`src/main.rs`, ~210 lines). State is a
single `Arc<RwLock<AppState>>`, served by a `current_thread` Tokio runtime.

```
GET / -> static index.html
GET /fonts/* -> embedded woff2
GET /api/state -> PublicState { race_number, timer, horses[16], user_points, user_bet, vip }
POST /api/bet -> bet, wrapped by route_layer(betting_open)
```

`AppState { user_points: 10, ..Default }` at boot; `user_bet: Option<(usize,u64)>`.

### race_loop (one tick per second)

| timer | action |
|-------|--------|
| `== 0` | `race_number += 1`, `horses = [0.0; 16]` |
| `== 30`| `favorite = rand::random_range(0..=15)` |
| `> 30` | every horse `h` gains `base ~ U(0,3)`, **doubled if `h == favorite`**; if any horse `>= 100.0`, `winner = argmax(horses)`, settle the bet, `timer = 0` |

Settlement: the stake was already deducted at bet time, so a win pays
`user_points += amount * 2` → **net `+amount`**. A loss keeps nothing.

### the gate

```rust
async fn betting_open(State(state), request, next) -> Result<Response, (StatusCode, String)> {
 if state.read.await.timer >= 30 {
 return Err((StatusCode::BAD_REQUEST, "Race already started".to_string));
 }
 Ok(next.run(request).await)
}
```
Applied via `.route_layer(middleware::from_fn_with_state(state.clone, betting_open))`.

## The bug — TOCTOU on the request body

`route_layer` middleware runs **before** the handler's extractors. `betting_open`
validates `timer < 30` against the **request head only**; the handler's
`Json<BetRequest>` extractor reads the **body** later. So:

1. Send the `POST /api/bet` request line + headers (with `Content-Length`) and
 **withhold the body**.
2. The middleware runs, sees `timer < 30`, and passes.
3. The handler blocks inside the `Json` extractor, waiting for the body.
4. The race runs. Poll `GET /api/state` — all 16 horses are visible.
5. Once a decisive leader emerges, send the body — the bet lands **mid-race**,
 on the horse we already know is winning.

Nothing in the handler re-checks the timer; the only gate was the middleware.

## Why the leader always wins

The favorite gains `U(0,3)*2` per tick vs `U(0,3)` for everyone else. Over a
race-to-100 that 2x advantage compounds — the favorite essentially always wins.
Simulation (`hh_sim.py`, n = 200,000):

```
P(favorite wins) = 1.0000
P(fired leader == winner | fired, M>=60, margin>=20)= 1.00000
```

So the strategy is deterministic: fire the withheld body the first instant the
leader is `>= 60` with a `>= 20` gap over 2nd (and `<= 90`, leaving several ticks
before the race ends).

## Payoff ladder

Net `+amount` per win ⇒ bet the whole balance ⇒ doubles. From the live start of
`user_points = 9` (a 1-point bet had already been lost on the instance):

```
9 -> 18 -> 36 -> 72 -> 144 -> 288 -> 576 (>= 500 => VIP)
```

## Exploit

`hh_exploit.py` — raw `socket` for the stalled-body POST, `urllib` for the
`/api/state` polling loop, fixed 64-byte JSON body (space-padded) so the
`Content-Length` can be sent up front.

```
python3 hh_exploit.py --control # immediate body mid-race -> HTTP 400 "Race already started"
python3 hh_exploit.py # stalled body -> ACCEPTED, doubles to 576, prints VIP
```

`hh_run.log`:
```
[race 13] timer~51 leader=#10 stake=9 -> ACCEPTED [+] WON 9 -> 18
[race 14] timer~52 leader=#10 stake=18 -> ACCEPTED [+] WON 18 -> 36
[race 15] timer~53 leader=#6 stake=36 -> ACCEPTED [+] WON 36 -> 72
[race 16] timer~51 leader=#12 stake=72 -> ACCEPTED [+] WON 72 -> 144
[race 17] timer~51 leader=#6 stake=144 -> ACCEPTED [+] WON 144 -> 288
[race 18] timer~51 leader=#0 stake=288 -> ACCEPTED [+] WON 288 -> 576
[+] VIP: VIP access granted! Here is your flag: PP{h0ld_y0ur_byt3s_n0t_y0ur_h0rs3s::HEWRVNeikRno}
```

## Root cause & fix

The gate is enforced at the wrong point in the request lifecycle, against a
snapshot that goes stale before the bet is actually applied. Fix: re-validate the
race state inside `bet` under the same write lock that mutates `user_bet` (or move
the check after body extraction), so the timer that is checked is the timer that
guards the mutation:

```rust
let mut state = state.write.await;
if state.timer >= 30 { return Err((StatusCode::BAD_REQUEST, "Race already started".into)); }
```

## Environment notes

- Target is only reachable over the event VPN (`wg-quick up pp2026-vpn`).
- If `user_points` ever reaches 0 the instance has no in-app reset (amount 0 is
 rejected, and `points < amount` blocks every bet) — a platform instance reset
 is required.
