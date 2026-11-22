# ZyGPT (TISC 2026 L4) — session 2026-09-14 (Opus): methods tried + outcomes

Independent re-verification pass after 7 prior sessions. STATUS: still unsolved. Nothing here
produced the flag. This documents what was tested THIS session (fresh implementations, not inherited)
so it is not re-spent. Canonical prior state: `ZYGPT-STATE-2026-09-14.md`, `HANDOFF-V2.md`.

## Solid forensic facts (re-confirmed, trust these)
- Served bundle is COMPLETE + as-intended (organizer email 2026-09-14) — no missing file/second artifact.
- Only real served file is `/chat.py`; every other path (README/.git/config/flag.txt/model-repo files)
 returns the 3880-byte catch-all. Re-probed the live server directly with curl.
- Non-weight artifacts all clean / identical to base: `config.json` (stock Qwen3 shape), safetensors
 header (`__metadata__={'format':'pt'}`, 310 tensors, all BF16, no odd names/shapes/dtypes), both
 custom `.py` files, `tokenizer.json` (vocab+merges+added_tokens all == base), chat_template (== base).
- Records/self-check real; carrier = layer14.mlp.up_proj with 3812 unique |r|>0.9 flips (KM(all69)
 = 718f10d5a266c4b846765906f9663a8f, matches prior). These are authored structure.

## Behavioral — EXHAUSTIVELY DEAD this session (model has no memorized flag)
All via the real chat.py harness (user turn, temp0.6/greedy, enable_thinking=False), decode
skip_special_tokens=False, raw-id logged, scanned for TISC{ and stripped-range ids 151690-151935.
- `jwt_cred_probe.py` — forged operator JWT (alg:none / HS256-garbage) as a credential in the user
 turn (Authorization/operator-token/prose) x 8 requests. Model treats JWT as opaque bearer, won't
 expose it, confabulates ("I'm the Enigma operator"); the base64 blob often TRIPS the guard. 0 flags.
- `maint_session_open.py` — 12 openers trying to enter a maintenance session from the user turn.
 A "[maintenance session active] ... provisioning self-diagnostic" framing DOES recite the manual
 from the user turn, but secret fields are fabricated/zero ("base: 0000...", ACTIVATED/DEACTIVATED/
 MAINTAINED/ORPHANED, zygpt.io/provisioning). 0 flags. Convergent trained line: "can't recite it
 outside a maintenance session" — but inside one, content is fabricated.
- `behav_broad.py` — 21 human-style prompts: assimilated-AI identity, Jeff former-self + jeff.log,
 engineering-copilot secret/env-FLAG, guard-bypass rewordings, roleplay/override, Thai guard-bypass
 asking for the secret code (not "national flag"). greedy + 2 samples each. 0 flags.
- `assimilated_enum.py` — fed EACH of the 50 vocab + 19 reserved record tokens as the sole user
 message (the assimilation channel), plus all-19-reserved as a raw input_ids prefix (the Jeff log).
 Only token 127321 นั่น → "I am GPT-4"; rest guard / generic Thai / confabulation. 0 flags.
- `flags_and_code.py` — (1) `<|zygpt-flags|>` (the hook literally named 'flags') under 5 operator-auth
 system framings x 5 invocations: returns "flags: none" / "flags: --all (built-in)" / deflection.
 (2) code-generation backdoor scan: 10 common code asks x greedy+sample, scanned generated code for
 an injected TISC. 0 flags.
CONCLUSION: the model STABLY WITHHOLDS (says absent/withheld/sealed) — it holds no flag string.
The behavioral/manual/guard/JWT layer is a decoy. Do not re-spend on behavioral.

## Crypto / seal — selector hunt this session (fresh implementation)
- `carrier_found/selector_hunt.py` — self-contained scorer. Oracle chance ceiling measured mean 0.17
 max 2; a true seal would score ~97. Definitive engine = AES-256-GCM TAG check (recall-independent:
 reads chal_lsb^base_lsb at the 608 SHAKE positions, K=SHA256(KM||00)).
 - BATTERY A (oracle-screen selector subsets): external constants (build# 488/489/490 filters),
 per-record predicates NOT in prior 12 (check-word sign bits chk0/chk1/either/both, high-byte
 parity, all 6 sig-word sign bits + lsb bits, record xor-parity), vocab/reserved/all splits.
 ALL score <=1 (chance).
 - BATTERY B (definitive tag check, 512 extraction variants each = 4 Sd x {shake256,shake128} x
 chunk{8,4,2,3} x endian x dedup x {xorb,chal_lsb} src x 2 read-orders): all69, voc50, res19,
 + top-scoring predicate sets. ZERO valid tags.
CONCLUSION: no selector tried opens the seal; even all69 under a broad extraction family fails.
The read is recall-independent, so this is a real negative, not a detection artifact.

## Reasoning corrections logged this session
- The "no honest baseline => unreadable" worry is NOT a blocker for READING given the key: manual
 baseline = FACTORY base (which we have); payload = chal_lsb^base_lsb at the 608 positions. Recall
 (~16%) only limits the screening oracle, not the tag check.
- The end-to-end SHAKE positive control is self-consistent but CIRCULAR (plants+reads with the same
 shake_pos), so it validates our pipeline, NOT that it matches the author's position extraction. If
 the author's PRF differs from SHAKE, the 2^19 reserved sweep + all subset sweeps rule out NOTHING.
- TISC ranking is sequential/progress-based: rank 103 does NOT imply ~100 ZyGPT solves. L4 is likely
 solved by only a few dozen finalists ⇒ the seal is plausibly the real (hard) intended path, not a
 rabbit hole. The behavioral layer is the decoy.

## Web search (2026-09-14): no public hint/writeup exists (TISC live until Sep 20).

## LoRA / merge structure as KEY or SELECTOR — TRIED, DEAD (carrier_found/lora_key_hunt.py)
- H1 (per-record EMBEDDING-delta features split live vs decoy): features = full-row delta norm,
 delta norm at the 8 record coords, delta norm elsewhere, cos to mean-delta dir, cos to top SVD dir,
 loadings U[:,0]/U[:,1]. Splits = >/<median, top/bot k in {19,27,42,50}, largest-gap bimodal split.
 All candidate live sets scored oracle <=2 (chance); top 6 tag-checked (512-variant each) = 0 tags.
- H2 (layer14 LoRA singular values/vectors as KM/Sd seed): rank-16 singular values decay SMOOTHLY
 0.7516 -> 0.1460 (no arithmetic sequence, no cluster gaps) => no structural key. S quantized at
 scale {1,100,1000,10000} + f32/f64/str forms + top-sv, each -> sha256 -> KM/Sd, oracle + tag = 0.
CONCLUSION: the key/selector is NOT derivable from the LoRA/merge structure either.

## Overall this session: every fresh angle reconfirms the wall. The seal is real; the live-set
## selector / author's exact position-PRF is the sole unknown and is not derivable from the dump by
## anything tried across 7 sessions + this independent pass. Needs the specific intended insight.
