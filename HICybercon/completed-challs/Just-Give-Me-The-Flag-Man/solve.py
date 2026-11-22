import base64, sys

A91 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!#$%&()*+,./:;<=>?@[]^_`{|}~"'

def b91decode(d):
    v, b, n, out = -1, 0, 0, bytearray()
    for c in d:
        p = A91.index(c)
        if v < 0:
            v = p
        else:
            v += p * 91
            b |= v << n
            n += 13 if (v & 8191) > 88 else 14
            while n > 7:
                out.append(b & 255); b >>= 8; n -= 8
            v = -1
    if v + 1:
        out.append((b | v << n) & 255)
    return bytes(out)

def rot47(s):
    return ''.join(chr(33 + (ord(c) - 33 + 47) % 94) if 33 <= ord(c) <= 126 else c for c in s)

def beaufort(s, k=12):
    out = ''
    for c in s:
        if c.isalpha():
            base = 65 if c.isupper() else 97
            c = chr((k - (ord(c) - base)) % 26 + base)
        out += c
    return out

path = sys.argv[1] if len(sys.argv) > 1 else 'extracted/chall.txt'
tokens = ''.join(open(path).read().split())

l1 = bytes.fromhex(tokens[::-1].translate(str.maketrans('uvwxyz', 'fedcba'))).decode()
print('[1] reversed atbash-hex :', l1)
l2 = base64.a85decode(l1).decode()
print('[2] ascii85             :', l2)
l3 = b91decode(rot47(l2)).decode()
print('[3] rot47 + base91      :', l3)
print('[4] beaufort key M      :', beaufort(l3))
