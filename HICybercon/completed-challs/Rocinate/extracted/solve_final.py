import json, random, itertools, sys, time
from mt import untemper, temper, twist
from untwist_fast import untwist

def value_of(ws):
    return sum(ws[j] << (32*j) for j in range(63)) + ((ws[63] >> 1) << 2016)

d = json.load(open('data.json'))
N = d['N']; a = d['a']; b = d['b']; Cs = d['Cs']; Zs = d['Zs']; Ts = d['Ts']
Kb = N.bit_length()
D = [a, b] + Cs
U1 = untemper(1)

def draw_words(v):
    g = v - 1
    w = [(g >> (32*j)) & 0xffffffff for j in range(63)]
    w.append(((g >> 2016) & 0x7fffffff) << 1)
    return w
W = [draw_words(v) for v in D]

def concat(j, L):
    out = []
    for m in range(j, j+L): out.extend(W[m])
    return out

def is_contig(j, L):
    w = concat(j, L)
    st = [untemper(x) for x in w[:624]]
    ns = twist(st)
    for p in range(64*L - 624):
        if (624+p) % 64 == 63: continue
        if temper(ns[p]) != w[624+p]: return False
    return True

# --- max corrupted relative index per K, measured empirically ---
def maxrel(Kmax):
    res = {}
    rnd = random.Random(999)
    out = [rnd.getrandbits(32) for _ in range(20000)]
    for A in range(6000, 6600, 37):
        st = [untemper(out[A+i]) for i in range(624)]
        cur = st
        for k in range(1, Kmax+1):
            cur = untwist(cur)
            lo = A - 624*k
            if lo < 0: break
            rel = [i for i in range(624) if temper(cur[i]) != out[lo+i]]
            res[k] = max(res.get(k, 0), max(rel) if rel else 0)
    return res
MR = maxrel(7)
print('maxrel per K:', MR)

runs = []
for L in (11, 10):
    for j in range(len(D)-L+1):
        if is_contig(j, L):
            runs.append((j, L))
print('runs:', runs)

def try_solve(r0, e):
    if pow(r0, e, N) != Ts[0]: return None
    r = [r0]
    for _ in range(99):
        r.append((a*r[-1] + b) % N)
    for i in range(100):
        if pow(r[i], e, N) != Ts[i]: return None
    # extended euclid over Cs
    from math import gcd
    g = 0
    for c in Cs: g = gcd(g, c)
    # bezout combination
    coeffs = [1]
    cur = Cs[0]
    for i in range(1, 100):
        x, y = cur, Cs[i]
        # extended gcd
        old_r, rr = x, y; old_s, s = 1, 0; old_t, t = 0, 1
        while rr:
            q = old_r // rr
            old_r, rr = rr, old_r - q*rr
            old_s, s = s, old_s - q*s
            old_t, t = t, old_t - q*t
        gg = old_r; u = old_s; v = old_t
        coeffs = [c*u for c in coeffs] + [v]
        cur = gg
    g = cur
    # s**g = prod A_i**coeff_i
    prod = 1
    for i in range(100):
        Ai = Zs[i] * pow(r[i], -1, N) % N
        prod = prod * pow(Ai, coeffs[i], N) % N
    # prod = s**g ; if g==1 -> s
    if g == 1:
        s = prod
    else:
        s = None
    return s, g, coeffs

beg = time.time()
for (j, L) in runs:
    run_words = concat(j, L)
    window = run_words[:624]
    base = [untemper(w) for w in window]
    trunc = [i for i in range(624) if i % 64 == 63]
    fwd = run_words[624:]
    npass = 0
    for combo in range(1 << len(trunc)):
        st = base[:]
        for bit, t in enumerate(trunc):
            if (combo >> bit) & 1: st[t] ^= U1
        tw = twist(st)
        ok = True
        for p in range(len(fwd)):
            if (624+p) % 64 == 63: continue
            if temper(tw[p]) != fwd[p]: ok = False; break
        if not ok: continue
        npass += 1
        for T in range(18, 46):
            A = 64*T
            K = -(-A // 624)
            lo = A - 624*K
            mr = MR.get(K, 600)
            need = 64*6
            if lo + mr > -1: continue
            if lo + 623 < need: continue
            cur = st
            for _ in range(K): cur = untwist(cur)
            rooms = lo + 623
            acc = []
            pos = 0
            while pos + 63 <= rooms:
                ws = [temper(cur[pos-lo+i]) for i in range(64)]
                g = value_of(ws)
                if g < N: acc.append(1+g)
                pos += 64
                if len(acc) >= 2: break
            if len(acc) < 2: continue
            r0, e = acc[0], acc[1]
            res = try_solve(r0, e)
            if res:
                s, g, coeffs = res
                print('FOUND j=', j, 'L=', L, 'T=', T, 'combo=', combo, 'r0=', r0, 'e=', e, 'g=', g)
                if s is not None:
                    print('s =', s)
                    print('bytes =', s.to_bytes((s.bit_length()+7)//8, 'big'))
                sys.exit(0)
    print(f'run j={j} L={L}: {npass} passing LSB combos, elapsed {time.time()-beg:.1f}s')
print('no solution found')
