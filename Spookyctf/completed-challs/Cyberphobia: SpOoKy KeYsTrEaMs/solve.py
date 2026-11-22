from Crypto.Cipher import AES

# backup.py: AES-CTR, fixed nonce=b"ghost123", initial_value=0, same key reused.
# => keystream(nonce) is identical for every message. Recover it from a known
#    plaintext, then XOR it off the encrypted flag.

KNOWN_MSG_HEX = "546865206861756e746564207661756c7420636c6f736573206174206d69646e696768742e2053746179206f7574736964652e20202020202020202020202020"
ENC_MSG_HEX   = "e4a8bb39921d6f0e3940a040ae22a1afc698fdeb3058ea8e1002fe25142227c6f7f018ddf3eb9ce75e69dbdc59720fcffd98a9c0bb9f03f0d644f34c68a4c306"
ENC_FLAG_HEX  = "c3b0b176910561033e16f151920887be9298bea77f0bafdd1043aa25596b6388beb75089fdebefb31f30db930c265c86b9dda7c0bb9f03f0d644f34c68a4c306"

known = bytes.fromhex(KNOWN_MSG_HEX)          # already 64 bytes (padded in the file)
enc_msg = bytes.fromhex(ENC_MSG_HEX)
enc_flag = bytes.fromhex(ENC_FLAG_HEX)

keystream = bytes(a ^ b for a, b in zip(known.ljust(64, b" "), enc_msg))
flag = bytes(a ^ b for a, b in zip(enc_flag, keystream))
print(flag.decode().strip())
