# RESULT — Neural Nets (h4ckc0n 2026, AI/ML, 200 pts, 104 solves)

STATUS: SOLVED (flag proven by byte-exact round-trip, not guessed)

FLAG: d4rk{ved-in.was.here.?}

## One-line mechanism

The 32 scalar biases are **GPT-2 BPE token IDs divided by 1e5**
(`bias = token_id / 1e5`, stored as float32). Multiply each bias by 1e5, round,
and detokenize the ID list with GPT-2's `vocab.json` -> the flag. The network
itself is a dead 1x1-layer chain and `target.pt` is a decoy.

## Why every other reading failed (recorded so nobody re-does it)

* Pure affine composition of all 32 layers: slope = `prod(weights) = 8.0318e-19`,
 bias term `f(0) = -3.7507e-02`. With ReLU the map is *constant*
 (`7.1109e-03`) for every input in 0..255 (layer 7 onward, span = 0).
 So the "instrument" cannot map a char to `target.pt` at all -> the net is a decoy.
 `target.pt` = 13 values all ~`4.8252335e-06`: any linear/interp inverse explodes
 (implied input ~4.67e16); `1/t` is not integral; no bit-window yields ASCII.
 Only real content there: idx8 == idx10 exactly (same value), which merely
 mirrors biases 8 and 10 being identical.
* `bias*1e5 mod B` for a single base B: only 6 bases keep all residues in 0..93
 (94, 95, 97, 98, 99, 105) and all produce garbage ("d4rk{C-f.w.@E}Cyt~zpl&SF/D{kfr7B"
 for B=95). The `d4rk{` prefix is real because GPT-2's byte encoder assigns
 id = ord(ch)-33 for printable ASCII (id 67='d', 19='4', 81='r', 74='k', 90='{')
 — that is the *coincidence* that makes it look like `mod 95`.
* Big-int / digit-concatenation / reversal / sorting / per-layer bases: all dead.

## Mechanism detail (with the hint explained)

1. Hint "**gippity knows what to make of it**" -> GPT tokenizer. GPT-2's
 `bytes_to_unicode` maps printable byte 33..126 to ids 0..93, so the first
 five biases decode as single-byte tokens `d 4 r k {`.
2. Hint "**what are trailing zeros? they don't exist for me**" -> `43220/1e5`
 prints as `0.4322` (the 5th decimal zero is invisible), `90/1e5` prints as
 `0.0009`, `170/1e5` as `0.0017`. You must recover the *5-decimal* integer,
 i.e. `round(bias*1e5)`, not the printed digits. (If you read `0.4322` as id
 4322 you get a different token — this is the trap.)
3. All recovered IDs are < 50257 (GPT-2 vocab size), which confirms the scale.
4. Detokenizing all 32 IDs gives the flag followed by GPT-2-continuation decoys:
 `d4rk{ved-in.was.here.?} SkyrimWarscharges honest wandering conceded...`

## Proof (real output, `neuralnets_FINAL_verify.py`)

```
token ids from biases*1e5 : [67, 19, 81, 74, 90, 1079, 12, 259, 13, 9776, 13, 1456, 40791, 92,
 21789, 41508, 34948, 5508, 24504, 24684, 170, 24895, 32825, 9157,
 29369, 27205, 43220, 42254, 14889, 3406, 47807, 42023]
all ids < 50257 (GPT-2 vocab): True
detokenized (GPT-2) : 'd4rk{ved-in.was.here.?} SkyrimWarscharges honest wandering conceded\ufffd statutes Ghana proven CUtesterscour haha suprem Your darts sleepy'
FLAG : d4rk{ved-in.was.here.?}
round-trip encode(FLAG) : [67, 19, 81, 74, 90, 1079, 12, 259, 13, 9776, 13, 1456, 40791, 92]
matches bias ids prefix : True
VERIFIED
```

The decisive, independent check is the round trip: a from-scratch GPT-2 BPE
encoder (vocab.json + merges.txt, regex pre-tokenizer + rank merges) encodes
`d4rk{ved-in.was.here.?}` to exactly the author's 14 IDs, and BPE decode is a
bijection on the byte string, so the flag string is unique.

Token map for the flag part:
`d|4|r|k|{` = 67,19,81,74,90 ; `ved`=1079 ; `-`=12 ; `in`=259 ; `.`=13 ;
`was`=9776 ; `.`=13 ; `here`=1456 ; `.?`=40791 ; `}`=92

## Artifacts (in Neural Nets)

* `neuralnets_FINAL_verify.py` — final solver + round-trip proof (run:
 `stvenv/bin/python neuralnets_FINAL_verify.py`)
* `nn_gpt2.py`, `nn_gpt2b.py`, `nn_bpe.py`, `nn_tok.py` — decoding experiments
 (GPT-2 / cl100k_base / o200k_base; GPT-2 `round` is the only coherent one)
* `nn_modscan.py`, `nn_basescan.py`, `nn_scan14.py`, `nn_mid.py` — dead-end
 `mod B` scans (kept as negative evidence)
* `nn_affine.py`, `nn_layers.py`, `nn_probe.py` — proofs the net is dead
* `nn_bits2.py`, `nn_bitpack.py` — target.pt bit analysis (decoy)
* `gpt2_vocab.json`, `gpt2_merges.txt`, `cl100k.tiktoken`, `o200k.tiktoken`
 (downloaded via GET only; no outbound POSTs)
