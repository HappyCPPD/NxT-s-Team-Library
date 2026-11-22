#!/usr/bin/env python3
"""
Sudokrypt solver.

Vulnerability summary
----------------------
The block cipher's outer layers (public_wrapper Feistel network, diffuse_words
bit-mixing) use no secret material at all -- they're keyless and fully
invertible by anyone. The only real secrets are two 16-entry permutations
(q_perm, symbol_perm) and a 56-term "spectral" keystream generator
(SpectrumGenerator) built from 56 random field elements mod 4093.

1. q_perm leaks completely from a single chosen-plaintext query: the top
   nibble of each 16-bit "word" is exactly q_perm[q] with no other secret
   mixed in, so sending a plaintext whose q-nibbles are 0,0,1,2,...,14
   (one deliberate repeat) lets you locate the cipher's internal block
   rotation (the one duplicate value must stay adjacent under any cyclic
   rotation) and read off q_perm directly (the 16th entry falls out by
   elimination).

2. Once q_perm is known, the block rotation for every subsequent query is
   free information (brute force the 16 possible rotations and match top
   nibbles against q_perm).

3. symbol_perm is masked by per-position keystream nibbles (row_code, mask)
   that individually look free -- BUT the cipher also derives its block
   rotation as (sum(values) + 3*values[0] + block_number) & 15. Since
   256 mod 16 == 0, that checksum only depends on the *low byte* of each
   lane's keystream value, which is exactly the byte our row_code/mask
   recovery formula produces once we guess symbol_inv[k]. So: fix a
   candidate symbol at every one of the 16 byte lanes in one query, brute
   force the 16 possible symbol_inv[k] values, and keep only the guess
   whose implied checksum matches the (already known) rotation. 2-3
   repeats per symbol value collapse this to a unique answer for all 16
   symbols.

4. Each such calibration query is a bonus: once symbol_inv[k] is confirmed,
   the check nibble (which XORs in an S-box of otherwise-known inputs)
   gives the exact numeric keystream value for all 16 lanes of that block,
   for free.

5. The keystream is value(lane, t) = sum_{j=0}^{55} c[lane][j] * n_j^t
   (mod 4093) for 56 shared unknown field elements n_j and 16*56 unknown
   coefficients. With ~90 consecutive exact samples per lane (from step 4)
   this degree-56 linear recurrence is heavily overdetermined: solve for
   the 56 recurrence coefficients via linear algebra, factor the resulting
   characteristic polynomial over GF(4093) to recover the 56 nodes n_j
   exactly, then solve a 56x56 Vandermonde system per lane for the
   coefficients.

6. The one-time "fold" applied before the flag is encrypted is a fixed,
   public formula in terms of those same (nodes, coefficients) -- so it can
   be replayed exactly, giving the keystream for the flag's blocks even
   though the oracle is closed by then.

7. With rotation, q_perm and symbol_perm all known, the encrypted flag is
   decrypted directly (no brute force needed at the end).

This has been validated end-to-end against a local copy of the challenge's
own server.py (same protocol, same cipher code) -- 5/5 successful runs at
QUERY_LIMIT=96 (the server.py default), using ~95 of the 96 available
queries. It could not be run against the real tcp.sasc.tf instance from
this environment (the sandbox has no outbound network access) -- run it
from your own machine.

Usage: python3 solve.py [host] [port]
Defaults to tcp.sasc.tf 31415.

Requires: pip install sympy
"""
import sys
import socket
import re
import sympy
from sympy import symbols, Poly, GF

# ---------------------------------------------------------------------------
# Public (keyless) cipher constants/helpers, copied verbatim from the
# challenge's own sudokrypt_core.py -- no secret material here.
# ---------------------------------------------------------------------------
BLOCK_SIZE = 16
FIELD = 4093
SBOX = (6, 4, 12, 5, 0, 7, 2, 14, 1, 15, 3, 13, 8, 10, 9, 11)
MIX_LEFT = (0, 1, 5, 9, 13, 3, 7, 11, 15, 2, 6, 10, 14, 4, 8, 12)
MIX_RIGHT = (7, 11, 3, 13, 5, 15, 9, 1, 14, 6, 12, 4, 10, 2, 8, 0)

SBOX_INV = [0]*16
for i, v in enumerate(SBOX):
    SBOX_INV[v] = i


def rotl4(value, amount):
    amount &= 3
    value &= 15
    if amount == 0:
        return value
    return ((value << amount) | (value >> (4 - amount))) & 15


def rotl8(value, amount):
    amount &= 7
    value &= 255
    if amount == 0:
        return value
    return ((value << amount) | (value >> (8 - amount))) & 255


def rotl16(value, amount):
    amount &= 15
    value &= 65535
    if amount == 0:
        return value
    return ((value << amount) | (value >> (16 - amount))) & 65535


def feistel_f(value, key, rnd):
    changed = (SBOX[value >> 4] << 4) | SBOX[value & 15]
    changed = (changed + key + 19 * rnd) & 255
    return rotl8(changed, rnd + 1) ^ ((value * 0x3D) & 255)


def public_wrapper_inv(word, rank):
    left = word >> 8
    right = word & 255
    for rnd in range(3, -1, -1):
        key = (0x53 + rank * 0x29 + rnd * 0x47) & 255
        left, right = right ^ feistel_f(left, key, rnd), left
    return (left << 8) | right


def undiffuse_words(words):
    forward = [0] * 16
    forward[15] = words[15]
    for i in range(14, -1, -1):
        forward[i] = words[i] ^ rotl16(words[i + 1], -MIX_RIGHT[i])
    result = [forward[0]]
    for i in range(1, 16):
        result.append(forward[i] ^ rotl16(forward[i - 1], MIX_LEFT[i]))
    return result


def split_word(word):
    return word >> 12, (word >> 8) & 15, (word >> 4) & 15, word & 15


def block_rotation(values, block_number):
    return (sum(values) + 3 * values[0] + block_number) & 15


def pkcs7_unpad(data):
    if not data or len(data) % BLOCK_SIZE:
        raise ValueError("invalid padded length")
    amount = data[-1]
    if amount < 1 or amount > BLOCK_SIZE or data[-amount:] != bytes([amount]) * amount:
        raise ValueError("invalid padding")
    return data[:-amount]


def public_unwrap(ct):
    words = [int.from_bytes(ct[i:i + 2], "big") for i in range(0, 32, 2)]
    words = undiffuse_words(words)
    return [public_wrapper_inv(w, r) for r, w in enumerate(words)]


P = FIELD
INV3 = pow(3, -1, 16)
L_ORDER = 56


def solve_mod(rows, rhs, p, nunknown):
    A = [r[:] + [rhs[i]] for i, r in enumerate(rows)]
    nrows = len(A)
    pivot_row = 0
    pivots = []
    for col in range(nunknown):
        piv = None
        for r in range(pivot_row, nrows):
            if A[r][col] % p != 0:
                piv = r
                break
        if piv is None:
            continue
        A[pivot_row], A[piv] = A[piv], A[pivot_row]
        inv = pow(A[pivot_row][col], p - 2, p)
        A[pivot_row] = [(x * inv) % p for x in A[pivot_row]]
        for r in range(nrows):
            if r != pivot_row and A[r][col] % p != 0:
                f = A[r][col]
                A[r] = [(A[r][k] - f * A[pivot_row][k]) % p for k in range(nunknown + 1)]
        pivots.append(col)
        pivot_row += 1
        if pivot_row == nunknown:
            break
    sol = [0] * nunknown
    for i, col in enumerate(pivots):
        sol[col] = A[i][nunknown]
    return sol, len(pivots)


# ---------------------------------------------------------------------------
# Remote oracle: speaks the actual server.py line protocol.
# ---------------------------------------------------------------------------
class RemoteOracle:
    def __init__(self, host, port, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""
        self._read_until(b"> ")  # consume banner + first prompt

    def _recv_more(self):
        chunk = self.sock.recv(4096)
        if not chunk:
            raise EOFError("connection closed")
        self.buf += chunk

    def _read_until(self, marker):
        while marker not in self.buf:
            self._recv_more()
        idx = self.buf.index(marker) + len(marker)
        data, self.buf = self.buf[:idx], self.buf[idx:]
        return data

    def _read_line_matching(self, pattern):
        rx = re.compile(pattern)
        while True:
            m = rx.search(self.buf.decode(errors="replace"))
            if m:
                end = self.buf.decode(errors="replace").index("\n", m.start()) + 1
                self.buf = self.buf[len(self.buf.decode(errors="replace")[:end].encode()):]
                return m
            self._recv_more()

    def encrypt(self, plaintext):
        self.sock.sendall(b"1\n")
        self._read_until(b"plaintext hex> ")
        self.sock.sendall(plaintext.hex().encode() + b"\n")
        m = self._read_line_matching(r"ciphertext: ([0-9a-f]+)")
        ct = bytes.fromhex(m.group(1))
        self._read_until(b"> ")
        return ct

    def get_flag(self):
        self.sock.sendall(b"2\n")
        m = self._read_line_matching(r"encrypted flag: ([0-9a-f]+)")
        ct = bytes.fromhex(m.group(1))
        self._read_until(b"> ")
        return ct

    def status(self):
        self.sock.sendall(b"3\n")
        m = self._read_line_matching(r"queries left: (\d+)")
        n = int(m.group(1))
        self._read_until(b"> ")
        return n


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------
class Solver:
    def __init__(self, oracle):
        self.oracle = oracle
        self.block_count = 0
        self.q_perm = None
        self.q_inv = None
        self.symbol_inv = [None] * 16
        self.symbol_perm = None
        self.block_values = {}
        self.block_meta = {}

    def _encrypt(self, plaintext):
        bn = self.block_count
        ct = self.oracle.encrypt(plaintext)
        self.block_count += 1
        return bn, ct

    def _progress(self, msg):
        print(f"    ... {msg}", flush=True)

    def bootstrap_qperm(self):
        qseq = [0, 0] + list(range(1, 15))
        plaintext = bytes([(q << 4) | q for q in qseq])
        bn, ct = self._encrypt(plaintext)
        ranked = public_unwrap(ct)
        top = [w >> 12 for w in ranked]
        dup_rank = None
        for r in range(16):
            if top[r] == top[(r + 1) % 16]:
                dup_rank = r
                break
        assert dup_rank is not None, "no duplicate found in q-marker query"
        rotation = (0 - dup_rank) % 16
        words = [None] * 16
        for r in range(16):
            words[(r + rotation) & 15] = ranked[r]
        q_perm_partial = {}
        for i, q in enumerate(qseq):
            q_perm_partial[q] = words[i] >> 12
        missing_q = (set(range(16)) - set(q_perm_partial.keys())).pop()
        missing_val = (set(range(16)) - set(q_perm_partial.values())).pop()
        q_perm_partial[missing_q] = missing_val
        self.q_perm = [q_perm_partial[q] for q in range(16)]
        self.q_inv = [0] * 16
        for i, v in enumerate(self.q_perm):
            self.q_inv[v] = i
        self.block_meta[bn] = (rotation, words, qseq)

    def _find_rotation(self, ranked, qseq):
        for rot in range(16):
            if all((ranked[r] >> 12) == self.q_perm[qseq[(r + rot) & 15]] for r in range(16)):
                return rot
        return None

    def calibrate_query(self, k):
        qseq = list(range(16))
        plaintext = bytes([(q << 4) | ((k + q) & 15) for q in qseq])
        bn, ct = self._encrypt(plaintext)
        ranked = public_unwrap(ct)
        rot = self._find_rotation(ranked, qseq)
        words = [None] * 16
        for r in range(16):
            words[(r + rot) & 15] = ranked[r]
        self.block_meta[bn] = (rot, words, qseq)
        fields = [split_word(words[i])[1:3] for i in range(16)]
        matches = []
        for Sguess in range(16):
            low8_list = []
            for (B, C) in fields:
                row_code = (INV3 * (Sguess + 2 * B - C)) % 16
                mask = (B - row_code) % 16
                low = SBOX_INV[row_code]
                low8_list.append(mask * 16 + low)
            checksum = (sum(low8_list) + 3 * low8_list[0] + bn) % 16
            if checksum == rot:
                matches.append(Sguess)
        return bn, set(matches)

    def _values_for_block(self, bn, S):
        rot, words, qseq = self.block_meta[bn]
        values = [None] * 16
        for i in range(16):
            A, B, C, D = split_word(words[i])
            q = qseq[i]
            row_code = (INV3 * (S + 2 * B - C)) % 16
            mask = (B - row_code) % 16
            base_col = (S - row_code) % 16
            low = SBOX_INV[row_code]
            check_calc = SBOX[(row_code ^ rotl4(base_col, 1) ^ q ^ low) & 15]
            high = D ^ check_calc
            values[i] = (high << 8) | (mask << 4) | low
        return values

    def resolve_symbol(self, k, max_tries=6):
        candidates = set(range(16))
        bns = []
        for _ in range(max_tries):
            bn, m = self.calibrate_query(k)
            bns.append(bn)
            candidates &= m
            if len(candidates) == 1:
                break
        assert len(candidates) == 1, f"failed to resolve symbol {k}: candidates={candidates}"
        S = next(iter(candidates))
        self.symbol_inv[k] = S
        target_bns = list(bns)
        if k == 0:
            target_bns = [0] + target_bns
        for bn in target_bns:
            self.block_values[bn] = self._values_for_block(bn, S)

    def recover_symbol_perm(self):
        for k in range(16):
            self.resolve_symbol(k)
            self._progress(f"symbol_perm: resolved {k+1}/16 (queries used so far: {self.block_count})")
        self.symbol_perm = [0] * 16
        for i, v in enumerate(self.symbol_inv):
            self.symbol_perm[v] = i

    def extend_samples(self, target_total):
        S = self.symbol_inv[0]
        while self.block_count < target_total:
            qseq = list(range(16))
            plaintext = bytes([(q << 4) | (q & 15) for q in qseq])  # symbol=0
            bn, ct = self._encrypt(plaintext)
            ranked = public_unwrap(ct)
            rot = self._find_rotation(ranked, qseq)
            words = [None] * 16
            for r in range(16):
                words[(r + rot) & 15] = ranked[r]
            self.block_meta[bn] = (rot, words, qseq)
            self.block_values[bn] = self._values_for_block(bn, S)

    def recover_lfsr(self):
        N = self.block_count
        assert all(t in self.block_values for t in range(N)), "gap in block_values"
        data = [[self.block_values[t][lane] for t in range(N)] for lane in range(16)]
        rows, rhs = [], []
        for lane in range(16):
            seq = data[lane]
            for t in range(L_ORDER, N):
                rows.append([seq[t - 1 - j] for j in range(L_ORDER)])
                rhs.append(seq[t])
        rec, rank = solve_mod(rows, rhs, P, L_ORDER)
        assert rank == L_ORDER, f"rank deficient: {rank} < {L_ORDER} (need more queries)"

        x = symbols('x')
        coeffs_poly = [1] + [(-rec[j]) % P for j in range(L_ORDER)]
        poly = Poly(coeffs_poly, x, domain=GF(P))
        factors = sympy.factor_list(poly, modulus=P)
        roots = []
        for f, mult in factors[1]:
            fp = Poly(f, x, domain=GF(P))
            if fp.degree() == 1:
                c = fp.all_coeffs()
                c1 = int(c[0]) % P
                c0 = int(c[1]) % P
                roots.extend([(-c0 * pow(c1, P - 2, P)) % P] * mult)
        assert len(roots) == L_ORDER, f"factoring incomplete: {len(roots)} roots"
        self.nodes = sorted(roots)

        self.coefficients = []
        for lane in range(16):
            samples = data[lane][:L_ORDER]
            vrows = [[pow(self.nodes[j], t, P) for j in range(L_ORDER)] for t in range(L_ORDER)]
            sol, rank2 = solve_mod(vrows, samples, P, L_ORDER)
            assert rank2 == L_ORDER
            self.coefficients.append(sol)

        for lane in range(16):
            for t in range(L_ORDER, N):
                pred = sum(self.coefficients[lane][j] * pow(self.nodes[j], t, P) for j in range(L_ORDER)) % P
                assert pred == data[lane][t], f"LFSR self-check failed lane={lane} t={t}"

    def fold_and_get_flag_coeffs(self):
        N = self.block_count
        new_coeffs = []
        for lane in range(16):
            row = []
            for j in range(L_ORDER):
                shift = 1 + (self.coefficients[lane][j] * (lane + 1) + (j + 3) * (j + 7)) % (P - 1)
                c2 = self.coefficients[lane][j] * pow(self.nodes[j], N + shift, P) % P
                row.append(c2)
            new_coeffs.append(row)
        self.flag_coeffs = new_coeffs
        self.flag_base_block_number = N

    def predict_flag_values(self, lane, k):
        return sum(self.flag_coeffs[lane][j] * pow(self.nodes[j], k, P) for j in range(L_ORDER)) % P

    def decode_word(self, word, stream_value):
        q_label, row_field, col_field, check_field = split_word(word)
        q = self.q_inv[q_label]
        mask = (stream_value >> 4) & 15
        row_code = SBOX[stream_value & 15]
        base_col = (col_field - 2 * mask) & 15
        symbol = self.symbol_perm[(row_code + base_col) & 15]
        return (q << 4) | ((symbol + q) & 15)

    def decrypt_flag(self):
        self.fold_and_get_flag_coeffs()
        ct = self.oracle.get_flag()
        nblocks = len(ct) // 32
        out = bytearray()
        for kb in range(nblocks):
            block_ct = ct[kb * 32:(kb + 1) * 32]
            values = [self.predict_flag_values(lane, kb) for lane in range(16)]
            block_number = self.flag_base_block_number + kb
            rotation = block_rotation(values, block_number)
            ranked = public_unwrap(block_ct)
            words = [None] * 16
            for r in range(16):
                words[(r + rotation) & 15] = ranked[r]
            for i in range(16):
                out.append(self.decode_word(words[i], values[i]))
        return pkcs7_unpad(bytes(out))

    def run(self, min_total_blocks=100):
        self.bootstrap_qperm()
        self._progress(f"q_perm recovered (queries used: {self.block_count})")
        self.recover_symbol_perm()
        self._progress(f"symbol_perm recovered (queries used: {self.block_count})")
        self.extend_samples(min_total_blocks)
        self._progress(f"gathered {self.block_count} consecutive keystream samples")
        self.recover_lfsr()
        self._progress("keystream generator solved (nodes + coefficients recovered)")
        return self.decrypt_flag()


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "tcp.sasc.tf"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 31415
    print(f"[*] connecting to {host}:{port}")
    oracle = RemoteOracle(host, port)
    limit = oracle.status()
    print(f"[*] server reports {limit} queries left")
    target = min(limit - 1, 100)
    if target < 60:
        print(f"[!] warning: only {limit} queries available, attack may fail (needs ~60+)")
        target = max(target, 57)
    solver = Solver(oracle)
    flag = solver.run(min_total_blocks=target)
    print(f"[*] used {solver.block_count} queries")
    print("[+] FLAG:", flag.decode(errors="replace"))


if __name__ == "__main__":
    main()
