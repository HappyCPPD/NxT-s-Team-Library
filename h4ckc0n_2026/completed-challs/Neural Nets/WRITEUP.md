# Neural Nets — h4ckc0n 2026 (AI/ML, 200)

**Flag:** `d4rk{ved-in.was.here.?}`

## The instrument is dead

`mlp_weights.pt` holds 25 × `Linear(1,1)` and 7 × `Conv2d(1,1,1,1)` — all scalars.
Composing them is a plain affine map:

```
prod(weights) = 8.0318e-19 f(0) = -3.7507e-02
```

Slope 1e-19 means the output is input-independent in any real range; with ReLU
the whole chain saturates to the constant `7.1109e-03` from layer 7 onward
(measured span = 0.0 over x∈[0,255]). So `target.pt` (13 values, all
`4.8252335e-06`) is not the image of any character — it is a decoy. Any inverse
attempt explodes (`x ≈ 4.67e16`).

## "gippity" = GPT tokenizer

The flag lives in the biases, and the toy `mod 95` reading (`bias*1e5 = ord-33`,
which coincidentally spells `d4rk{`) is a trap. The real encoding:

```
bias_i = gpt2_token_id_i / 1e5 (stored as float32)
```

Proof of scale: ids run 0..50256 = exactly GPT-2's vocab, and GPT-2's
`bytes_to_unicode` maps printable ASCII to `id = ord(ch) - 33`, which is why
`0.00067, 0.00019, 0.00081, 0.00074, 0.0009 × 1e5 = 67,19,81,74,90 = d,4,r,k,{`.

Trailing-zero hint: `43220/1e5` is printed `0.4322`, `90/1e5` is `0.0009`,
`170/1e5` is `0.0017`. You must round to the 5-decimal integer; reading
`0.4322` as id 4322 lands on a wrong token.

## Decode

```
ids = [round(b*1e5) for b in biases] # mlp 0..24 then cnn 0..6
```

`[67,19,81,74,90,1079,12,259,13,9776,13,1456,40791,92, ...]`
→ GPT-2 detokenize → `d4rk{ved-in.was.here.?}` + GPT-2-continuation decoys
(`SkyrimWarscharges honest wandering conceded…`).

Verification: a from-scratch GPT-2 BPE encoder (vocab.json + merges.txt)
re-encodes `d4rk{ved-in.was.here.?}` to exactly those 14 IDs, and BPE decode is
lossless/unique, so the string is pinned.

Solver: `neuralnets_FINAL_verify.py`. Full reasoning + negative results:
`RESULT-neuralnets.md`.
