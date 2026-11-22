# Cyberphobia: SpOoKy KeYsTrEaMs

Category: crypto | Points: 405 | Difficulty: easy
Flag: spooky{cs351JKS} (challenge name: Cyberphobia: SpOoKy KeYsTrEaMs)

## TL;DR
The provided `backup.py` encrypts with AES-CTR using a *fixed* nonce
(`nonce=b"ghost123"`, `initial_value=0`) and the same key for every message.
AES-CTR keystream depends only on (key, nonce, counter), so every message is
XORed with the SAME keystream. `data.txt` leaks a known plaintext
("The haunted vault closes at midnight. Stay outside.") alongside the
encrypted message and the encrypted flag.

## Steps
1. keystream = known_plaintext XOR encrypted_message (both 64 bytes).
2. flag = encrypted_flag XOR keystream.

```python
known = bytes.fromhex("...") # known message (64 bytes)
enc_msg = bytes.fromhex("...")
enc_flag = bytes.fromhex("...")
ks = bytes(a^b for a,b in zip(known.ljust(64,b" "), enc_msg))
flag = bytes(a^b for a,b in zip(enc_flag, ks))
print(flag.decode.strip) # spooky{cs351JKS}
```

Solver: `solve.py`.

## Lesson
CTR/OFB/CFB are *stream* ciphers: never reuse a (key, nonce) pair. A single
known plaintext under the same nonce recovers the keystream and breaks
everything else. The known-plaintext-to-keystream attack is a 3-line job.
