# read the rules

**Category:** misc | **Flag:** `spooky{th1s_could-b3-a_flag!}`

## Approach
The flag was a literal string in the challenge metadata / rules text — no decoding required. A plain grep across the bundle surfaced it.

## Reproduction
```bash
grep -rIo "spooky{[^}]*}" . | sort -u
```
The value `spooky{th1s_could-b3-a_flag!}` appears in the challenge metadata (completed-challs tree).
