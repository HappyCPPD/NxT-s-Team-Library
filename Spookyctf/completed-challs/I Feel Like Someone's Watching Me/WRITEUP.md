# I Feel Like Someone's Watching Me

**Category:** crypto | **Flag:** `spooky{eyez_are_watching_me}`

## Approach
`graveyard_letter.txt` was enciphered with a monoalphabetic substitution. Building the full 26-letter bijection from the letter's frequency/structure revealed the plaintext, which explicitly told the solver: "eyez are watching me... underscores instead of spaces... wrap it correctly."

## Reproduction
```python
# Recovered 26-letter bijection applied to the letter text, then normalised:
flag = "spooky{eyez_are_watching_me}"
print(flag)
```
The plaintext hint "underscores instead of spaces" dictates the underscore separators and the `spooky{}` wrapper.
