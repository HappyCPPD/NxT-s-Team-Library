# Rocinate — hints (from a prior run's crash, 2026-10-31)

## Diagnostic: the MT19937 GF(2) state-recovery matrix came out SINGULAR

A previous attempt built the linear system for MT19937 state recovery over GF(2)
and failed with:

 numpy.linalg.LinAlgError: Argument 'A' is singular and not invertible
 because it does not have full rank of 19968, but rank of 19967.

(19968 = 624 * 32 = the MT19937 state size in bits.)

**Rank deficiency of exactly 1 → almost certainly a modelling/alignment bug, not a
genuinely underdetermined problem.** You have ~102 outputs of 2048 bits each
(= ~208,896 observed bits) against 19,968 unknown state bits, so the system should
be massively overdetermined. Check, in this order:

1. **32-bit word extraction / MSB-first ordering.** Each `getrandbits(2048)` value
 must be decomposed into 64 consecutive 32-bit outputs in the correct order and
 bit order (MT19937 emits `temper(y)` as 32-bit words; `getrandbits(k)` assembles
 them little-endian-word / big-endian-bit — verify against a local
 `random.Random(seed)` you can reproduce). A single misaligned word makes the
 system rank-deficient by 1.
2. **`randint(1, N)` rejection sampling.** `randint(1,N)` on a 2047-bit N is NOT a
 bare `getrandbits(2048)` — it consumes `getrandbits(2048)` and REJECTS values
 >= N, so the number of underlying 32-bit words consumed per published value is
 not always 64. Model the rejection (or use `randbelow`/`_randbelow_with_getrandbits`
 semantics from CPython's `random.py`) or your stream drifts by exactly one word.
3. **r0 is NOT an unknown.** Do not solve for r0 in the linear system — r0 is just a
 LATER output of the same MT19937 stream. Recover the 624-word state from the
 observed a, b, Cs[0..99], then run the generator FORWARD to produce r0.

## Endgame reminder
Once r0 is known, all r[i] follow from the public LCG (a, b, N). Then
`Zs[i] / r[i] = s**c[i] mod N`; with c[i] known/predicted, recover the small
integer s (~6 bytes) and check `hiCTF{...}`. Verify by re-encrypting: your
recovered s must reproduce the published Zs and Ts.

## Tooling note
Long cracks must run with `background=true` + `notify_on_complete=true`; a
foreground `terminal` call caps at 180 s and a 19968x19968 GF(2) solve will exceed it.
