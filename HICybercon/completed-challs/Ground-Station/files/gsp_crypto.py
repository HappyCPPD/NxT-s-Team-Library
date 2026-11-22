import struct

def rol32(x, n):
    x &= 0xffffffff; n &= 31
    return ((x << n) | (x >> (32 - n))) & 0xffffffff

def key_expand():
    seed = 0x1f2e3d4c; key = bytearray(16)
    for i in range(16):
        seed = (seed * 0x19660d + 0x3c6ef35f) & 0xffffffff
        key[i] = ((seed >> 0x11) ^ (i * 0x5b)) & 0xff
    return bytes(key)

def access(inp16, key):
    """inp16: 16-byte vector; key: >=8 bytes. Returns 8-byte response."""
    a, b, c, d = struct.unpack('<4I', inp16[:16])
    e, f = struct.unpack('<2I', key[:8])
    for i in range(12):
        a = rol32(a + e, 7); b = rol32(b ^ a, 11)
        c = rol32(c + b + f, 17); d = rol32(d ^ c, 19)
        e = (e + d + i * 0x9e3779b9) & 0xffffffff
        f = rol32(f ^ a, 13)
        a, b, c, d = b, c, d, a
    return struct.pack('<II', a ^ c, b ^ d)

KBUF = key_expand()
FIXVEC = bytes.fromhex('4753432d37000123011b033b54000000')
if __name__ == '__main__':
    print('KBUF  ', KBUF.hex())
    print('sig   ', access(KBUF, FIXVEC)[:4].hex(), '(expect de8c1297)')
