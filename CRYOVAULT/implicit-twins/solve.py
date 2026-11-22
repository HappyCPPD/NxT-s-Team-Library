#!/usr/bin/env python3
"""
implicit-twins solver.

N1 = p1*q1, N2 = p2*q2 with p1 == p2 (mod 2^T)  [shared low bits of p].
=> q1*N2 - q2*N1 = q1*q2*(p1-p2) == 0 (mod 2^T)
=> the small vector (q1, q2) lives in the 2D lattice
      L = { (a,b) : a*N2 - b*N1 == 0 (mod 2^T) }
   basis {(2^T, 0), (N1 * N2^-1 mod 2^T, 1)}   det = 2^T
Gauss-reduce => shortest vector ~ (q1, q2), then p1 = N1/q1, decrypt.
"""
import json, math
from fractions import Fraction

D = "implicit-twins/"
out = json.load(open(D + "output.json"))
N1, N2, e, ct = out["N1"], out["N2"], out["e"], out["ct"]


def gauss_reduce(v1, v2):
    def dot(a, b): return a[0]*b[0] + a[1]*b[1]
    def n2(a): return dot(a, a)
    while True:
        if n2(v2) < n2(v1):
            v1, v2 = v2, v1
        mu = round(Fraction(dot(v1, v2), n2(v1)))
        if mu == 0:
            return v1, v2
        v2 = (v2[0] - mu*v1[0], v2[1] - mu*v1[1])


def try_t(t):
    M = 1 << t
    inv = pow(N2, -1, M)            # N2 odd
    b2 = ((N1 * inv) % M, 1)
    b1 = (M, 0)
    w1, w2 = gauss_reduce(b1, b2)
    for (a, b) in (w1, w2, (-w1[0], -w1[1]), (-w2[0], -w2[1])):
        if a > 0 and b > 0 and N1 % a == 0:
            p1 = N1 // a
            if N2 % b == 0:
                return a, b, p1
    return None


found = None
for t in range(700, 300, -1):
    r = try_t(t)
    if r:
        q1, q2, p1 = r
        print(f"[+] hit at T={t}:  q1={q1}\n                q2={q2}")
        # verify
        if N1 % q1 == 0 and N2 % q2 == 0:
            p1 = N1 // q1
            p2 = N2 // q2
            if (p1 % (1 << 200)) == (p2 % (1 << 200)):
                print(f"[+] shared low bits confirmed (>=200)")
            phi = (p1 - 1) * (q1 - 1)
            d = pow(e, -1, phi)
            m = pow(ct, d, N1)
            pt = m.to_bytes((m.bit_length() + 7)//8, "big")
            print("[+] flag:", pt)
            open(D + "flag.txt", "wb").write(pt + b"\n")
            found = pt
            break
if not found:
    print("[-] no solution found")
