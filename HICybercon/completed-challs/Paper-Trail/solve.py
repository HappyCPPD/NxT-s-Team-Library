# Paper-Trail solver: AES-128-CBC, key = trailer /ID[0], IV = /ID[1],
# ciphertext = the three long TJ runs (from their 3rd number) in stream order 179,180,181.
import json
from Crypto.Cipher import AES
P = json.load(open('payload.json'))
L = [l for o, l in P['lines']]
ct = bytes(x for i in (3, 9, 14) for x in L[i][2:])
key = bytes.fromhex('e3b51a3ba231502d79c55593eb522037')
iv = bytes.fromhex('6749db1175e3e659a640695dcc830c82')
pt = AES.new(key, AES.MODE_CBC, iv).decrypt(ct)
n = int.from_bytes(pt[4:6], 'big')
print(pt[6:6 + n].decode())
