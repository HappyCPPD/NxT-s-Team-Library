import json, hashlib, hmac, itertools, string
from eth_keys import keys
from eth_utils import keccak
from eth_abi import encode as abi_encode, decode as abi_decode

N=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
LIVENESS=keccak(b'custody-desk/authorizer/liveness/v1')
ESCROW_DOMAIN=keccak(b'custody-desk/authorizer/escrow/v1')

txs=json.load(open('parsed.json'))
for t in txs:
    t['dataB']=bytes.fromhex(t['data']); t['toB']=bytes.fromhex(t['to']) if t.get('to') else b''
by_n={t['n']:t for t in txs}
AUTH_A='5ebbf52ec4b7f4148f46a1eb6f753fe3498516eb'
AUTH_B='cac5bbcb8a4b57fca03f71a8eeb64be756d6327c'

def auth_sig(t,auth):
    rid,amt,recip,v,r,s=abi_decode(['bytes32','uint256','address','uint8','bytes32','bytes32'], t['dataB'][4:])
    r=int.from_bytes(r,'big'); s=int.from_bytes(s,'big')
    dig=keccak(abi_encode(['address','bytes32','uint256','address'],[bytes.fromhex(auth),rid,amt,recip]))
    return v,r,s,dig

def rfc6979(d,h1):
    z1=(int.from_bytes(h1,'big')%N).to_bytes(32,'big')
    V=b'\x01'*32; K=b'\x00'*32; xb=d.to_bytes(32,'big')
    K=hmac.new(K,V+b'\x00'+xb+z1,hashlib.sha256).digest(); V=hmac.new(K,V,hashlib.sha256).digest()
    K=hmac.new(K,V+b'\x01'+xb+z1,hashlib.sha256).digest(); V=hmac.new(K,V,hashlib.sha256).digest()
    while True:
        T=b''
        while len(T)<32:
            V=hmac.new(K,V,hashlib.sha256).digest(); T+=V
        k=int.from_bytes(T[:32],'big')
        if 1<=k<N: return k

def ecdsa_raw(d,h1):
    z=int.from_bytes(h1,'big')
    k=rfc6979(d,h1)
    Rb=keys.PrivateKey(k.to_bytes(32,'big')).public_key.to_bytes()
    r=int.from_bytes(Rb[:32],'big')%N
    ypar=int.from_bytes(Rb[32:],'big')&1
    s=pow(k,-1,N)*(z+r*d)%N
    return r,s,ypar

def escrow_mask(v,r,s):
    return keccak(ESCROW_DOMAIN+r.to_bytes(32,'big')+s.to_bytes(32,'big')+bytes([v]))

# verify keys
def verify(priv_hex,auth,exp):
    d=int(priv_hex,16); ok=0;tot=0
    for t in txs:
        if t['to']==auth and t['dataB'][:4].hex()=='3dff6cbc':
            v,r,s,dig=auth_sig(t,auth); tot+=1
            try:
                a=keys.Signature(vrs=(v-27,r,s)).recover_public_key_from_msg_hash(dig).to_checksum_address()
            except Exception: a=None
            if a==exp: ok+=1
    return ok,tot

for name,priv,auth,sealn,blobn in [
    ('A', 'c0ecef7be0815db43cf992c33dce2b92739576089c31e30ce0c30ac2e2919e52', AUTH_A, 341, 341),
    ('B', '45f8c18e65d3d3a56937c52fefbbb4d57efbaab2555a605d5d3a6739b7b08d34', AUTH_B, 352, 352)]:
    d=int(priv,16)
    pk=keys.PrivateKey(d.to_bytes(32,'big')).public_key.to_checksum_address()
    print("\n#### Authorizer",name,"signer",pk)
    blob=abi_decode(['bytes32'], by_n[blobn]['dataB'][4:])[0]
    r,s,ypar=ecdsa_raw(d,LIVENESS)
    print("liveness r=%s"%hex(r))
    print("liveness s(unnorm)=%s"%hex(s))
    # running digest and masked_secret check needs storage; skip
    cands=[]
    for v in (27,28):
        for sv in ('s','neg'):
            ss = s if sv=='s' else N-s
            if ss>N//2 and sv=='s': pass
            m=escrow_mask(v,r,ss)
            plain=bytes(x^y for x,y in zip(blob,m))
            # printable score
            score=sum(1 for b in plain if 32<=b<127)
            cands.append((score,v,sv,m.hex(),plain))
    cands.sort(key=lambda x:-x[0])
    for score,v,sv,m,plain in cands:
        print(" score=%d v=%d s=%s mask=%s"%(score,v,sv,m[:16]))
        print("    plain:",repr(plain))
