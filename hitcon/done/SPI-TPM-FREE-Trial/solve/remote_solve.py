import socket, hashlib, re, time, sys, os, random
HERE=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,HERE)
HOST=('spi-tpm-rev.chal.hitconctf.com',1337)
def _connect(retries=60):
    for att in range(retries):
        try: return socket.create_connection(HOST,timeout=20)
        except OSError: time.sleep(4)
    raise SystemExit('cannot connect')
def _pow(s):
    b=b''
    while b'nonce\n' not in b:
        d=s.recv(4096)
        if not d: raise EOFError('eof banner')
        b+=d
    pre=re.search(r'prefix ([0-9a-f]+)',b.decode()).group(1)
    pp=pre.encode(); salt=('spi-tpm-pow-v1:'+pre).encode(); n=0
    while int.from_bytes(hashlib.scrypt(pp+str(n).encode(),salt=salt,n=32768,r=8,p=1,dklen=32,maxmem=134217728),'big')>>248: n+=1
    s.sendall((str(n)+'\n').encode())
def read_until(s,pat,limit=300,idle=1.0):
    s.settimeout(idle); buf=b''; t0=time.time()
    while time.time()-t0<limit:
        try:
            d=s.recv(65536)
            if not d: break
            buf+=d
            if re.search(pat,buf): break
        except socket.timeout:
            if re.search(pat,buf): break
    return buf
def open_ready(retries=25):
    for i in range(retries):
        try:
            s=_connect(); _pow(s)
            b=read_until(s, rb'ready', limit=120)
            if b'budget' in b and b'ready' in b:
                print('session ready (attempt %d):'%(i+1), b[:120], flush=True); return s
            print('bad banner attempt%d:'%(i+1), b[:160], flush=True); s.close()
        except (OSError,EOFError) as e:
            print('attempt%d err %s'%(i+1,e),flush=True)
            try: s.close()
            except Exception: pass
        time.sleep(3)
    raise SystemExit('no ready session')
def cmd(s,c,limit=300):
    s.sendall((c+'\n').encode()); return read_until(s, rb'ready', limit=limit)
if __name__=='__main__':
    nw=992
    random.seed(2024)
    words=[random.getrandbits(32) for _ in range(nw)]
    pt=b''.join(w.to_bytes(4,'little') for w in words).hex()
    s=open_ready()
    o=cmd(s,'get_flag'); print('get_flag ->',o[:200],flush=True)
    m=re.search(r'([0-9a-fA-F]{40,})',o.decode('latin1')); flagblob=bytes.fromhex(m.group(1)) if m else None
    o=cmd(s,'encrypt 1 1 '+pt); print('encrypt resp head:',o[:120],flush=True)
    ms=re.findall(r'([0-9a-fA-F]{200,})',o.decode('latin1')); encblob=bytes.fromhex(ms[-1]) if ms else None
    print('enc len', len(encblob) if encblob else None, 'flag len', len(flagblob) if flagblob else None, flush=True)
    if encblob and flagblob:
        open(HERE+'/remote_flag.blob','wb').write(flagblob)
        open(HERE+'/remote_enc.blob','wb').write(encblob)
        open(HERE+'/remote_words.txt','w').write('\n'.join('%08x'%w for w in words))
        print('saved blobs', flush=True)
    o=cmd(s,'budget'); print('budget ->',o[:120],flush=True)