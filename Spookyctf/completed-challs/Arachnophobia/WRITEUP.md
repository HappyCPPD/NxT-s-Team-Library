# Arachnophobia

**Category:** forensics | **Flag:** `spooky{8_l3gs_4nd_4_z1p}`

## Approach
The hint "tangled" meant data tangled after the PNG's end. `exiftool` warned "Trailer data after PNG IEND chunk"; a ZIP (`PK\x03\x04`) was appended directly after IEND. Carving the trailer and unzipping yielded `flag.txt`.

## Reproduction
```python
data = open('tangled.png','rb').read
i = data.rfind(b'IEND')
open('trailer.zip','wb').write(data[i+8:])
```
```bash
unzip -o trailer.zip -d extracted && cat extracted/flag.txt
```
Output: `spooky{8_l3gs_4nd_4_z1p}`
