# CER FRUMOS — Writeup

**CTF:** TFC CTF 2026
**Category:** Crypto
**Challenge:** CER FRUMOS
**Flag:** `TFCCTF{ursu_ursa_bea_ursus_intrun_urus_verzuliu}`

## Challenge Overview

The challenge seeds Python's `random` module (Mersenne Twister, MT19937) with a
random 128-bit integer, then generates 625 samples of 48-bit numbers. Each
sample consumes 2.5 MT outputs:

```
x = random.getrandbits(48) # 32 + 16 bits from two tempered state words
random.getrandbits(16) # discarded
print(x)
```

After the 625 samples, 10 more `getrandbits(32)` calls are made (discarded),
then the next two `getrandbits(64)` calls produce seeds for AES-256-CBC:

```python
key = sha256(str(random.getrandbits(64)).encode).digest
iv = sha256(str(random.getrandbits(64)).encode).digest[:16]
cipher = AES.new(key, AES.MODE_CBC, iv=iv)
enc_flag = cipher.encrypt(flag)
```

We are given `out.txt` — 625 lines of 48-bit integers and the hex-encrypted
flag.

## Vulnerability

Python's `random` module uses MT19937, a 624-word (19968-bit) state that is
entirely deterministic once the state is known. Given enough consecutive
outputs, the full internal state can be recovered. The challenge gives generous
leakage:

- 625 × 48-bit samples = 625 × (32 + 16 bits) of tempered output
- Each 48-bit sample gives the **full lower 32 bits** and the **top 16 bits**
 of consecutive MT outputs
- With 624 words needed to reconstruct the state and over 1000 tempered words
 leaking, Z3 can recover the state trivially

## Solution

### Step 1: Model the Mersenne Twister in Z3

We model the MT state as 624 symbolic 32-bit bitvectors. The twist and temper
operations are implemented as Z3 expressions mirroring CPython's
`_randommodule.c`:

- **twist**: regenerates the state array every 624 calls using the recurrence
 relation with the twist matrix `A = 0x9908B0DF`
- **temper**: applies the output transformation (right shift 11, left shift 7
 with mask `0x9D2C5680`, left shift 15 with mask `0xEFC60000`, right shift 18)

### Step 2: Add Constraints from the Leaked Outputs

For each 48-bit sample `x`:

```python
solver.add(next_word == (x & 0xFFFFFFFF)) # lower 32 bits
solver.add(Extract(31, 16, next_word) == (x >> 32)) # upper 16 bits of next word
next_word # discarded 16-bit call
```

The solver tracks `idx` and calls `twist` automatically when it wraps around
at 624.

### Step 3: Skip Discarded Outputs and Recover Key/IV

After constraining all 625 samples, we advance the state past the 10 discarded
calls and extract the symbolic key/IV words:

```python
for _ in range(10):
 next_word

key_lo, key_hi = next_word, next_word
iv_lo, iv_hi = next_word, next_word
```

### Step 4: Solve and Decrypt

```python
assert solver.check == sat
model = solver.model
key_seed = model.eval(key_lo) | (model.eval(key_hi) << 32)
iv_seed = model.eval(iv_lo) | (model.eval(iv_hi) << 32)
key = sha256(str(key_seed).encode).digest
iv = sha256(str(iv_seed).encode).digest[:16]
flag = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(enc)
```

### Results

```
key seed: 4364408293663289775
iv seed: 9427524340023772294
flag: TFCCTF{ursu_ursa_bea_ursus_intrun_urus_verzuliu}
```

## Key Takeaways

1. **Mersenne Twister is not cryptographically secure.** 624 consecutive
 32-bit outputs fully determine the internal state.
2. **Partial output bits are still constraints.** The 16-bit upper halves
 constrain half of the next state word — Z3 handles this naturally.
3. **Z3 is overkill here** — given full 32-bit lower words for all 625 samples,
 an untempering approach (inverting the temper function, then solving the
 linear GF(2) recurrence) would also work and be much faster.
4. **Never use `random` for cryptographic keys.** Use `os.urandom` or
 `secrets` module.