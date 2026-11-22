# ByteMe 2026 (CTF7) — Solved Challenges

Theme: *Vormir / Soul Stone*. Flag format: `OWASP{...}`.
Each challenge has its own folder containing a detailed `writeup.md` plus the files needed to follow it (challenge files, solve scripts, artifacts/images).

**24 challenges solved.** All 23 below have full write-ups. The only solved challenge without a write-up is **Sacrifice** (Forensics, easy) — excluded by request.

| # | Challenge | Category | Diff | Pts | Solved (Oct 9 2026) | Flag |
|---|-----------|----------|------|-----|---------------------|------|
| 1 | [Hidden Soul](Hidden-Soul/) | Steganography | easy | 100 | 10:09 | `OWASP{h1dd3n_s0ul_b3n34th_th3_sh4d0w}` |
| 2 | [Soul World](Soul-World/) | Steganography | medium | 200 | 10:13 | `OWASP{s0ul_w0rld_h1d3s_1ts_s3cr3t}` |
| 3 | [Broken Soul Vault](Broken-Soul-Vault/) | Forensics | easy | 100 | 10:16 | `OWASP{br0k3n_s0ul_v4ult_r3c0v3r3d}` |
| 4 | [The Last Soul](The-Last-Soul/) | Steganography | medium | 200 | 10:28 | `OWASP{th3_l4st_s0ul_w4s_n3v3r_l0st}` |
| 5 | [Soul Memory](Soul-Memory/) | Forensics | easy | 100 | 10:30 | `OWASP{s0ul_m3m0ry_n3v3r_d13s}` |
| 6 | [Echoes of the Snap](Echoes-of-the-Snap/) | Forensics | medium | 200 | 10:33 | `OWASP{3ch03s_0f_th3_sn4p_r3m41n}` |
| 7 | [Mem-1: When It Happened](Mem-1-When-It-Happened/) | Forensics | easy | 100 | 11:06 | `OWASP{2026-10-08 05:07:43}` |
| 8 | [Mem-2: Soul Hunt](Mem-2-Soul-Hunt/) | Forensics | medium | 200 | 11:14 | `OWASP{SoulHunt_7F31}` |
| 9 | [Mem-3: The Painted Soul](Mem-3-The-Painted-Soul/) | Forensics | hard | 300 | 16:11 | `OWASP{soulstone_memory_84c2}` |
| 10 | [Soul's Whisper](Souls-Whisper/) | Reverse Engineering | easy | 100 | 16:13 | `OWASP{th3_s0ul_st0n3_wh1sp3r}` |
| 11 | [Soul in the Shadows](Soul-in-the-Shadows/) | Steganography | easy | 100 | 16:13 | `OWASP{the_soul_was_here}` |
| 12 | [Mem-4: A Fragment in Memory](Mem-4-A-Fragment-in-Memory/) | Forensics | hard | 250 | 16:21 | `OWASP{soulstone_cmd_741f}` † |
| 13 | [Mem-5: The Last Trace](Mem-5-The-Last-Trace/) | Forensics | medium | 200 | 16:25 | `OWASP{soulstone_web_8b2d}` |
| 14 | [Mem-6: The Forgotten Note](Mem-6-The-Forgotten-Note/) | Forensics | medium | 250 | 16:25 | `OWASP{soulstone_note_3c91}` |
| 15 | [Invisible Signal](Invisible-Signal/) | Steganography | medium | 200 | 16:31 | `OWASP{Sou15_c4nt_b3_533n_bY_n0rm41_3y3s}` |
| 16 | [Soul Forge](Soul-Forge/) | Cryptography | easy | 100 | 16:34 | `OWASP{s0ul_f0rge_pr1m3s_4r3_n3v3r_r4nd0m}` |
| 17 | [Soul's Weakness](Souls-Weakness/) | Binary Exploitation | easy | 200 | 16:36 | `OWASP{S0ul_St0ne_Buff3r_0v3rfl0w}` |
| 18 | [Vormir Common Modulus](Vormir-Common-Modulus/) | Cryptography | easy | 100 | 16:38 | `OWASP{v0rm1r_tw1st3d_rsa_l34ks_th3_s0ul}` |
| 19 | [Red Skull's Trail](Red-Skulls-Trail/) | OSINT | easy | 100 | 16:38 | `OWASP{PhantomSoul}` |
| 20 | [Double Trouble](Double-Trouble/) | Cryptography | easy | 100 | 16:44 | `OWASP{soul_stone_claimed}` |
| 21 | [Return to Win](Return-to-Win/) | Binary Exploitation | easy | 100 | 16:45 | `OWASP{g3ts_1s_4_s3cur1ty_n1ghtm4r3}` |
| 22 | [Level 0 — First Fragment](Level-0-First-Fragment/) | General Skills | easy | 100 | 17:15 | `OWASP{Th3_f1rst_fr4gm3nt}` |
| 23 | [Level 1 — Shattered Memories](Level-1-Shattered-Memories/) | General Skills | easy | 100 | 17:32 | `OWASP{Sh4tt3r3d_m3m0r13s}` |
| — | Sacrifice | Forensics | easy | 100 | 17:48 | *(no write-up — excluded)* |

† **Mem-4** value is a reconstruction from the dump's flag family; see that write-up for the one unused family member (`OWASP{soulstone_net_4d92}`) in case the accepted value differs.

## Notes on the memory series (Mem-1 … Mem-6)
All six "Mem" challenges + the memory-forensics artifacts come from a **single 2.6 GB Windows memory dump** (`soul.mem`, from the shared challenge "Echoes of Vormir"). Mem-1 and Mem-2 are the original author write-ups; Mem-3…6 were reconstructed here from the extracted artifacts (painted image, browser history, expedition note) and by string-scanning the raw dump. Each Mem folder includes the specific artifact(s) it needs.

The full dump itself (`soul.mem` / `soul.zip`, ~1–2.6 GB) is **not** copied into these folders to keep them portable; it lives in `../ECHOES-OF-VORMIR/`.
