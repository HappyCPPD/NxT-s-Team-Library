import ssl,socket,re,time
from gsp_crypto import access, KBUF
class Conn:
    def __init__(self, host, port=1337):
        ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        self.s=ctx.wrap_socket(socket.create_connection((host,port),timeout=20), server_hostname=host)
        self.s.settimeout(8); self.f=self.s.makefile('rwb',buffering=0)
        self.greeting=[]
        while True:
            l=self.f.readline().decode('utf-8','replace').rstrip('\n')
            if l=='' : break
            self.greeting.append(l)
            if l.startswith('OK') or l.startswith('ERR'): break
        self.nonce=bytes.fromhex(re.search(r'NONCE ([0-9a-fA-F]+)','\n'.join(self.greeting)).group(1))
    def send(self,c): self.f.write(c.encode()+b'\n')
    def readterm(self,t=8):
        self.s.settimeout(t); out=[]
        while True:
            try: l=self.f.readline().decode('utf-8','replace').rstrip('\n')
            except Exception: break
            if l=='': break
            out.append(l)
            if l.startswith('OK') or l.startswith('ERR'): break
        return out
    def cmd(self,c,t=8):
        self.send(c); return self.readterm(t)
    def auth(self):
        return self.cmd('AUTH '+access(KBUF,self.nonce).hex())
    def close(self):
        try: self.f.write(b'QUIT\n'); self.s.close()
        except Exception: pass
