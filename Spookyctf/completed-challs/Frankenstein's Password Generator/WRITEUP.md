# Frankenstein's Password Generator

**Category:** rev | **Flag:** `spooky{its_alive_at_midnight}`

## Approach
The generator binary validated a password against internal logic. Running it with the magic string `BOLTATMIDNIGHT` produced the flag. Verified by direct execution.

## Reproduction
```bash
./frankenstein BOLTATMIDNIGHT # or pipe via stdin as the binary expects
```
Output: `spooky{its_alive_at_midnight}`
