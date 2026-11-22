# Careless Talk

**Category:** Reverse Engineering 
**Flag:** `SkillBit{c4r3l355_t4lk_c05t5_l1v35}`

## Challenge

We're given a 64-bit Linux ELF binary that prompts for a "watchword." The flavor text hints that while the human clerks kept their secret, the terminal itself might not have.

## Solution

Running `strings` on the binary reveals the flag stored in plaintext as two environment-style variables:

```
FLAG_A=SkillBit{c4r3l355_t4lk_
FLAG_B=c05t5_l1v35}
```

Concatenating the two halves gives the flag. The binary is padded with dozens of decoy strings (convoy rosters, harbor ciphers, relay digests, etc.) to make the output noisy, but a simple `grep` for `FLAG` or `}` cuts through it.

No need to reverse the password check or run the binary at all — the flag was compiled straight into the data section.
