# The Phantom Login

**Category:** forensics | **Flag:** `spooky{the_ghost_left_a_trace}`

## Approach
Correlating `njit_security.csv` (Windows events) with `njit_web.log` traced phantom account `evelyn.graves` from external IP `203.0.113.77`:
- 03:10–03:12 — 9× 4625 failures (Status 0xC000006A)
- 03:14 — 4624 success, LogonType=3, NTLM, LogonID 0xB130
- 03:15 — 4672 SpecialPrivilegesAssigned, same LogonID
- 03:17 — 5140 access to \\BW-FS01\Archives$ with LogonID 0xB130
- 03:19:08 — `GET /archives/export?note=c3Bvb2t5e3RoZV9naG9zdF9sZWZ0X2FfdHJhY2V9`

Base64-decoding the `note` parameter yields the flag. Decoys ruled out: `administrator` brute force from 198.51.100.66 and ambient internal 4625s.

## Reproduction
```bash
echo c3Bvb2t5e3RoZV9naG9zdF9sZWZ0X2FfdHJhY2V9 | base64 -d
```
Output: `spooky{the_ghost_left_a_trace}`
