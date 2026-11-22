# Quinn's Secret Treasure

**Category:** crypto | **Flag:** `spooky{lets_g3t_cr4zy_pudd1n}`

## Approach
Direct inversion of the provided `encode.py`. The encoder emitted a list of integers; applying the inverse transform recovers the plaintext string.

## Reproduction
Encoded ints: `126,100,116,77,66,73,76,82,32,56,...`
Inverting the per-character arithmetic (reverse the offset/substitution used by encode.py) yields:
`spooky{lets_g3t_cr4zy_pudd1n}`
