import struct
exec(open("vm.py").read().split('if __name__')[0])

KEY=BLOB[0:16]
perm=[0,5,10,15,4,9,14,3,8,13,2,7,12,1,6,11]
phrase=BLOB[16:80]
keys=[phrase[16*r:16*r+16] for r in range(4)]
print("keys:", [k.hex() for k in keys])

def gf_inv(a):
    for v in range(1,256):
        if gmul(a,v)==1: return v
    return 0

M=[[2,3,5,1],[1,2,3,5],[5,1,2,3],[3,5,1,2]]

def matvec(M,x):
    out=[]
    for i in range(4):
        r=0
        for j in range(4):
            r^=gmul(M[i][j],x[j])
        out.append(r)
    return out

def matinv(A):
    n=4
    W=[row[:]+[1 if i==j else 0 for j in range(n)] for i,row in enumerate(A)]
    for col in range(n):
        piv=next(r for r in range(col,n) if W[r][col]!=0)
        W[col],W[piv]=W[piv],W[col]
        pinv=gf_inv(W[col][col])
        W[col]=[gmul(pinv,v) for v in W[col]]
        for r in range(n):
            if r!=col and W[r][col]!=0:
                f=W[r][col]
                W[r]=[W[r][c]^gmul(f,W[col][c]) for c in range(2*n)]
    return [row[n:] for row in W]

Minv=matinv(M)
print("Minv:",Minv)
for t in range(64):
    x=[(t*7+i*13)%256 for i in range(4)]
    assert matvec(Minv,matvec(M,x))==x
print("Minv verified")

def inv_round(T,r):
    u=[T[i]^keys[r][i] for i in range(16)]
    t=[0]*16
    for w in range(4):
        o=matvec(Minv,[u[4*w+j] for j in range(4)])
        for j in range(4): t[4*w+j]=o[j]
    st=[0]*16
    for i in range(16):
        st[perm[i]]=INV[t[i]]
    return st

T=list(KEY)
for r in (3,2,1,0):
    T=inv_round(T,r)
inp=bytes(T)
print("recovered input:",inp.hex())
res,steps,ctx=run_vm(inp)
print("VM result:",res)
print("final mem[0:16]:",ctx[0x40:0x50].hex())
print("key:            ",KEY.hex())
