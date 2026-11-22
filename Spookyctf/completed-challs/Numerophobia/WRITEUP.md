# Numerophobia

**Category:** crypto | **Flag:** `spooky{th3_4n5w3r_h45_4lw4y5_b33n_42}`

## Approach
`numerophobia.txt` held 3 space-separated decimal lines; `10` = newline. Lines 1 and 3 were decoy padding (alternating 50 65 / 63 52). Line 2 was the payload.
Hints: "dyslexia" = reverse the line; "every other step ... marked with a 13" = subtract 13 from every other element. Then chr.

## Reproduction
```python
mid=[138,50,65,95,123,51,64,98,108,53,134,52,132,108,65,95,66,52,117,95,127,51,132,53,123,52,108,51,117,116,136,121,120,111,124,112,128]
s=[mid[i]-13 if i%2==0 else mid[i] for i in range(len(mid))]
print("".join(map(chr,s))[::-1])
```
Output: `spooky{th3_4n5w3r_h45_4lw4y5_b33n_42}`
