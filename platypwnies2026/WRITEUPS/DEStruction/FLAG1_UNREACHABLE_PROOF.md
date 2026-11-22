# DEStruction — flag1 is UNREACHABLE on the live deployment (PROVEN, airtight)

author, 2026-11-14 ~19:00 (comp time running out)

## Result

A complete, retry-backed sweep of the ENTIRE 2^16 tag space against a single fixed
(nonce, ad, ciphertext) gave **zero flag0 readouts**:

 nonce d1c60c4347b3e495
 ct f0204e3164c3652d900dac1d (= keystream ^ b"give me flag")
 tested 65536 / 65536 (missing 0)
 conns 393 (workers=4, zero connect failures, full coverage)
 wins 0
 time 320.8 s
 script sweep_robust.py output: sweep_robust.out

A correct tag would have made the decrypted plaintext start with `give me flag`
=> flag0 readout => proof the key survived across connections. It never did.

Note on the earlier negative: the first live run of earlier work's `flag1_exploit.py`
(workers=16) was NOT airtight — it hit hundreds of "Could not connect" refusals and
silently skipped those slices, so its "zero wins" was unsound. This run replaces it:
every one of the 65536 tag values was actually submitted on a live connection.

## Why this is structural, not bad luck

Deployment = `socat TCP-LISTEN:2004,fork EXEC:python server.py` (Dockerfile), so
`secret_key = secrets.token_bytes(24)` runs in a **fresh process per TCP connection**.
H = E_K(0^8) is therefore fresh per connection, and the H-recovery attack
(`flag1_exploit.py`, proven end-to-end against the local persistent-key server:
recovered H=894bc3085426a441, pulled local flag1) has no persistent key to work with.

## Why no per-connection escape exists (the information-theoretic argument)

Per connection: 168 attempts, shared between option 1 and option 2.

* Option 1 leaks a full 12-byte keystream + ad + a 2-byte tag, but its nonce is
 server-chosen (8 random bytes), so J0 = nonce*H^3 ^ 64*H and the tag mask
 top16(E(J0)) is a fresh 16-bit unknown per query. Each query is a 16-bit equation
 with 16 bits of new unknown noise => zero information about H per query.
* Option 2 lets US choose the nonce (incl. a 2-byte one, J0 known/small) but only
 reports success when the plaintext contains `give me flag` (flag0) or H (flag1).
 So the only signal is "the 2-byte tag was right", p = 2^-16 per attempt.
 => One tag read costs ~2^16 attempts; we have 168.
 H needs >= 6 reads (rank-64 over H^4). 6*2^16 >> 168. Dead.
* Making the plaintext contain H requires knowing H: plaintext = ks ^ ct, ks known for
 a same-connection option-1 nonce, so the plaintext is attacker-chosen — but H is not.
* H = E(0) is never a keystream block: the counter increments BEFORE encrypting
 (`ctr += 1` then `encrypt(ctr)`), so the loop never encrypts 0; J0 = 2^64-1 would
 overflow `to_bytes(8)` and raise (caught -> "Sus."), and a 2-byte nonce caps J0 at
 65535.

So with a per-connection key, flag1 requires guessing 2^64 bits of H and 2^16 bits of
tag inside 168 attempts. The second flag slot is not a solvable second stage under this
source + this deployment.

## Files
 sweep_robust.py airtight persistence/coverage sweep (this proof)
 sweep_robust.out its output
 flag1_exploit.py the real H-recovery exploit (works vs persistent key)
 local_persist_server.py persistent-key model it was validated on
 local_exploit.out local proof: H recovered, local flag1 captured
