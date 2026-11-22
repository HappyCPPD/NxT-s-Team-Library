# Owner Of The Footprints — Writeup

**Category:** Forensics (Windows DFIR)
**Flag:** `SkillBit{Th3y_w0n7_sUrV1v3_34}`

## Challenge

> An attacker got into a service company's network and moved between machines. Two jump servers were the way in.
>
> We need the account that performed the lateral movement. Both servers have hundreds of users on them, and the attacker deleted most of the logs before leaving. Some evidence survived.

We get two KAPE-style triage collections:

- `2025-03-11T082527_JUMP-SCV-01.zip`
- `2025-03-11T090100_JUMP-SCV-02.zip`

Each one holds `C:\Windows\System32\winevt\logs\*.evtx`, the registry hives (`SAM`, `SYSTEM`, `SOFTWARE`, `SECURITY`) and the service profile `NTUSER.DAT`s.

## Approach

### 1. Turn the logs into something you can search

`evtx_dump` was broken on my machine, so I used `python-evtx` to dump every non-empty `.evtx` to one-line XML. After that, `grep` and some small regex scripts were enough:

```python
import sys, Evtx.Evtx as ev
with ev.Evtx(sys.argv[1]) as l:
 for r in l.records:
 print(r.xml.replace('\n', ' '))
```

### 2. Check what's left in the Security logs

| Host | Notable |
|---|---|
| JUMP-SCV-01 | ~19k `4907` events (audit-policy noise). The log stops around 03:3x on 2025-03-11, so the attack window is gone. |
| JUMP-SCV-02 | `1102` (log cleared) at **07:49:08**, then only post-wipe events |

The Security logs are a dead end. The usernames are noise too: there are dozens of `Th3y_w0n7_sUrV1v3_NN` accounts on both boxes.

### 3. Logs the attacker didn't clear: RDP on JUMP-SCV-02

`Get-EventLog | Clear-EventLog` only clears the *classic* logs. The `Applications and Services` operational channels stay put.

**`Microsoft-Windows-RemoteDesktopServices-RdpCoreTS/Operational`** (JUMP-SCV-02):

```
07:30:32 131 ConnType=TCP ClientIP=192.168.91.159:50086
07:31:18 131 ConnType=TCP ClientIP=192.168.91.159:50092
07:31:18 227 'User is not granted access to this connection' <-- first attempt denied
07:33:53 131 ConnType=TCP ClientIP=192.168.91.159:50099
07:33:53 66 ConnectionName=RDP-Tcp#3 SessionID=12 <-- succeeds
07:38:01 ... disconnect
```

**`Microsoft-Windows-TerminalServices-LocalSessionManager/Operational`** (JUMP-SCV-02). This is the only session in the whole log with a non-`LOCAL` source address:

```
07:34:50 21 User=JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 SessionID=12 Address=192.168.91.159
07:34:51 22 User=JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 SessionID=12 Address=192.168.91.159
07:38:04 24 User=JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 SessionID=12 Address=192.168.91.159
```

### 4. PowerShell Operational (4104 Script Block Logging) on JUMP-SCV-02

This log also survived the wipe, and it shows the whole story:

```
07:33:11 IEUser (RID 1000) net localgroup "Remote Desktop Users" Th3y_w0n7_sUrV1v3_34 /add
07:33:16 IEUser (RID 1000) netsh advfirewall firewall set rule group="Remote Desktop" new enable=Yes
07:36:38 RID 1043 Set-Location 'C:\Users\Th3y_w0n7_sUrV1v3_34\Desktop'
07:37:17 RID 1043 whoami
07:37:20 RID 1043 echo HACKED
07:49:08 Administrator Get-EventLog -LogName * | ForEach { Clear-EventLog $_.Log }
```

1. The first RDP attempt failed because `_34` wasn't allowed to use RDP.
2. The account was added to `Remote Desktop Users` and the firewall rule was opened.
3. The second attempt worked.
4. The attacker ran recon in that session, then cleared the logs.

### 5. Confirm the RID → username and the source host from the registry

**SAM** (`SAM\Domains\Account\Users\Names`, where each name's value type is its RID):

```
1043 (0x413) -> Th3y_w0n7_sUrV1v3_34
```

The SAM `F` record for RID 1043 on JUMP-SCV-02 gives a last logon of **2025-03-11 07:34:03**, which matches the RDP logon.

**SYSTEM** (`ControlSet001\Services\Tcpip\Parameters\Interfaces`):

| Host | IP |
|---|---|
| JUMP-SCV-01 | **192.168.91.159** |
| JUMP-SCV-02 | 192.168.91.173 |

So the RDP came from JUMP-SCV-01 into JUMP-SCV-02, which is a jump-server-to-jump-server hop. The account that made the hop was **`Th3y_w0n7_sUrV1v3_34`**.

## Red herrings

- **`bquanman`:** `4648` events on 02 at 07:59–08:01 show Administrator using `bquanman` creds against `BquanmanPC` (192.168.91.1:445). That's SMB to a third machine *after* the hop between the two jump servers.
- **`Th3y_w0n7_sUrV1v3_42` (RID 1051 on 01):** this was the only user active on JUMP-SCV-01 during the window, so it was the operator's session on the *source* box. But the account that *did the lateral movement* is the one that logged into the target over the network, which is `_34`.
- **Hundreds of `Th3y_w0n7_sUrV1v3_NN` console sessions:** these are local logon churn (LSM `Address=LOCAL`) and don't count as lateral movement.

## Takeaways

- Clearing logs with `Clear-EventLog` / `wevtutil cl` on the classic logs leaves **RdpCoreTS**, **LocalSessionManager** and **PowerShell/Operational** behind. For RDP lateral movement, LSM 21/22/24 with a non-`LOCAL` `Address` is the key sign.
- Even with the Security log gone, the SAM `F` value's last-logon timestamps let you place an account's activity on a timeline.
- Match the source IP to a host using the `Tcpip\Parameters\Interfaces` key in the SYSTEM hive.

**Flag:** `SkillBit{Th3y_w0n7_sUrV1v3_34}`
