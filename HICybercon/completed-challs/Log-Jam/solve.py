import hashlib, hmac, sys, json
from Crypto.Cipher import AES

p=0x7958085483c2736f23
g=0x2d738b6682dacc0bb7
h=0x36130f3996b8198135
nonce=bytes.fromhex("786fe3b966eb9949d0ded089")
ct=bytes.fromhex("dec59383508c24b2aa7c5ec44407720c8ac385af2dbc157b59a4113056f6b0b49abe300e822ffed923516e0d8eb77d49b55f")
tag=bytes.fromhex("469442d8157214b3ba95136e3a7e8082")

def try_gcm(key,label):
    if len(key) not in (16,24,32): return False
    try:
        c=AES.new(key,AES.MODE_GCM,nonce=nonce)
        pt=c.decrypt_and_verify(ct,tag)
        print("SUCCESS",label,key.hex(),pt)
        return True
    except Exception as e:
        return False

x=int(sys.argv[1]) if len(sys.argv)>1 else None
cands={}
if x is not None:
    cands['x_int_str']=str(x).encode()
    cands['x_hex']=format(x,'x').encode()
    for nb in (8,9,10,16,32):
        if x.bit_length()<=nb*8:
            cands[f'x_bytes{nb}']=x.to_bytes(nb,'big')
shared_variants={}
if x is not None:
    # shared secret variants
    shared_variants['g^x']=pow(g,x,p)
    shared_variants['h']=h
    shared_variants['x_pub']=x
allnames={}
for sn,sv in shared_variants.items():
    base=[]
    base.append(('dec',str(sv).encode()))
    base.append(('hex',format(sv,'x').encode()))
    base.append(('bytes8', sv.to_bytes(8,'big') if sv.bit_length()<=64 else None))
    base.append(('bytes9', sv.to_bytes(9,'big') if sv.bit_length()<=72 else None))
    base.append(('bytes16', sv.to_bytes(16,'big')))
    base.append(('bytes32', sv.to_bytes(32,'big')))
    for bn,bv in base:
        if bv is None: continue
        allnames[f'{sn}:{bn}']=bv

found=False
for n,bv in allnames.items():
    h256=hashlib.sha256(bv).digest()
    h512=hashlib.sha512(bv).digest()
    md5=hashlib.md5(bv).digest()
    for k,lab in [(bv,'raw'),(h256,'sha256'),(h512[:32],'sha512-32'),(h512[:16],'sha512-16'),(md5,'md5')]:
        if try_gcm(k, n+':'+lab): found=True
print("done, found=",found)
