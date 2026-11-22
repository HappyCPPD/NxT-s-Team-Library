# Lumberjack — Kaspersky CTF 2026 — Solution

**Category:** AI / ML
**Points:** 245
**Solves:** 143

## The Challenge

A web service at `*.kit.sasc.tf` lets you upload an ONNX model containing a
`TreeEnsembleClassifier` and compiles it to a native x86-64 binary. Executing
the binary prints:

```
Predicted Class: X (probability: Y.YY)
```

The flag is stored in the `FLAG` environment variable of the sandbox where the
binary executes.

## The Vulnerability

The ONNX compiler generates C code that accesses model features as `features[feature_idx]`.
For each tree node, the compiler emits:

```c
float val = features[node->feature_idx];
```

This compiles to:

```asm
mov -0x8(%rbp),%rax ; rax = features pointer
sub $0x40,%rax ; rax = features - 64 (for feature_idx = -16)
movss (%rax),%xmm1 ; xmm1 = *(features - 64)
```

The offset is `feature_idx * sizeof(float)`. By setting `feature_idx = -16`, the
compiled binary reads from `features - 64`, which happens to be the stack location
of the `FLAG` environment variable pointer returned by `getenv("FLAG")`.

In `main`, the stack layout is:
- `rbp - 0x30`: features array (16 bytes for 4 floats)
- `rbp - 0x70`: FLAG pointer (getenv result), stored 64 bytes below features

Setting `feature_idx = -16` reads 4 bytes of the flag as a float.

## Exploitation

1. **Build a minimal sklearn RandomForestClassifier** with 2 trees, max_depth=1,
 and fixed `random_state=99` for reproducibility.

2. **Patch the ONNX model** — set all `nodes_featureids` to the desired negative
 index (-16 through -6 to read all 44 bytes of the flag), `class_ids` to
 `[0,1,0,1]`, and `class_weights` to `[0.0, 1.0, 0.0, 1.0]` so the output
 probability equals the number of trees where `flag_float > threshold`.

3. **Binary search** the flag bytes — for each position, two-phase search:
 - Phase 1: find exponent range (-150 to +130, 10 iterations)
 - Phase 2: narrow mantissa to float32 precision (32 iterations)

4. The `probability` output reveals whether `flag_float > threshold`:
 - `prob > 0` means the comparison went to class 1 (flag_float > threshold)
 - `prob = 0` means class 0 (flag_float <= threshold)

5. Convert the found float32 values back to bytes via `struct.pack('<f', value)`.

## Flag

```
kaspersky{943438bc-1f33-4097-8865-e72ceb0094}
```

## Files

- `simple.py` — working solver with two-phase binary search
- `solve.py` — earlier attempt (had comparison direction bug)
- `test_small.onnx` — minimal sklearn model for testing