# Garden (Kaspersky CTF) — Analysis & Exploit Writeup

**Target:** https://garden.task.sasc.tf/
**Source:** `garden-299ddb5aaa0347e1.tar.gz` (Flask + cshogi shogi app behind a Babylon.js 3D frontend)

## The app

Three endpoints, all in `static/main.py`:

- `GET /game/state` — returns the current player's board (sfen, legal moves, turn, captures)
- `POST /game/move` — plays a move, then lets a simple AI respond as White
- `POST /game/new` — clears the player's move history

Each player is identified by `session['user_id']`, a `uuid4` string set on first visit and stored in a signed Flask cookie. All of a user's moves are stored in a SQLite table (`game_moves`) and replayed from scratch on every request to reconstruct the board — there's no server-side game object held in memory between requests.

## The vulnerability

`Game.save_move_to_db` builds its INSERT with an f-string instead of parameter binding:

```python
cur.execute(f"""
 INSERT INTO game_moves (user_id, move, created_at)
 VALUES ('{self.user_id}', '{move_usi}', datetime('now'))
""")
```

`move_usi` is safe — `cshogi.Board.move_from_usi` only accepts a handful of exact formats (`"7g7f"`, `"P*5e"`, optionally a trailing `+`), so there's no room to smuggle SQL through it. (A trailing NUL byte *is* accepted by cshogi's parser, but Python's `sqlite3` module unconditionally rejects any query string containing a NUL, so that path just always errors — not usable as a conditional oracle.)

`self.user_id`, however, comes straight from the session cookie. Flask's default `SECRET_KEY` in `main.py` is the literal string `'dev-secret-key-change-in-production'`, and nothing in the given `compose.yaml` overrides it. If that's really the key in use, anyone can mint their own signed session cookie with an arbitrary `user_id` — including a SQL-breakout string — and reach the injection.

`init_db.py` seeds the table with:

```python
INSERT INTO game_moves (user_id, move, created_at)
SELECT 'admin', 'kaspersky{test}', datetime('now')
WHERE NOT EXISTS (SELECT 1 FROM game_moves WHERE user_id = 'admin')
```

So the real flag almost certainly sits in that `admin` row in production, and the challenge title ("winning without attending a battle") is the pun: you don't beat the shogi AI, you SQL-inject your way to the flag instead of playing the game.

## The exploit (verified working against a local reproduction)

1. **Forge a session cookie.** Flask signs sessions with `itsdangerous.URLSafeTimedSerializer(secret_key, salt="cookie-session", signer_kwargs={"key_derivation": "hmac", "digest_method": sha1})`. Given the secret key, this is fully reproducible outside Flask (see `exploit_poc.py`).
2. **Inject through `user_id`.** Set it to a payload that breaks out of the VALUES tuple and re-enters SQL:
 ```
 x', (CASE WHEN (SELECT unicode(substr(move,{i},1)) FROM game_moves WHERE user_id='admin')>{mid} THEN (SELECT 1/0) ELSE 'ok' END), datetime('now')) -- 
 ```
 `SELECT 1/0` in SQLite doesn't raise "divide by zero" — integer division by zero returns `NULL`, which then trips the `move` column's `NOT NULL` constraint. `save_move_to_db` has no `except` clause around the `execute` call, so that `IntegrityError` propagates all the way up to an unhandled 500.
3. **Play any legal move** (e.g. `7g7f`) through `POST /game/move` with that cookie attached. The response code is a clean boolean oracle: **500 = condition true, 200 = condition false.**
4. **Binary-search each character's ASCII code** (`unicode` of `substr(move, i, 1)`), using code ≤ 1 as the end-of-string sentinel (SQLite's `substr` past the end returns `''`, and `unicode('')` is `NULL`, which is never `>` anything). ~7 requests per character.

I verified this full chain end-to-end against a local SQLite DB with a fake flag row and Flask's real session-signing code — it recovers the flag exactly (`exploit_poc.py`).

## Where it broke on the live instance

Porting the same exploit into a real browser (needed because the sandbox here can't reach arbitrary CTF hosts, and Flask session cookies are `HttpOnly` so plain `curl`/`requests` calls with a forged cookie were the only clean option once inside a browser context — I used the browser's JS engine with `crypto.subtle` to reproduce the HMAC-SHA1 signing directly, cross-checked byte-for-byte against a real local Flask instance):

- The forged cookie's *format* and *signature computation* are provably correct (validated three independent ways, including hash-comparison against a genuine Flask 2.3.3 + itsdangerous instance).
- Against the live target, **no forged cookie ever persists identity across two requests** — even sending the exact same cookie string twice in a row, the second request always sees a fresh, unplayed board. Totally invalid garbage cookies behave identically to carefully-forged ones.
- This means the live server's actual `SECRET_KEY` is **not** `'dev-secret-key-change-in-production'`. I also tried ~35 other common/thematic guesses (`garden`, `shogi`, `kasperskyctf`, `changeme`, etc.) — none worked.
- Separately, `debug=True` is on and reachable (e.g. `POST /game/move` with a bare JSON integer body crashes with a full Werkzeug traceback), but the interactive debugger (`EVALEX`) is disabled and no local variables are rendered inline, so that surface doesn't leak the key either.

**Bottom line:** the vulnerability is real and the exploit is fully built and tested, but the deployed instance appears to be running with a non-default secret key, which blocks the forgery step remotely. This is most likely because it's a dynamically-provisioned/archived instance with a randomized per-deployment secret rather than the static one shown in the given source.

## Files

- `exploit_poc.py` — full working local proof-of-concept (cookie forging + blind SQLi extractor), runs against a throwaway SQLite DB with a fake flag.
- `browser_exploit.js` — the same logic adapted to run inside a browser console against a live target, for reuse if you obtain the real secret key (e.g. from a teammate, a hint, or source-diffing a patched version).

## Other things worth checking if you get unstuck

- `Game.is_valid_drop` is a stub that always returns `True`, skipping shogi's normal drop-legality checks (nifu is actually still enforced by `cshogi.move_from_usi` itself, but the *uchifuzume* rule — illegal to deliver checkmate by dropping a pawn — is not re-checked by the app). This could let you force a checkmate that a real shogi engine would refuse. I didn't find a code path that turns a legitimate win into the flag, though (the visible `main.py` has no "you won, here's the flag" logic), so this only matters if the deployed app differs from the given source.
- If you can get the real `SECRET_KEY` any other way, `exploit_poc.py`'s `mint_cookie` + `browser_exploit.js` will get you the rest of the way with no changes needed.
