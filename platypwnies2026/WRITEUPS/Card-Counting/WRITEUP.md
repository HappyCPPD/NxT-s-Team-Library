---
title: "Card Counting"
ctf: "platypwnies 2026"
date: 2026-11-14
category: blockchain
difficulty: 2
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{c0unt1ng_tw1st3d_c4rds::83WdaSTIBjUz}"
---

# Card Counting

## Summary

`PlatyJack` shuffles the blackjack deck with Python's **non-cryptographic Mersenne
Twister** (`random.Random`) and burns exactly **one 32-bit output per hand** to produce
six cards. Because a hand is built as `number = rng.getrandbits(32)` followed by six
`divmod(number, 52)` steps, the six dealt cards are simply the **base-52 digits of one
complete, untempered MT19937 output word**. Every `HandDealt` event therefore leaks a
full MT state word. 624 of them reconstruct the whole generator; from that point every
future draw is known — including the roulette wheel (`rng.randrange(37)`). Blackjack itself
is a slight loss, so the money is the roulette: predict the number, spin 0.5 ETH, get a
36× payout.

Win condition: `Setup.isSolved` → `address(TARGET).balance < 10 ether`, starting from a
100 ETH casino pot.

## Solution / Exploit

Source of truth: `contracts/Chal.sol`, `contracts/Setup.sol`, `service/dealer.py`, exploit
`cardcounting_exploit.py`.

### Step 0 — the leak

`service/dealer.py`:

```python
rng = random.Random

def deal_hand:
 # shuffling a whole deck for every hand is slow, one random number is plenty for six cards
 number = rng.getrandbits(32)
 cards = []
 for _ in range(6):
 number, card = divmod(number, 52)
 cards.append(card)
 return cards

def spin_wheel:
 return rng.randrange(37)
```

`Chal.deal(...)` stores `cards[i]` in `handCards[id]` and `getHand(id)` is a public view, so
the six base-52 digits are readable for every hand id. Inverting the base-52 encoding
(`cards_to_word` in the exploit) returns the exact 32-bit MT output — **no tempering is
lost**, because `getrandbits(32)` returns the raw `genrand_uint32` word.

### Step 1 — harvest 625 words

Play 625 hands (`625 = 624 state words + 1 check word`). Each hand costs
`HAND_BET + DEALER_TIP = 0.011 ETH`, so the observation costs `625 * 0.011 = 6.875 ETH`.
`play` caps at 16 hands per call, so the exploit chunks it:

```python
send(w3, acct, chal.functions.play(n), value=n * (HAND_BET + DEALER_TIP),
 gas=300_000 + 200_000 * n)
```

Wait for the dealer backend to settle them, then read `getHand(id)` for every id and
rebuild the words.

### Step 2 — rebuild the MT19937 state

The 624-word window may start anywhere inside a 624-word block, so every alignment is tried
(`recover_mt`): untemper the words, twist, and keep the offset whose twist reproduces the
wrapped tail of the window. The recovered generator is then verified against word #625:

```python
gen = recover_mt(words[:624], expected_offset=start_id)
probe = gen.genrand
if probe != words[624]:
 raise RuntimeError("state recovery failed to predict the check word ...")
```

A matching check word proves the reconstructed generator is bit-exactly the dealer's.

### Step 3 — bet the roulette on the known outcome

For each of 6 rounds, simulate `randbelow(37)` exactly as CPython's `random.randrange(37)`
does, place the spin, and wait for `settleSpins`:

```python
number = gen.randbelow(37) # == dealer's spin_wheel
send(w3, acct, chal.functions.spin(number), value=bet) # bet = 0.5 ETH (MAX_SPIN_BET)
```

A hit pays `36 * bet = 18 ETH`. Six wins drain 108 ETH, dropping the 100 ETH pot below the
10 ETH threshold. Finally `cashOut`:

```python
if chal.functions.winnings(acct.address).call > 0:
 send(w3, acct, chal.functions.cashOut)
```

### Run

```bash
RPC_URL=http://127.0.0.1:8545/<uuid> \
PRIVATE_KEY=<player key> \
SETUP_ADDRESS=<setup addr> \
FLAG='PP{c0unt1ng_tw1st3d_c4rds::83WdaSTIBjUz}' \
python3 cardcounting_exploit.py
```

Env knobs: `HANDS` (default 625), `WINS` (default 6), `BET_WEI` (default 0.5e18). The player
account needs roughly 11 ETH (6.875 ETH for observation + 3 ETH staked, all returned with
profit).

### Expected output

No raw run log was retained for this challenge; the block below is the literal format of the
script's own `print` statements (not a captured transcript).

```
[*] TARGET 0x... balance 100.0000 ETH, dealer 0x...
[*] observation costs 6.8750 ETH (+ 3.0000 ETH of bets), player has ... ETH
[*] 625 hands played, waiting for the dealer to deal them...
[*] recovered 625 dealer RNG outputs from the dealt cards
[+] MT19937 state recovered and verified against hand #...
[+] spin ...: predicted N, wheel showed N, payout 18 ETH (x6)
[*] winnings booked: 108.0000 ETH, casino balance ... ETH
[*] after cashOut: casino balance ... ETH
[+] isSolved = True
FLAG: PP{c0unt1ng_tw1st3d_c4rds::83WdaSTIBjUz}
```

## Flag(s)

```
PP{c0unt1ng_tw1st3d_c4rds::83WdaSTIBjUz}
```

## Notes / Pitfalls

- **One word per hand, not one per card.** The whole point is that `divmod` consumes nothing
 extra: the six cards are *reversible* digits of a single MT word. If the dealer had drawn a
 fresh word per card (or used `random.shuffle`) this would not work.
- **625, not 624, hands.** MT19937 needs 624 words to pin the state; the 625th is the only
 cheap way to *prove* the alignment is right before risking money. `HANDS < 625` is rejected
 by the script for this reason.
- **Block alignment is unknown.** The observation window can start mid-block; guessing the
 wrong offset yields a generator that still "looks" fine until the check word. `recover_mt`
 brute-forces all 624 offsets and validates via the twist.
- **Cost/float.** The player must be funded (~11 ETH); the script aborts up front if short.
- **Interleaving hazard.** If somebody already spun the wheel before the observation window,
 the dealer's RNG stream is interleaved with other draws and recovery can fail — the script
 prints a warning when `nextSpinId != 0`. Only deal hands (which burn exactly one word
 each) between snapshots.
- **`getrandbits(32)` is untempered.** The exploit's `MT19937`/`untemper` reimplement CPython's
 exact `random.Random` semantics; `randbelow` mirrors `_randbelow_with_getrandbits` so the
 roulette prediction matches the dealer's `randrange(37)` bit-for-bit.
