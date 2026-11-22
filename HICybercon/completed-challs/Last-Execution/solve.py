#!/usr/bin/env python3
"""EXE9CORE cold-image emulator for the HICybercon 'Last-Execution' challenge.

Implements exactly the machine described in the image's own PRIMER segment:
header + segment table (big-endian), CODE page-rotation fetch, rotating
dispatch, chained HALT links, TBL row rotation + LDRR, and the SEAL-256
cipher used to open WILL_SEAL.
"""
import struct, hashlib, sys, math

IMG = "Last-Execution/extracted/last_execution.img"
MASK64 = (1 << 64) - 1
K = 0x9E3779B97F4A7C15
X = 0xA5A5A5A5A5A5A5A5

def rol64(v, n):
    n &= 63
    return ((v << n) | (v >> (64 - n))) & MASK64 if n else v & MASK64

def ror64(v, n):
    n &= 63
    return ((v >> n) | (v << (64 - n))) & MASK64 if n else v & MASK64

def be64(b, off=0):
    return struct.unpack_from(">Q", b, off)[0]

class Seg:
    def __init__(self, sid, typ, off, size, flags, aux, crc, name):
        self.id, self.type, self.off, self.size = sid, typ, off, size
        self.flags, self.aux, self.crc, self.name = flags, aux, crc, name
        self.rot = None          # per-page rotation amounts (CODE)
        self.rr = None           # per-row rotation amounts (TBL)

class Image:
    def __init__(self, path):
        self.data = bytearray(open(path, "rb").read())
        d = self.data
        assert d[:8] == b"EXE9CORE", "bad magic"
        self.version, self.flags = struct.unpack_from(">HH", d, 8)
        self.nseg = struct.unpack_from(">I", d, 0x0C)[0]
        self.exec_seed = be64(d, 0x10)
        self.table_seed = be64(d, 0x18)
        self.entry = struct.unpack_from(">I", d, 0x20)[0]
        self.manual = struct.unpack_from(">I", d, 0x28)[0]
        self.filesize = struct.unpack_from(">I", d, 0x2C)[0]
        self.hdr_crc = struct.unpack_from(">I", d, 0x30)[0]
        import zlib
        self.hdr_crc_ok = (zlib.crc32(bytes(d[0:0x30])) & 0xffffffff) == self.hdr_crc
        self.segs = {}
        for i in range(self.nseg):
            b = 0x100 + i * 0x40
            sid, typ = struct.unpack_from(">II", d, b)
            off, size = struct.unpack_from(">QQ", d, b + 0x08)
            flags, aux, crc = struct.unpack_from(">III", d, b + 0x18)
            name = bytes(d[b + 0x24:b + 0x34]).split(b"\0")[0].decode("latin1")
            self.segs[sid] = Seg(sid, typ, off, size, flags, aux, crc, name)
        for s in self.segs.values():
            s.crc_ok = (zlib.crc32(bytes(d[s.off:s.off + s.size])) & 0xffffffff) == s.crc

    # ---- rotation chains -------------------------------------------------
    def code_rotations(self, s):
        if s.rot is not None:
            return s.rot
        d = self.data
        rot = []
        m = rol64((self.exec_seed ^ ((s.id * K) & MASK64)) & MASK64, 19)
        n_pages = (s.size + 255) // 256
        for p in range(n_pages):
            if p > 0:
                w = be64(d, s.off + (p - 1) * 256)
                m = rol64(((m ^ w ^ X) * K) & MASK64, 31)
            rot.append(m % 64)
        s.rot = rot
        return rot

    def tbl_rotations(self, s):
        if s.rr is not None:
            return s.rr
        d = self.data
        n_rows = s.size // 64
        rr = []
        rr.append((self.table_seed ^ ((s.id * 0x1BF5) % (1 << 64))) % 64)
        for i in range(1, n_rows):
            B = d[s.off + (i - 1) * 64]          # first byte of stored row i-1
            rr.append((rr[i - 1] * 17 + B + i * 11) % 64)
        s.rr = rr
        return rr

    def logical_row(self, s, i):
        """row i of a TBL segment with the stored rotation undone."""
        rr = self.tbl_rotations(s)
        stored = bytes(self.data[s.off + i * 64: s.off + (i + 1) * 64])
        return self._ror_bytes(stored, rr[i])

    @staticmethod
    def _ror_bytes(b, n):
        n %= 64
        return b if n == 0 else b[-n:] + b[:-n]

    @staticmethod
    def _rol_bytes(b, n):
        n %= 64
        return b if n == 0 else b[n:] + b[:n]

# ---------------------------------------------------------------------------
DISPATCH = {
    0x03: "NOP", 0x0A: "JNZ", 0x0B: "LI", 0x12: "JMP", 0x16: "LUI", 0x1D: "TRAP",
    0x21: "ORI", 0x2D: "MOV", 0x38: "ADD", 0x42: "ADDI", 0x4C: "SUB", 0x55: "AND",
    0x5F: "OR", 0x6A: "XOR", 0x73: "XORI", 0x7E: "MUL", 0x87: "ROL", 0x8F: "HALT",
    0x91: "ROR", 0x9C: "SHL", 0xA5: "SHR", 0xB0: "NOT", 0xBA: "LDW", 0xC3: "LDB",
    0xC9: "ANDI", 0xCE: "STW", 0xD7: "STB", 0xE2: "LDRR", 0xEC: "CMP", 0xF5: "JZ",
}
PSH = ["NOP", "XOR", "ADD", "MOV", "ROL", "SHR", "AND", "SUB"]

def sext32(v):
    return v - (1 << 32) if v & 0x80000000 else v

class Fault(Exception):
    pass

class Machine:
    def __init__(self, img, trace=False):
        self.img = img
        self.mem = img.data                       # live memory (stores visible)
        self.regs = [0] * 16
        self.z = 0
        self.trace = trace
        self.steps = 0

    def run(self, sid=None, pc=0, max_steps=2_000_000, verbose=False):
        if sid is None:
            sid = self.img.entry
        nhalts = 0
        while True:
            s = self.img.segs.get(sid)
            if s is None or s.type != 1:
                raise Fault(f"BADLINK: seg {sid} missing or not CODE")
            rot = self.img.code_rotations(s)
            s_off, s_size = s.off, s.size
            while True:
                if pc + 8 > s_size:
                    raise Fault(f"pc {pc:#x} past end of segment {sid}")
                self.steps += 1
                if self.steps > max_steps:
                    raise Fault("step budget exhausted")
                raw = be64(self.mem, s_off + pc)
                if pc + 16 > s_size:              # may cross page boundary
                    pass  # raw already read as contiguous be64 from memory
                word = rol64(raw, rot[pc >> 8])
                op_byte = (word >> 56) & 0xFF
                rd = (word >> 48) & 0xFF
                ra = (word >> 40) & 0xFF
                rb = (word >> 32) & 0xFF
                imm = word & 0xFFFFFFFF
                idx = (op_byte + ((pc >> 4) + s.aux)) % 256
                mn = DISPATCH.get(idx)
                if mn is None:
                    mn = PSH[idx % 8]
                if verbose:
                    print(f"  seg{sid} {s.name} pc={pc:#06x} op={op_byte:#04x} idx={idx:#04x} {mn} "
                          f"rd={rd} ra={ra} rb={rb} imm={imm:#x}")
                pc = self._exec(mn, rd, ra, rb, imm, pc)
                if pc is None:
                    return  # terminated
                if isinstance(pc, tuple):
                    sid, pc = pc
                    break
            nhalts += 1
            if nhalts > 10000:
                raise Fault("halt loop")

    def _need(self, *rs):
        for r in rs:
            if r > 15:
                raise Fault(f"bad register R{r}")

    def _exec(self, mn, rd, ra, rb, imm, pc):
        R = self.regs
        if mn == "NOP":
            return pc + 8
        if mn == "LI":
            self._need(rd); R[rd] = imm; return pc + 8
        if mn == "LUI":
            self._need(rd); R[rd] = (imm << 32) & MASK64; return pc + 8
        if mn == "ORI":
            self._need(rd); R[rd] = (R[rd] | imm) & MASK64; return pc + 8
        if mn == "MOV":
            self._need(rd, ra); R[rd] = R[ra]; return pc + 8
        if mn in ("ADD", "SUB", "AND", "OR", "XOR", "MUL"):
            self._need(rd, ra, rb)
            a, b = R[ra], R[rb]
            R[rd] = {"ADD": (a + b), "SUB": (a - b), "AND": (a & b),
                     "OR": (a | b), "XOR": (a ^ b), "MUL": (a * b)}[mn] & MASK64
            return pc + 8
        if mn == "ADDI":
            self._need(rd, ra); R[rd] = (R[ra] + sext32(imm)) & MASK64; return pc + 8
        if mn in ("ANDI", "XORI"):
            self._need(rd, ra)
            R[rd] = (R[ra] & imm if mn == "ANDI" else R[ra] ^ imm) & MASK64
            return pc + 8
        if mn in ("ROL", "ROR"):
            self._need(rd, ra)
            R[rd] = rol64(R[ra], imm % 64) if mn == "ROL" else ror64(R[ra], imm % 64)
            return pc + 8
        if mn == "SHL":
            self._need(rd, ra); R[rd] = (R[ra] << (imm % 64)) & MASK64; return pc + 8
        if mn == "SHR":
            self._need(rd, ra); R[rd] = R[ra] >> (imm % 64); return pc + 8
        if mn == "NOT":
            self._need(rd, ra); R[rd] = R[ra] ^ MASK64; return pc + 8
        if mn == "CMP":
            self._need(ra, rb); self.z = 1 if R[ra] == R[rb] else 0; return pc + 8
        if mn in ("LDW", "LDB"):
            self._need(rd, ra)
            addr = (R[ra] + sext32(imm)) & 0xFFFFFFFFFFFFFFFF
            if addr + (8 if mn == "LDW" else 1) > len(self.mem):
                raise Fault(f"{mn} out of image at {addr:#x}")
            R[rd] = be64(self.mem, addr) if mn == "LDW" else self.mem[addr]
            return pc + 8
        if mn in ("STW", "STB"):
            self._need(ra, rd)
            addr = (R[ra] + sext32(imm)) & 0xFFFFFFFFFFFFFFFF
            tgt = self._seg_containing(addr)
            if tgt is None or not (tgt.flags & 1):
                raise Fault(f"WRITEPROT at {addr:#x}")
            if mn == "STW":
                self.mem[addr:addr + 8] = struct.pack(">Q", R[rd])
            else:
                self.mem[addr] = R[rd] & 0xFF
            return pc + 8
        if mn == "LDRR":
            self._need(rd, ra)
            phys = (R[ra] + sext32(imm)) & 0xFFFFFFFFFFFFFFFF
            t = self._seg_containing(phys)
            if t is None or t.type != 3:
                raise Fault(f"LDRR not in TBL at {phys:#x}")
            row_base = t.off + ((phys - t.off) & ~63)
            k = phys - row_base
            if k > 56:
                raise Fault("LDRR misaligned")
            i = (row_base - t.off) // 64
            logical = self.img.logical_row(t, i)
            R[rd] = be64(logical, k)
            return pc + 8
        if mn == "JMP":
            return (pc + 8 + sext32(imm)) & 0xFFFFFFFF
        if mn in ("JZ", "JNZ"):
            take = (self.z == 1) if mn == "JZ" else (self.z == 0)
            return (pc + 8 + sext32(imm)) if take else (pc + 8)
        if mn == "HALT":
            nxt = (imm ^ (self.regs[1] & 0xFFFFFFFF)) & 0xFFFFFFFF
            if nxt == 0xFFFFFFFF:
                return None
            s = self.img.segs.get(nxt)
            if s is None or s.type != 1:
                raise Fault(f"BADLINK next_id={nxt:#x}")
            return (nxt, 0)
        if mn == "TRAP":
            raise Fault(f"TRAP imm={imm:#x}")
        raise Fault("unhandled " + mn)

    def _seg_containing(self, addr):
        for s in self.img.segs.values():
            if s.off <= addr < s.off + s.size:
                return s
        return None

# ---- SEAL-256 -------------------------------------------------------------
def seal_sbox(img):
    dlook = next(s for s in img.segs.values() if s.name == "DLOOK")
    D = bytearray()
    for i in range(4):
        D += img.logical_row(dlook, i)
    assert len(D) == 256
    perm = list(range(256))
    for i in range(255, 0, -1):
        j = D[i] % (i + 1)
        perm[i], perm[j] = perm[j], perm[i]
    inv = [0] * 256
    for i, v in enumerate(perm):
        inv[v] = i
    return perm, inv

P = [0x00, 0x05, 0x0A, 0x0F, 0x04, 0x09, 0x0E, 0x03, 0x08, 0x0D, 0x02, 0x07, 0x0C, 0x01, 0x06, 0x0B]
IP = [0x00, 0x0D, 0x0A, 0x07, 0x04, 0x01, 0x0E, 0x0B, 0x08, 0x05, 0x02, 0x0F, 0x0C, 0x09, 0x06, 0x03]

def key_schedule(key):
    x = list(struct.unpack(">4Q", key))
    rk = []
    for i in range(1, 18):
        for j in range(4):
            t = (x[j] + x[(j + 1) % 4] + ((0x9E3779B97F4A7C15 * (4 * (i - 1) + j + 1)) & MASK64)) & MASK64
            t ^= x[(j + 3) % 4] >> 7
            x[j] = rol64(t, 13)
        rk.append(struct.pack(">QQ", x[0] ^ x[2], x[1] ^ x[3]))
    return rk

def seal_decrypt_block(block, rk, inv_sbox):
    st = bytes(block)
    st = bytes(a ^ b for a, b in zip(st, rk[16]))
    for r in range(15, -1, -1):
        st = bytes(st[IP[i]] for i in range(16))
        st = bytes(inv_sbox[v] for v in st)
        st = bytes(a ^ b for a, b in zip(st, rk[r]))
    return st

def open_seal(img, key, seg=None, verbose=True):
    sbox, inv_sbox = seal_sbox(img)
    if seg is None:
        seg = next(s for s in img.segs.values() if s.name == "WILL_SEAL")
    blob = bytes(img.data[seg.off:seg.off + seg.size])
    shifts = blob[:16]
    ct = blob[16:]
    L = len(ct) // 16
    assert L * 16 == len(ct), "ct not block aligned"
    # undo column rotation: stored[r][c] = ct[(r - shift[c]) mod L][c]
    out = bytearray(len(ct))
    for r in range(L):
        for c in range(16):
            src = (r - shifts[c]) % L
            out[r * 16 + c] = ct[src * 16 + c]
    rk = key_schedule(key)
    pt = b""
    for r in range(L):
        pt += seal_decrypt_block(out[r * 16:(r + 1) * 16], rk, inv_sbox)
    # strip PKCS#7
    if pt and 1 <= pt[-1] <= 16 and pt[-pt[-1]:] == bytes([pt[-1]]) * pt[-1]:
        pt = pt[:-pt[-1]]
    return pt


def main():
    img = Image(IMG)
    print(f"version={img.version:#06x} flags={img.flags} N={img.nseg} entry={img.entry} "
          f"manual={img.manual} size={img.filesize} header_crc_ok={img.hdr_crc_ok}")
    print(f"EXEC_SEED={img.exec_seed:#018x} TABLE_SEED={img.table_seed:#018x}")
    for s in sorted(img.segs.values(), key=lambda s: s.id):
        print(f"  id={s.id:2d} type={s.type} off={s.off:#08x} size={s.size:7d} flags={s.flags:#x} "
              f"aux={s.aux:#x} crc_ok={s.crc_ok} {s.name}")

    # --- spec self-check -------------------------------------------------
    st = next(s for s in img.segs.values() if s.name == "EXEC_SELFTEST")
    m = Machine(img)
    m.run(sid=st.id, pc=0, verbose=False)
    digest = hashlib.sha256(b"".join(struct.pack(">Q", m.regs[i]) for i in (1, 2, 3, 4))).hexdigest()
    want = "0b6d8d4770eac443de6b9b73340a4a262117d9da42e6ced9411ebda286bbbcf2"
    print(f"\nSELFTEST R1..R4 = {[hex(m.regs[i]) for i in (1,2,3,4)]}")
    print(f"SELFTEST commitment = {digest}\n              expect = {want}\n  match = {digest == want}")

    # --- full chain ------------------------------------------------------
    m2 = Machine(img)
    m2.run(sid=img.entry, pc=0, verbose=False)
    print(f"\nFINAL step count = {m2.steps}")
    print("FINAL R15 =", hex(m2.regs[15]), "(want 0x5354414C)")
    print("FINAL R1..R4 =", [hex(m2.regs[i]) for i in (1, 2, 3, 4)])
    for i in range(16):
        pass

    # telemetry cross-check
    tel = next(s for s in img.segs.values() if s.name == "TELEMETRY")
    print("\nTELEMETRY segment (raw):")
    print(bytes(img.data[tel.off:tel.off + tel.size])[:256])

    key = hashlib.sha256(b"LASTEXEC" + b"".join(struct.pack(">Q", m2.regs[i]) for i in (1, 2, 3, 4)) + b"LASTEXEC").digest()
    print("\nkey =", key.hex())
    pt = open_seal(m2 and img, key)
    print("WILL plaintext:", pt)


if __name__ == "__main__":
    main()
