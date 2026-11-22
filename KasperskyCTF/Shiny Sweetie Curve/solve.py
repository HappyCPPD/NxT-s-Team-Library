"""
Riffle Royale ("Shiny sweetie curve") solver.

Usage:
    python3 solve.py "<comma-separated samples>" <target_index>

Prints the recovered x-coordinate of u + TARGET_INDEX*step (the LEFT/slot-0
hand card's value) to stdout; diagnostics go to stderr.

See WRITEUP.md in this folder for the full explanation.
"""
import sympy as sp
import itertools, math, time, sys

s_sym = sp.symbols('s')

def Rfun(xprev,xm,xnext):
    c2 = xnext+xprev-2*xm
    c1 = -2*xm*(xm+xnext+xprev)
    c0 = xm*xm*(xnext+xprev)
    return c2, c1, c0

def get_R_fast(xs, i1, i2, i3, i4):
    xprev1,xm1,xnext1 = xs[i1-1],xs[i1],xs[i1+1]
    xprev2,xm2,xnext2 = xs[i2-1],xs[i2],xs[i2+1]
    xprev3,xm3,xnext3 = xs[i3-1],xs[i3],xs[i3+1]
    xprev4,xm4,xnext4 = xs[i4-1],xs[i4],xs[i4+1]

    R1 = Rfun(xprev1,xm1,xnext1)
    R2 = Rfun(xprev2,xm2,xnext2)
    R3 = Rfun(xprev3,xm3,xnext3)

    D = 2*(xm1-xm2)
    if D == 0:
        return None
    Ra = (R1[0]-R2[0], R1[1]-R2[1], R1[2]-R2[2])

    DR1 = (D*R1[0], D*R1[1], D*R1[2])
    sRa = (Ra[0], Ra[1], Ra[2], 0)
    twoxm1Ra = (0, 2*xm1*Ra[0], 2*xm1*Ra[1], 2*xm1*Ra[2])
    two_s_Ra = (2*sRa[0], 2*sRa[1], 2*sRa[2], 2*sRa[3])
    twoterm = tuple(two_s_Ra[k]+twoxm1Ra[k] for k in range(4))
    DR1pad = (0, DR1[0], DR1[1], DR1[2])
    Rb = tuple(DR1pad[k]-twoterm[k] for k in range(4))

    negtwosRa = (-2*Ra[0], -2*Ra[1], -2*Ra[2], 0)
    negtwoxm3Ra = (0, -2*xm3*Ra[0], -2*xm3*Ra[1], -2*xm3*Ra[2])
    part1 = tuple(negtwosRa[k]+negtwoxm3Ra[k] for k in range(4))
    negRb = tuple(-Rb[k] for k in range(4))
    DR3 = (0, D*R3[0], D*R3[1], D*R3[2])
    F1c = tuple(part1[k]+negRb[k]+DR3[k] for k in range(4))

    F1poly = sp.Poly(F1c[0]*s_sym**3+F1c[1]*s_sym**2+F1c[2]*s_sym+F1c[3], s_sym)

    Ra_p = sp.Poly(Ra[0]*s_sym**2+Ra[1]*s_sym+Ra[2], s_sym)
    Rb_p = sp.Poly(Rb[0]*s_sym**3+Rb[1]*s_sym**2+Rb[2]*s_sym+Rb[3], s_sym)

    term1 = -(Ra_p*Ra_p)
    term2 = Ra_p * (2*xm4*D) * sp.Poly(s_sym, s_sym)
    term3 = Rb_p * (D) * sp.Poly(s_sym, s_sym)
    term4 = Rb_p * (xm4*D)
    c2 = -xm4*xm4+xnext4*xprev4
    c1 = -2*xm4*xnext4*xprev4
    c0 = xm4*xm4*xnext4*xprev4
    term5 = sp.Poly((D*D)*(c2*s_sym**2+c1*s_sym+c0), s_sym)

    F2poly = term1+term2+term3+term4+term5

    if F1poly.degree() < 1 or F2poly.degree() < 1:
        return None
    R = sp.resultant(F1poly, F2poly, s_sym)
    return int(R)

def search(samples):
    n = len(samples)
    x0 = samples[0]
    others_idx = list(range(1, n))
    best = None
    tried = 0
    t0 = time.time()
    for combo in itertools.combinations(others_idx, 6):
        tried += 1
        xs7 = [x0] + [samples[i] for i in combo]
        RA = get_R_fast(xs7, 1,2,3,1)
        if RA is None or RA == 0:
            continue
        RB = get_R_fast(xs7, 2,3,4,2)
        if RB is None or RB == 0:
            continue
        g = math.gcd(RA, RB)
        if g.bit_length() > 200:
            best = (combo, g, xs7)
            print(f"FOUND at tried={tried} combo={combo} gcd_bits={g.bit_length()}", file=sys.stderr)
            break
    print(f"search done, tried={tried}, time={time.time()-t0:.2f}s", file=sys.stderr)
    return best

def main():
    samples = [int(x) for x in sys.argv[1].split(',')]
    target_index = int(sys.argv[2])

    result = search(samples)
    if result is None:
        print("NOT_FOUND")
        return
    combo, g, xs7 = result
    print(f"combo(original indices, 0-based, samples[0] fixed as first)={combo}", file=sys.stderr)
    print(f"gcd={g}", file=sys.stderr)
    print(f"gcd bit_length={g.bit_length()}", file=sys.stderr)

    # factor out small cofactor if any (try to find the large prime factor)
    p_candidate = g
    for sp_ in [2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97]:
        while p_candidate % sp_ == 0:
            p_candidate //= sp_
    print(f"p_candidate after stripping small factors, bit_length={p_candidate.bit_length()}", file=sys.stderr)

    p = p_candidate
    is_prime = sp.isprime(p)
    print(f"is_prime(p) = {is_prime}", file=sys.stderr)

    xs7m = [x % p for x in xs7]

    def build_F1_F2_mod(xs, i1,i2,i3,i4,p):
        xprev1,xm1,xnext1 = xs[i1-1]%p,xs[i1]%p,xs[i1+1]%p
        xprev2,xm2,xnext2 = xs[i2-1]%p,xs[i2]%p,xs[i2+1]%p
        xprev3,xm3,xnext3 = xs[i3-1]%p,xs[i3]%p,xs[i3+1]%p
        xprev4,xm4,xnext4 = xs[i4-1]%p,xs[i4]%p,xs[i4+1]%p
        R1 = Rfun(xprev1,xm1,xnext1)
        R2 = Rfun(xprev2,xm2,xnext2)
        R3 = Rfun(xprev3,xm3,xnext3)
        D = (2*(xm1-xm2)) % p
        Ra = tuple((R1[k]-R2[k]) % p for k in range(3))
        DR1 = tuple((D*R1[k]) % p for k in range(3))
        sRa = (Ra[0], Ra[1], Ra[2], 0)
        twoxm1Ra = (0, (2*xm1*Ra[0])%p, (2*xm1*Ra[1])%p, (2*xm1*Ra[2])%p)
        two_s_Ra = tuple((2*v)%p for v in sRa)
        twoterm = tuple((two_s_Ra[k]+twoxm1Ra[k])%p for k in range(4))
        DR1pad = (0, DR1[0], DR1[1], DR1[2])
        Rb = tuple((DR1pad[k]-twoterm[k])%p for k in range(4))
        negtwosRa = tuple((-2*v)%p for v in (Ra[0],Ra[1],Ra[2]))+(0,)
        negtwoxm3Ra = (0, (-2*xm3*Ra[0])%p, (-2*xm3*Ra[1])%p, (-2*xm3*Ra[2])%p)
        part1 = tuple((negtwosRa[k]+negtwoxm3Ra[k])%p for k in range(4))
        negRb = tuple((-v)%p for v in Rb)
        DR3 = (0, (D*R3[0])%p, (D*R3[1])%p, (D*R3[2])%p)
        F1c = tuple((part1[k]+negRb[k]+DR3[k])%p for k in range(4))
        F1poly = sp.Poly([F1c[0],F1c[1],F1c[2],F1c[3]], s_sym, modulus=p)

        Ra_p = sp.Poly([Ra[0],Ra[1],Ra[2]], s_sym, modulus=p)
        Rb_p = sp.Poly([Rb[0],Rb[1],Rb[2],Rb[3]], s_sym, modulus=p)
        term1 = -(Ra_p*Ra_p)
        term2 = Ra_p * ((2*xm4*D)%p) * sp.Poly([1,0], s_sym, modulus=p)
        term3 = Rb_p * (D%p) * sp.Poly([1,0], s_sym, modulus=p)
        term4 = Rb_p * (xm4*D%p)
        c2 = (-xm4*xm4+xnext4*xprev4)%p
        c1 = (-2*xm4*xnext4*xprev4)%p
        c0 = (xm4*xm4*xnext4*xprev4)%p
        term5 = sp.Poly([(D*D%p)*c2%p,(D*D%p)*c1%p,(D*D%p)*c0%p], s_sym, modulus=p)
        F2poly = term1+term2+term3+term4+term5
        return F1poly, F2poly

    F1poly, F2poly = build_F1_F2_mod(xs7, 1,2,3,1, p)
    g_poly = sp.gcd(F1poly, F2poly)
    print(f"gcd poly degree: {g_poly.degree()}, gcd poly: {g_poly}", file=sys.stderr)

    if g_poly.degree() != 1:
        print("UNEXPECTED_GCD_DEGREE", g_poly)
        return

    coeffs = g_poly.all_coeffs()
    lead, const = coeffs[0], coeffs[1]
    lead_inv = pow(int(lead) % p, -1, p)
    s_val = (-int(const) * lead_inv) % p
    print(f"s_val = {s_val}", file=sys.stderr)

    xprev1,xm1,xnext1 = xs7m[0],xs7m[1],xs7m[2]
    xprev2,xm2,xnext2 = xs7m[1],xs7m[2],xs7m[3]
    R1 = Rfun(xprev1,xm1,xnext1)
    R2 = Rfun(xprev2,xm2,xnext2)
    def evalpoly(c,sval,p):
        return (c[0]*sval*sval + c[1]*sval + c[2]) % p
    R1v = evalpoly(R1, s_val, p)
    R2v = evalpoly(R2, s_val, p)
    D = (2*(xm1-xm2)) % p
    Dinv = pow(D, -1, p)
    a_val = ((R1v - R2v) * Dinv) % p
    b_val = ((-2*(s_val+xm1)*a_val + R1v) * pow(4,-1,p)) % p
    print(f"a_val={a_val}", file=sys.stderr)
    print(f"b_val={b_val}", file=sys.stderr)

    def legendre(v,p):
        if v % p == 0: return 0
        return pow(v, (p-1)//2, p)

    ok_all = True
    for x in xs7m:
        v = (x**3 + a_val*x + b_val) % p
        leg = legendre(v, p)
        if leg != 1 and v != 0:
            ok_all = False
    print(f"all points valid QR: {ok_all}", file=sys.stderr)

    def ec_add(P1,P2,a,p):
        if P1 is None: return P2
        if P2 is None: return P1
        x1,y1=P1; x2,y2=P2
        if x1==x2 and (y1+y2)%p==0:
            return None
        if x1==x2 and y1==y2:
            if y1==0: return None
            k=(3*x1*x1+a)*pow(2*y1,-1,p)%p
        else:
            k=(y2-y1)*pow(x2-x1,-1,p)%p
        x3=(k*k-x1-x2)%p
        y3=(k*(x1-x3)-y1)%p
        return (x3,y3)

    def ec_mul(n,P,a,p):
        out=None
        base=P
        while n:
            if n&1:
                out = ec_add(out, base, a, p)
            base = ec_add(base, base, a, p)
            n >>= 1
        return out

    def modsqrt(v, p):
        # p ≡ 3 mod 4 for these curves, matches server.py's own sqrt trick
        return pow(v, (p+1)//4, p)

    x_u = xs7m[0]
    v_u = (x_u**3+a_val*x_u+b_val) % p
    y_u = modsqrt(v_u, p)
    assert (y_u*y_u) % p == v_u, "sqrt failed for u"

    v_s = (s_val**3+a_val*s_val+b_val) % p
    y_s = modsqrt(v_s, p)
    assert (y_s*y_s) % p == v_s, "sqrt failed for step"

    found_branch = None
    for sign_s in [1,-1]:
        ys = y_s if sign_s==1 else (p-y_s)%p
        U = (x_u, y_u)
        STEP = (s_val, ys)
        pt = U
        seq = [pt[0]]
        ok = True
        for _ in range(6):
            pt = ec_add(pt, STEP, a_val, p)
            if pt is None:
                ok = False
                break
            seq.append(pt[0])
        # only compare the first 6 points: those are the ones the search
        # actually validated. The 7th combo element wasn't checked and can
        # be wrong without affecting u/step recovery.
        if ok and seq[:6] == xs7m[:6]:
            found_branch = (U, STEP)
            print(f"MATCHED branch sign_s={sign_s}", file=sys.stderr)
            break

    if found_branch is None:
        print("NO_BRANCH_MATCHED")
        print("xs7m:", xs7m, file=sys.stderr)
        return

    U, STEP = found_branch
    jump = ec_mul(target_index, STEP, a_val, p)
    target_point = ec_add(U, jump, a_val, p)
    print(f"target_point={target_point}", file=sys.stderr)
    print(target_point[0])

main()
