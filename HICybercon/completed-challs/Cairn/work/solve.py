#!/usr/bin/env python3
# Cairn (HI CyberCon 2026) -- isogeny-labyrinth walk solver
# Walk: j_{i+1} = root index h[1] mod n of Phi_l(j_i, Y), l = L[h[0] mod 4], h=SHA256(ser(j_i)||BE8(i)||salt)
# Fast root extraction: factor F(Y) = f(Y)*conj(f(Y)) over GF(p) into min-polys (deg 1/2), then gcd(f, q) over GF(p^2).
import json, time, hashlib, os, sys
import cypari2

WORK = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(WORK, "challenge files", "challenge.json")))
p = int(D["p"]); j0 = D["j0"]; salt = bytes.fromhex(D["salt_hex"])
T = int(D["T"]); L = [int(x) for x in D["L"]]
PHI = {int(k): [(int(a), int(b), int(c)) for a, b, c in v] for k, v in D["phi"].items()}
ct = __import__("base64").b64decode(D["ciphertext_b64"])
nonce = __import__("base64").b64decode(D["nonce_b64"])
tag = __import__("base64").b64decode(D["tag_b64"])

pari = cypari2.Pari(); pari.allocatemem(1 << 31)
m = f"Mod(1,{p})"
af = pari.ffgen(pari(f"{m}*y^2 + {m}"), "y")
Xv = pari("X"); Zv = pari("Z"); Tv = pari("T")
ZERO = pari(0) + 0 * af

def build_phi(terms):
    s = "0"
    for xe, ye, c in terms:
        s += f" + ({c % p})*X^{xe}*Z^{ye}"
    return pari(s)
PHIP = {l: build_phi(t) for l, t in PHI.items()}

def conj(z): return pari.lift(pari.trace(z)) - z

def roots_at(j, l):
    """sorted (a,b) list of distinct roots of Phi_l(j,Y) over GF(p^2)."""
    jgen = pari(j[0]) + pari(j[1]) * af
    f = pari.subst(PHIP[l], Xv, jgen)
    d = int(pari.poldegree(f))
    fc = pari.Polrev([conj(pari.polcoeff(f, i)) for i in range(d + 1)], Zv)
    F = f * fc
    df = int(pari.poldegree(F))
    Fp = pari.Polrev([pari.Mod(pari.lift(pari.trace(pari.polcoeff(F, i)) / 2), p)
                      for i in range(df + 1)], Tv)
    fac = pari.factor(Fp)
    roots = []
    for k in range(len(fac[0])):
        q = fac[0][k]; dq = int(pari.poldegree(q))
        qq = pari.Polrev([pari.polcoeff(q, i) + ZERO for i in range(dq + 1)], Zv)
        g = pari.gcd(f, qq)
        dg = int(pari.poldegree(g))
        if dg == 1:
            cand = [-pari.polcoeff(g, 0) / pari.polcoeff(g, 1)]
        else:
            # both roots of q are roots of f -> factor q over GF(p^2)
            fq = pari.factor(qq)
            cand = []
            for kk in range(len(fq[0])):
                fk = fq[0][kk]
                if int(pari.poldegree(fk)) == 1:
                    cand.append(-pari.polcoeff(fk, 0) / pari.polcoeff(fk, 1))
        for r in cand:
            a = int(pari.lift(pari.trace(r) / 2)); w = (r - pari(a)) * (-af)
            b = int(pari.lift(pari.trace(w) / 2))
            roots.append((a, b))
    roots.sort()
    return roots

def ser(j):
    return j[0].to_bytes(32, 'little') + j[1].to_bytes(32, 'little')

CKPT = os.path.join(WORK, "ckpt.txt")

def solve(start_idx, j, upto):
    """Run steps [start_idx, upto). Checkpoints every 4096 steps of THIS run."""
    t0 = time.time(); done = 0
    for idx in range(start_idx, upto):
        h = hashlib.sha256(ser(j) + idx.to_bytes(8, 'big') + salt).digest()
        l = L[h[0] % 4]
        rts = roots_at(j, l)
        j = rts[h[1] % len(rts)]
        done += 1
        if done % 4096 == 0 or idx == upto - 1:
            with open(CKPT, "w") as fh:
                fh.write(f"{idx+1} {j[0]} {j[1]}\n")
            rate = done / (time.time() - t0)
            print(f"[cairn] idx={idx+1} rate={rate:.1f}/s eta={(upto-idx-1)/rate/60:.1f}min j={j[0]%1000000}", flush=True)
    return j

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    if mode == "validate":
        N = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        # compare fast vs direct for N steps
        def roots_direct(j, l):
            jgen = pari(j[0]) + pari(j[1]) * af
            f = pari.subst(PHIP[l], Xv, jgen)
            fac = pari.factor(f); roots = []
            for k in range(len(fac[0])):
                fk = fac[0][k]
                if int(pari.poldegree(fk)) == 1:
                    r = -pari.polcoeff(fk, 0) / pari.polcoeff(fk, 1)
                    a = int(pari.lift(pari.trace(r) / 2)); w = (r - pari(a)) * (-af)
                    roots.append((a, int(pari.lift(pari.trace(w) / 2))))
            roots.sort(); return roots
        j = (j0[0] % p, j0[1] % p); mism = 0; t0 = time.time()
        for idx in range(N):
            h = hashlib.sha256(ser(j) + idx.to_bytes(8, 'big') + salt).digest()
            l = L[h[0] % 4]
            rd = roots_direct(j, l); rf = roots_at(j, l)
            if rd != rf:
                mism += 1
                if mism <= 3: print("MISMATCH", idx, l, rd, rf)
            j = rd[h[1] % len(rd)]
        dt = time.time() - t0
        print(f"validate N={N} mismatch={mism} fast_per_step_ms={1000*(dt/N - 0):.2f} (incl direct) jT={j}")
    else:
        start = 0; j = (j0[0] % p, j0[1] % p); upto = T
        if mode == "resume" and os.path.exists(CKPT):
            line = open(CKPT).read().split()
            start = int(line[0]); j = (int(line[1]), int(line[2]))
            print("resuming from", start)
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            upto = int(sys.argv[2])
        jf = solve(start, j, upto)
        print("FINAL jT =", jf)
        key = hashlib.sha256(ser(jf) + b"IsogenyLabyrinth").digest()
        print("key =", key.hex())
        try:
            from Crypto.Cipher import AES
            c = AES.new(key, AES.MODE_GCM, nonce=nonce)
            pt = c.decrypt_and_verify(ct, tag)
            print("FLAG:", pt.decode())
        except Exception as e:
            print("AES decode error:", e)