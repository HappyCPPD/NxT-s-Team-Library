# Gelotophobia

**Category:** web | **Flag:** `spooky{th4t_w4snt_funn3h}`

## Approach
Live jokes website at http://18.217.64.238 with a strobe-light warning. The page's rapidly flashing content hid the flag; extracting the page states / strobing text revealed the flag, returned in an `<h3>` element on a 200 response (1749 bytes).

## Reproduction
```bash
curl -s http://18.217.64.238/ | grep -oE 'spooky\{[^}]*\}'
```
Output: `spooky{th4t_w4snt_funn3h}` (verified live against the service).
