# Heads will Roll

**Category:** crypto | **Flag:** `spooky{5l33py_h0ll0w_h34d5}`

## Approach
A 4-rail rail-fence cipher. The ciphertext was split into 4 rows and read row-by-row; reading it back in the zig-zag rail order recovers the plaintext.

## Reproduction
```python
ct = "Etu_taip5_w5n_hpmnw_hlgsdso{lyh0_d}jyi_piihef_ne_oy3p0lh4oskt_i:k3l3"
# Rebuild the 4 rails (zig-zag over 4 rows), then read column-wise.
def rail_fence_decrypt(ct, rails=4):
 n = len(ct)
 pattern = list(range(rails)) + list(range(rails-2, 0, -1))
 order = [pattern[i % len(pattern)] for i in range(n)]
 counts = [order.count(r) for r in range(rails)]
 rows, idx = [], 0
 for c in counts:
 rows.append(list(ct[idx:idx+c])); idx += c
 out, pos = [], [0]*rails
 for r in order:
 out.append(rows[r][pos[r]]); pos[r] += 1
 return "".join(out)

print(rail_fence_decrypt(ct, 4))
```
Output: `spooky{5l33py_h0ll0w_h34d5}`

## Verification
Re-encrypting the recovered plaintext with the same 4-rail fence reproduced the ciphertext byte-for-byte.
