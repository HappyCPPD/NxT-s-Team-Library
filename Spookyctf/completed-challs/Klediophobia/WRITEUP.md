# Klediophobia — SpookyCTF 2026 (crypto, 741 pts, 25 solves)

Flag: `spooky{4T_L345T_1T_15NT_F0UR}`

## TL;DR
The "unusual event" in the HSM log (`HSM WRAP` then `HSM UNWRAP ... handler=compat-restore`
on `OBJ-0003`) means intermediate key ST-ISS-03 was destroyed and re-created by a
"compatibility restore" path that used catastrophically weak randomness. Its private
scalar is tiny (`d = 1963`), so it is brute-forceable straight from the public
certificate. Recover `d`, sign the audit message, submit.

This mirrors the real Oct-2026 eMudhra/emSign intermediate-CA incident, where eight
intermediate keys were generated with **single-byte P-384 randomness**
(`d = 4, 56, 66, 115, 155, 156, 230, 237`).

## Artifacts
- `root.pem` — self-signed root CA (P-384)
- `ST-ISS-0{1..4}.pem` — four intermediates, all signed by the root
- `ST-ISS-0{1..4}.csr.pem` — the CSRs (self-signed by each intermediate key)
- `ceremony.log`, `key-inventory.csv`, `client.py`

Everything looks cryptographically perfect: all signatures verify, no ECDSA nonce is
reused anywhere (all 9 `r` values distinct), each CSR pubkey == its cert pubkey.

## The bug
`ceremony.log`:
```
KEY GENERATE object=OBJ-0003 curve=P-384
HSM WRAP object=OBJ-0003 mechanism=AES256-GCM
HSM UNWRAP source=OBJ-0003 object=OBJ-0003-R handler=compat-restore
CSR CREATE object=OBJ-0003-R certificate=ST-ISS-03
```
`key-inventory.csv` maps `ST-ISS-03.pem -> OBJ-0003-R`.

The key wrap/restore round-trip re-generated the P-384 scalar with almost no entropy.
Result: ST-ISS-03's private key is a small integer, recoverable by simply testing
`d = 1, 2, 3, ...` against the public key.

## Solve
Signatures/nonces were a red herring — none are reused and none are biased. The key
material itself is the weakness.

```python
import json, base64, urllib.request, urllib.error
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes

# 1) brute-force the weak intermediate key from its public certificate
cert = x509.load_pem_x509_certificate(open("ST-ISS-03.pem","rb").read)
target = cert.public_key.public_numbers
for d in range(1, 10_000_000):
 pn = ec.derive_private_key(d, ec.SECP384R1).public_key.public_numbers
 if (pn.x, pn.y) == (target.x, target.y):
 break # -> d == 1963
priv = ec.derive_private_key(d, ec.SECP384R1)

# 2) sign the fresh audit message and submit
SRV = "http://3.149.129.229:8000"
with urllib.request.urlopen(SRV + "/challenge", timeout=10) as r:
 ch = json.loads(r.read.decode)
sig = priv.sign(ch["message"].encode, ec.ECDSA(hashes.SHA384))
body = json.dumps({"session_id": ch["session_id"],
 "signature": base64.b64encode(sig).decode}).encode
req = urllib.request.Request(SRV + "/verify", data=body,
 headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req, timeout=10).read.decode)
```
Output:
```
{"result": "VALID", "flag": "spooky{4T_L345T_1T_15NT_F0UR}"}
```

Working solver: `solve.py` in this directory.

## Lesson
When ECDSA artifacts are "clean" (no nonce reuse, no nonce bias, valid chains), the
weakness is often the **key generation**, not the signatures. Check public keys for a
small discrete log before spending time on nonce lattices.

## Verification (re-ran against live server 2026-11-07)
`solve_fresh.py` independently brute-forces d from the cert (no hardcoded value),
confirms ST-ISS-01/02/04 have full entropy (no small d in 300k) and only ST-ISS-03
is weak (d=1963), then signs the live `/challenge` message:
```
ST-ISS-03.pem -> d = 1963
RESPONSE: {"result": "VALID", "flag": "spooky{4T_L345T_1T_15NT_F0UR}"}
```
