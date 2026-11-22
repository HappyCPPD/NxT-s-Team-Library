# Tormented Tanny

**Category:** forensics | **Flag:** `spooky{tormented_tanner_hates_his_vetsulin}`

## Approach
The flag was split across three PNG metadata fields. Concatenating them in tag order reconstructs the full string.

## Reproduction
```bash
exiftool -a -u -g1 TormentedTanny.png | grep -E "Title|Description"
# Title : spooky{tormented_tanner_
# Description (XMP): hates_his_
# Image Description: vetsulin}
```
Concatenated: `spooky{tormented_tanner_hates_his_vetsulin}`
