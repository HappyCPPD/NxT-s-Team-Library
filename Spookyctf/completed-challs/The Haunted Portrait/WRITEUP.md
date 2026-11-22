# The Haunted Portrait

**Category:** forensics | **Flag:** `spooky{portraits_keep_secrets}`

## Approach
The PNG's blue channel LSB plane carried rendered text. Extracting bit-plane 0 of the blue channel as an image produced:

```
THE PORTRAIT WHISPERS:
THE DEAD SPEAK IN ROT13
fcbbxl{cbegenvgf_xrrc_frpergf}
```

ROT13-decoding the string gives the flag. Note the last word is "frpergf" → "secrets" (an earlier misread as "scarest" was wrong).

## Reproduction
```python
from PIL import Image; import numpy as np
a=np.array(Image.open('haunted_portrait.png').convert('RGB'))
Image.fromarray(((a[:,:,2]&1)*255).astype('uint8')).save('blue_lsb.png')
```
```bash
python3 -c "import codecs;print(codecs.decode('fcbbxl{cbegenvgf_xrrc_frpergf}','rot13'))"
```
Output: `spooky{portraits_keep_secrets}`
