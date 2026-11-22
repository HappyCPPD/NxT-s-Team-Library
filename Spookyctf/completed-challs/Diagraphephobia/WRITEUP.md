# Diagraphephobia

**Category:** crypto | **Flag:** `spooky{qaStaH_nuq}`

## Approach
AES-128-ECB. The key was the 16-byte Klingon subject string `lojmIt yIpoSmoH!` recovered from the challenge's certificate/subject metadata. Decrypting produced valid PKCS#7 padding and plaintext ending in the flag.

## Reproduction
```python
from Crypto.Cipher import AES
key = b"lojmIt yIpoSmoH!" # 16 bytes
ct = open('ciphertext.bin','rb').read
pt = AES.new(key, AES.MODE_ECB).decrypt(ct)
print(pt)
```
Valid PKCS#7 padding confirmed correct key; plaintext ends `spooky{qaStaH_nuq}`.
