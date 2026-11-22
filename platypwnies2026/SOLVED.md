# platypwnies 2026 — flags obtained (ledger)

Append under your own heading; don't rewrite others' sections.

## author / earlier work agent — live-confirmed flags

| Challenge | Cat | Flag |
|---|---|---|
| Matryoshka | rev | `PP{th3r3_1s_4_b1n4ry_1n_my_b1n4ry?!}` |
| Public Money, Public Exploits | forensics | `PP{n3x7_573p_publ1c_c0d3!_0p3n_y0ur_f0r3n51c5_pr_n0w::f7a4d9a3}` *(flag 1 of 3 — 2 more not yet located)* |
| Unholy Trinity (flag0) | crypto | `PP{modulo_hashing_is_not_collision_resistant::fGWQMe7UvDiF}` |
| Unholy Trinity (flag1) | crypto | `PP{rsa_messages_need_to_be_sufficiently_large::89gDoeIsXkoC}` |
| DEStruction (flag0) | crypto | `PP{D3S_c4nn07_s4v3_7runc473d_GCM_fr0m_c0llisi0ns::VQEMEM6L6nNb}` *(flag1 unreachable: needs H=E(0)))* |
| Ron's Revenge | crypto | `PP{st4t3s1z3_w4s_n0t_th3_m41n_pr0bl3m::MyazN90an3Fx}` |
| Diceware (warmup) | crypto | `PP{y0u_4r3_7h3_5rv3r_n0w::LEKgDiYHMyGN}` |
| Diceware (user) | crypto | `PP{k3y_r3u53_41l0wS_r3sp0ns3_r3u5e::JsvKvFPyfnuK}` |
| Diceware (admin) | crypto | `PP{g00d_r34ct10n_71m3::IvJY5DkQH3VN}` |
| Just in Time | blockchain | `PP{t1m3_15_n0t_4_s3cr3t::jrLLK4JVipAx}` |
| You're not my type | blockchain | `PP{n0t_my_typ3_0f_m0n3y::F9PGddRH88B6}` |
| PlatyLocker | blockchain | `PP{pr1v4t3_15_n0t_s3cr3t::nc8axkA1O7Db}` |
| Referral Program | blockchain | `PP{st0r4g3_c0ll1s10n_r3f3rr4l::xNasZukTMiNJ}` |
| PlatyPals | blockchain | `PP{r3r0ll_unt1l_l3g3nd4ry::YtgUAPznRLEk}` |
| Card Counting | blockchain | `PP{c0unt1ng_tw1st3d_c4rds::83WdaSTIBjUz}` |
| FS-Enc | reverse/crypto | `PP{f1l3_3ncrypt10n_1s_h4rd::knrpLH1NobCZ}` *(tool stores its derived key‖nonce in the file: magic‖key(32)‖nonce(12)‖ct‖tag; no password needed)* |

Solved by parallel effort (other agents): Bish Bash Bosh, Hold Your Horses, Fishies, Carbon, Flack Safety.

## Open on my side
- **May Day Fourth** — no exploit yet. 24-step MD4-like secret-IV MAC; only `iv0,iv1` (64 bits) are
 unknown (iv2,iv3 = key[8:16] leaked by the oracle). z3 AND bitwuzla both time out on the ARX
 inversion; needs a bespoke C brute-force/meet-in-the-middle.
- **Diceware** — exploit written and verified locally (3 flags); needs live web+wordlist URLs and a
 callback URL the container can reach inbound.
- **Public Money flags 2 & 3** — searched raw image, all 6 exfil payloads, 4.6 GB decompressed
 VM pages (WKdm/LZ4), and all vault/archive/JPEG markers: not present. Carrier files implied by the
 keychain (MetaMask vault `reader-donations`, 2nd SecureDrop `journalist-interface`, mail
 `ines.korvald`, pad `pad.spurweite`) are not resident in the image; likely APFS-resident only.
