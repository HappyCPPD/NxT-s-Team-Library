# Standing Order

A grant program pays out against approvals signed by its committee. Two
redemption paths exist -- one for small onboarding credits, one for the
committee's own larger approvals -- and both were wired against the same
signature check.

## Connect

Each team gets a private chain. You are given:

- an RPC URL
- a funded private key
- the address of the `Setup` contract
- a committee-signed voucher, as three values: `voucher_amount`,
 `voucher_nonce`, and `voucher_signature`

Those three values are your approval. You are handed them because you cannot
produce a committee signature yourself -- the same reason your funded key is
handed to you. You can also read them straight off `Setup` on-chain
(`committee`, `voucherAmount`, `voucherNonce`, `voucherSignature`); the
handout and the chain agree.

The Solidity sources for everything deployed on your instance are in
`contracts/`. No web interface; use your own tooling (`cast`/`forge`, `ethers`,
`web3.py`).

Win condition: the program's reserve ends holding less than 1% of its starting
balance. `Setup.isSolved` returns `true` once you have won; submit through the
checker.

## Flag format

`hiCTF{...}`
