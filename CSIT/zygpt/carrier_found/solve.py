#!/usr/bin/env python3
"""ZyGPT (TISC 2026 L4) solver.
  Stage 1 — find the LIVE record set by brute-forcing 5-subsets of all 69 records
            against the flip-mask position oracle (correct set scores ~59, chance <=2).
  Stage 2 — derive KM, read the sealed wire, AES-256-GCM decrypt -> flag.
Usage:
  python solve.py            # verify the known live set + decrypt (instant)
  python solve.py --search   # actually brute-force all 11.2M 5-subsets (~minutes) then decrypt
"""
import sys, json, struct, hashlib, itertools, multiprocessing as mp
import numpy as np
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

flag_mask = np.load("l14_flag.npy")          # 3812 detected LSB flips in layers.14.mlp.up_proj
cw = np.load("cw.npy"); bw = np.load("bw.npy")   # carrier words (chal) and factory-baseline words
E  = flag_mask.size; Eu = np.uint64(E)

REC = {int(t): v["words"] for t, v in json.load(open("recs.json")).items() if v["ok"]}
ids = sorted(REC)                                 # the 69 provisioning records
def sig(t):  return [REC[t][i] for i in (0, 1, 3, 4, 6, 7)]
BLOB = {t: struct.pack(">I", t) + struct.pack("<6H", *sig(t)) for t in ids}
def km_of(sub): return hashlib.sha256(b"".join(sorted(BLOB[t] for t in sub))).digest()[:16]

def positions(Sd, need=608):
    raw = np.frombuffer(hashlib.shake_256(Sd).digest(8 * 1024), dtype=">u8")
    v = (raw % Eu).astype(np.int64)
    _, i = np.unique(v, return_index=True)
    return v[np.sort(i)[:need]]
def score(sub):                                   # the cheap, sound oracle
    Sd = hashlib.sha256(km_of(sub) + b"\x01").digest()
    return int(flag_mask[positions(Sd)].sum())

def _score_combo(combo):
    s = score(combo)
    return (s, combo) if s >= 20 else None

def brute_search():
    total = 11238513  # C(69,5)
    print("[*] brute-forcing all 11,238,513 5-subsets of the 69 records")
    print("    against the position oracle (chance <=2 ; correct set scores ~59) ...\n")
    with mp.get_context("fork").Pool() as p:
        for r in p.imap_unordered(_score_combo,
                                  itertools.combinations(ids, 5), chunksize=4096):
            if r:
                s, combo = r
                print(f"    *** HIT  score={s}  live={list(combo)}\n")
                p.terminate()
                return list(combo)
    raise SystemExit("no hit")

def decrypt(live):
    KM = km_of(live)
    K  = hashlib.sha256(KM + b"\x00").digest()
    Sd = hashlib.sha256(KM + b"\x01").digest()
    pos = positions(Sd)
    bits = (cw[pos] & 1) ^ (bw[pos] & 1)          # payload bit = leaked_LSB XOR baseline_LSB
    wire = np.packbits(bits.astype(np.uint8)).tobytes()
    nonce, ct, tag = wire[:12], wire[12:60], wire[60:76]
    pt = AESGCM(K).decrypt(nonce, ct + tag, None)
    print(f"\n[*] live records : {live}")
    print(f"[*] KM           : {KM.hex()}")
    print(f"[*] AES-256-GCM tag: VALID")
    print(f"\n    FLAG = {pt.rstrip(chr(0).encode()).decode()}")

if __name__ == "__main__":
    live = brute_search() if "--search" in sys.argv else [125499, 130167, 142680, 151879, 151905]
    decrypt(live)
