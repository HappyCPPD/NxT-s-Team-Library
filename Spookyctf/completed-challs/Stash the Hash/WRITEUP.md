# Stash the Hash

Category: forensics | Points: 629 | Solves: 86

## Flag
spooky{dleeds_isa_devil}

## Steps

1. Unzip `StashTheHash.zip` -> `UserAccountInfo.txt` + `secretKnowledgeFolder.7z`.
2. `UserAccountInfo.txt` leaks the account password as an MD5:
 `ad7bcd7ab3cc113f496e1840bc582bbd`
 (Username dleeds / Daniel Leeds / DevilLeeds / NJ-062805 -> Jersey Devil theme).
3. Crack the MD5 with rockyou:
 `hashcat -m 0 hash.txt .local/share/wordlists/rockyou.txt`
 -> `ad7bcd7ab3cc113f496e1840bc582bbd:newjerseydevils`
4. Unlock the 7z:
 `7z x -pnewjerseydevils secretKnowledgeFolder.7z` -> `secretKnowledge.png` (700x700 RGBA).
5. The flag is hidden in the **least-significant bit plane of the RED channel**.
 Extract it:
 ```python
 from PIL import Image
 im = Image.open('secretKnowledge.png').convert('RGB'); w,h = im.size; px = im.load
 out = Image.new('L',(w,h)); o = out.load
 for y in range(h):
 for x in range(w):
 o[x,y] = 255*(px[x,y][0]&1)
 out.save('r0.png')
 ```
 The top of `r0.png` renders the text: `spooky{dleeds_isa_devil}`
