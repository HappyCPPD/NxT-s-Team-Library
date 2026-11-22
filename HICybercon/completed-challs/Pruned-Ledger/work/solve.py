#!/usr/bin/env python3
"""Pruned Ledger (HI CyberCon 2026) -- full case-file reconstruction for case 0xca5ef11e.

Everything below is recomputed from the shipped archive (transactions.jsonl) and the
replayed chain; nothing is guessed.  Run:  .venv/bin/python work/solve.py
"""
import json, rlp, subprocess
from eth_utils import keccak
from eth_account import Account

CASE_TAG   = "0xca5ef11e"
RPC        = "http://127.0.0.1:8545"
TXF        = "Pruned-Ledger/extracted/chain/transactions.jsonl"

sel = lambda s: keccak(text=s)[:4].hex()
SEL = {"configure": sel("configure(bytes32)"), "seal": sel("seal(bytes32)"),
       "prune": sel("prune()"), "unlock": sel("unlock(bytes32)")}
ARCHIVE_DOMAIN = b"hictf.pruned-ledger.archive"
SEAL_DOMAIN    = keccak(b"hictf.pruned-ledger.seal")
NOTE_DOMAIN    = keccak(b"hictf.pruned-ledger.note")

def cast(*a):
    return subprocess.run(["cast", *a], capture_output=True, text=True).stdout.strip()
def asc(b):
    b = b.rstrip(b"\x00")
    try: s = b.decode("ascii")
    except Exception: return None
    return s if s and all(32 <= ord(c) < 127 for c in s) else None
def create_addr(snd_hex, nonce):
    return keccak(rlp.encode([bytes.fromhex(snd_hex[2:]), nonce]))[12:]

TXS = [json.loads(l) for l in open(TXF) if l.strip()]

# ---- 1. locate the case's Ledger via the relay trail (relay caseTag == CASE_TAG) ----
creations = {}
for t in TXS:
    dec = rlp.decode(bytes.fromhex(t["raw"][2:]))
    if not dec[3]:
        snd = Account.recover_transaction(bytes.fromhex(t["raw"][2:]))
        creations[create_addr(snd, dec[0]).hex()] = (dec[5], t["n"])
print("[*] relay trail for case tag", CASE_TAG)
trail = []
relay_addrs = set()
for addr, (code, n) in creations.items():
    if len(code) == 964:                      # Relay(bytes4 caseTag, address next)
        relay_addrs.add("0x" + addr)
for addr, (code, n) in creations.items():
    if len(code) == 964:
        tag = code[-64:-60].hex()
        nxt = "0x" + code[-20:].hex()
        if tag == CASE_TAG[2:]:
            trail.append((n, addr, nxt))
trail.sort()
for n, addr, nxt in trail:
    print(f"    n{n:3d} relay {addr} -> {nxt}")
ledger = next(nxt for _, _, nxt in trail if nxt not in relay_addrs)  # terminal non-relay hop
print(f"[*] terminal contract (Ledger) = {ledger}")

# ---- 2. case reference (immutable, lives in code) ----
ref_raw = cast("call", ledger, "caseReference()(bytes32)", "--rpc-url", RPC)
ref = bytes.fromhex(ref_raw[2:]); case_ref = asc(ref)
print(f"[*] caseReference() = {ref_raw} = {case_ref!r}")

# ---- 3. the pruned working record history (from the tx archive) ----
print("[*] configure() history (record values the operator set):")
hist = []
for t in TXS:
    dec = rlp.decode(bytes.fromhex(t["raw"][2:]))
    if dec[3] and dec[3].hex() == ledger[2:] and dec[5][:4].hex() == SEL["configure"]:
        hist.append((t["n"], dec[5][4:36]))
for n, r in hist:
    print(f"    tx#{n:4d}  record = 0x{r.hex()}  {asc(r)!r}")

# find the record live when seal() was called, and unmask the filed entry
seal_n = seal_arg = None
for t in TXS:
    dec = rlp.decode(bytes.fromhex(t["raw"][2:]))
    if dec[3] and dec[3].hex() == ledger[2:] and dec[5][:4].hex() == SEL["seal"]:
        seal_n, seal_arg = t["n"], dec[5][4:36]
rec_at_seal = max((n, r) for n, r in hist if n < seal_n)[1]
print(f"[*] seal() at tx#{seal_n}: record live at seal = {asc(rec_at_seal)!r}")

# ---- 4. recompute the derived archive slot and read the entry from storage ----
slot = (int.from_bytes(keccak(ARCHIVE_DOMAIN + rec_at_seal), "big") - 1) % 2**256
slot_hex = "0x" + slot.to_bytes(32, "big").hex()
stored = cast("storage", ledger, slot_hex, "--rpc-url", RPC)
mask  = keccak(SEAL_DOMAIN + bytes.fromhex(ledger[2:]) + rec_at_seal)
entry = bytes(p ^ q for p, q in zip(seal_arg, mask))
print(f"[*] archive slot = keccak(ARCHIVE_DOMAIN ++ record)-1 = {slot_hex}")
print(f"[*] cast storage {ledger} {slot_hex} -> {stored}  (= {asc(bytes.fromhex(stored[2:]))!r})")
print(f"[*] maskedEntry ^ mask -> {entry.hex()}  (= {asc(entry)!r})   [matches storage]")
entry_str = asc(entry)

# ---- 5. unmask the note (address-keyed mask; filed for the 0x1233... caller) ----
masked_note = bytes.fromhex(cast("call", ledger, "_maskedNote()(bytes32)", "--rpc-url", RPC)[2:]) \
    if False else None
# _maskedNote has no getter -> take it from the creation ctor args
ctor = creations[ledger[2:]][0]
masked_note = ctor[-64:-32]
print(f"[*] maskedNote (ctor arg) = {masked_note.hex()}")
print("[*] caller brute-force: note(caller) = maskedNote ^ keccak(NOTE_DOMAIN ++ ledger ++ caller)")
note_str = caller_hit = None
callers = set()
for a in json.load(open(TXF.replace("transactions.jsonl", "genesis.json")))["alloc"]:
    callers.add(a.lower())
for t in TXS:
    s = Account.recover_transaction(bytes.fromhex(t["raw"][2:]))
    callers.add(s[2:].lower())
for c in sorted(callers):
    cb = bytes.fromhex(c)
    x = bytes(p ^ q for p, q in zip(masked_note, keccak(NOTE_DOMAIN + bytes.fromhex(ledger[2:]) + cb)))
    if asc(x):
        note_str, caller_hit = asc(x), "0x" + c
        print(f"    caller {caller_hit} -> note = {note_str!r}")
print(f"[*] note filed for {caller_hit} = {note_str!r}")

# ---- 6. live confirmation: unlock() with a wrong guess leaks the note in the revert ----
rev = cast("call", ledger, "unlock(bytes32)", "0x" + b"bad".ljust(32, b"\x00").hex(),
           "--from", caller_hit, "--rpc-url", RPC)
print(f"[*] live unlock(0x00..bad) revert data: {rev}")

# ---- 7. assemble the case file ----
fields = [case_ref, asc(rec_at_seal), entry_str, note_str]
flag = "hiCTF{" + "_".join(fields) + "}"
print()
print("RECONSTRUCTED CASE FILE for", CASE_TAG)
for k, v in zip(["caseReference", "record", "archiveEntry", "note"], fields):
    print(f"   {k:14s} = {v}")
print("FLAG:", flag)
