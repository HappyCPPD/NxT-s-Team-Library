#!/usr/bin/env python3
import socket, ssl
HOST="labyrinth-40a84c7462ba.chall.hiddeninvestigations.net"; PORT=1337
MAGIC=b"LBY\x7f"
def conn():
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    s=ctx.wrap_socket(socket.create_connection((HOST,PORT),timeout=10),server_hostname=HOST)
    s.settimeout(0.8)
    try:
        while True:
            c=s.recv(65536)
            if not c: break
    except socket.timeout: pass
    return s
def rx(s,t=0.8):
    s.settimeout(t); d=b""
    try:
        while True:
            c=s.recv(65536)
            if not c: return d+b"<EOF>"
            d+=c
    except socket.timeout: return d
def parse(d):
    if len(d)<8: return (None,None,None,d)
    return (d[4], int.from_bytes(d[5:7],'big'), d[7], d[8:])
def mk(op,pl=b""): return MAGIC+bytes([op])+len(pl).to_bytes(2,'big')+pl
def send(s,op,pl=b""):
    s.sendall(mk(op,pl)); return parse(rx(s))

s=conn()
_,_,_,pl=send(s,0x01); N=pl[:8]
st,ln,c,p=send(s,0x10,N)
data=p[:28]
G=[data[i:i+4] for i in range(0,28,4)]
cc=G[1][0]
print("c=",hex(cc))
def T(v): return bytes(x^cc for x in v)[::-1]
for i in range(3):
    print(f"check T(G{2*i}) ==", T(G[2*i]).hex(), "vs", G[2*i+1].hex(), T(G[2*i])==G[2*i+1])
chal=G[6]
ans=T(chal)
print("challenge", chal.hex(), "answer", ans.hex())
st,ln,c,p=send(s,0x30,ans)
print("op30 answer ->", f"st={st:02x} c={c}", p)
# maybe more steps
for i in range(10):
    st,ln,c,p=send(s,0x30,ans)
    print("op30 again ->", st, c, p)
    if b"<EOF>" in p: break
s.close()
