#!/usr/bin/env python3
"""Solve Censored - Kaspersky CTF 2026.
Recovers sk from nonce leakage via diagnostic blob, then forges signature."""

import hashlib, math, secrets, json, subprocess, os, sys
from fpylll import IntegerMatrix, LLL

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'static'))
import supercoolcryptolib as crypto


def unmask_pv(cid_bytes, commitment, diag):
    pm = crypto.telemetry_mask(cid_bytes, commitment, b"patch", crypto.PATCH_BITS)
    rm = crypto.telemetry_mask(cid_bytes, commitment, b"resid", crypto.RESID_BITS)
    return ((diag['patch'] ^ pm) << crypto.RESID_BITS) | (diag['resid'] ^ rm)


def pv_to_nonce_bounds(pv, prof, calib, Q):
    """Convert profile_value to (lo, hi, mid, half) for the nonce."""
    PM = 1 << crypto.PROFILE_BITS
    TAU = crypto.TAU
    LS = crypto.LUT_SIZE
    slo = pv / PM
    shi = (pv + 1) / PM
    sigma = prof.sigma

    ln = []
    for i in range(LS + 1):
        param = TAU * i / LS
        trav = (param - calib.phase) % TAU
        theta = (TAU - trav) % TAU if calib.direction else trav
        ln.append(int(theta * Q / TAU))

    intervals = []
    for j in range(LS):
        if sigma[j+1] > slo and sigma[j] < shi:
            ds = sigma[j+1] - sigma[j]
            dn = ln[j+1] - ln[j]
            f_lo = max(0.0, (slo - sigma[j]) / ds)
            f_hi = min(1.0, (shi - sigma[j]) / ds)
            n_lo = ln[j] + int(f_lo * dn)
            n_hi = ln[j] + int(f_hi * dn)
            if n_lo > n_hi:
                n_lo, n_hi = n_hi, n_lo
            intervals.append((n_lo, n_hi))

    intervals.sort()
    merged = []
    for lo, hi in intervals:
        if merged and lo <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], hi))
        else:
            merged.append((lo, hi))

    if not merged:
        return 0, Q - 1, (Q - 1) // 2, (Q - 1) // 2

    lo, hi = merged[0]
    mid = (lo + hi) // 2
    half = max(1, (hi - lo) // 2)
    return lo, hi, mid, half


def solve():
    sd = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    env = {**os.environ, 'FLAG': 'kaspersky{testflag}'}
    proc = subprocess.Popen(
        [sys.executable, '-c',
         f'import sys,os;os.chdir({sd!r});sys.path.insert(0,".");import server;server.main()'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env)

    rl = lambda: proc.stdout.readline().strip()
    snd = lambda c: (proc.stdin.write((c + '\n').encode()), proc.stdin.flush())

    rl(); rl()  # banner
    snd("PUB"); pub = json.loads(rl())
    P = int(pub['p']); Q = int(pub['q']); G = int(pub['g']); y = int(pub['y'])
    quota = pub['quota']; cal = pub['calibration']
    cid = bytes.fromhex(cal['id'])
    mk = hashlib.sha256(b"calibration\x00" + cid).digest()
    ps = cal['phase_code'] ^ (int.from_bytes(mk[:2], "big") & (crypto.PHASE_STEPS - 1))
    dr = cal['direction_code'] ^ (mk[2] & 1)
    mat = (cal['affine_num'][0][0], cal['affine_num'][0][1],
           cal['affine_num'][1][0], cal['affine_num'][1][1])
    shf = (cal['shift_num'][0], cal['shift_num'][1])
    calib = crypto.Calibration(cid, mat, shf, ps, dr)
    prof = crypto.PathProfile(calib)

    print(f"Collecting {quota} signatures...")
    sigs = []
    for i in range(quota):
        msg = secrets.token_bytes(16)
        snd(f"SIGN {msg.hex()}"); resp = json.loads(rl())
        if not resp.get('ok'): break
        R = int(resp['R'])
        sigs.append({
            'msg': msg, 'R': R, 's': int(resp['s']),
            'diag': resp['diag'], 'c': crypto.challenge_hash(msg, R)
        })
    print(f"Got {len(sigs)} signatures")

    data = []
    for idx, sig in enumerate(sigs):
        pv = unmask_pv(cid, sig['R'], sig['diag'])
        lo, hi, mid, half = pv_to_nonce_bounds(pv, prof, calib, Q)
        a_i = (sig['s'] - mid) % Q
        data.append({'c': sig['c'], 'a': a_i, 'half': half})

    # Filter out degraded ranges and use best sigs
    data = [d for d in data if d['half'] < Q // 4]
    data.sort(key=lambda d: d['half'])
    n = min(len(data), 30)
    X = max(d['half'] for d in data[:n])
    halfX = X
    print(f"Using {n} signatures for lattice, X=2^{X.bit_length()-1}")

    # Build Q-scaled centered HNP lattice
    dim = n + 2
    M = IntegerMatrix(dim, dim)

    for i in range(n):
        M[i, i] = Q * Q
        M[n, i] = (data[i]['c'] % Q) * Q
        centered = (data[i]['a'] - halfX) % Q
        M[n+1, i] = centered * Q

    M[n, n] = X          # sk column (was X/Q in rational form)
    M[n+1, n+1] = X * Q  # bound column (was X in rational form)

    print("Running LLL...")
    LLL.reduction(M)

    # Extract sk: look for row where last column = X*Q
    target_last = X * Q
    found = None
    for i in range(dim):
        last_val = abs(M[i, dim - 1])
        sec_val = abs(M[i, dim - 2])
        if last_val == target_last and sec_val % X == 0:
            sk_cand = sec_val // X
            if 0 < sk_cand < Q and pow(G, sk_cand, P) == y:
                found = sk_cand
                break
            sk_cand = (-sec_val) // X
            sk_cand %= Q
            if 0 < sk_cand < Q and pow(G, sk_cand, P) == y:
                found = sk_cand
                break

    # Fallback: scan all entries for sk (divided by X or Q)
    if not found:
        for i in range(dim):
            for j in range(dim):
                v = abs(M[i, j])
                if v > 0 and v % X == 0:
                    sk_cand = (v // X) % Q
                    if pow(G, sk_cand, P) == y:
                        found = sk_cand; break
                if v > 0 and v % Q == 0:
                    sk_cand = (v // Q) % Q
                    if pow(G, sk_cand, P) == y:
                        found = sk_cand; break
            if found: break

    if not found:
        print("Failed to recover secret key.")
        proc.terminate()
        return

    print(f"Recovered secret key: {found}")

    # Forge signature for "give_me_gift"
    target_msg = b'give_me_gift'
    k = secrets.randbelow(Q - 1) + 1
    R = pow(G, k, P)
    c = crypto.challenge_hash(target_msg, R)
    s = (k + c * found) % Q
    snd(f"SUBMIT {target_msg.hex()} {R} {s}")
    result = json.loads(rl())
    
    if result.get('ok') and 'flag' in result:
        print(f"\nFLAG: {result['flag']}")
    else:
        print(f"\nResult: {json.dumps(result, indent=2)}")
    
    proc.terminate()


if __name__ == '__main__':
    solve()