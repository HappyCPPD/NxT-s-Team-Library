# Eisoptrophobia

**Category:** forensics | **Flag:** `spooky{the_reflection_never_lies}`

## Approach
`zsteg -a` on the PNG found base64 text in the RGB LSB plane (`b1,rgb,lsb,xy`):
`c3Bvb2t5e3RoZV9yZWZsZWN0aW9uX25ldmVyX2xpZXN9` → base64-decode → flag.

## Reproduction
```bash
zsteg -a Eisoptrophobiactf.png | grep text
echo 'c3Bvb2t5e3RoZV9yZWZsZWN0aW9uX25ldmVyX2xpZXN9' | base64 -d
```
Output: `spooky{the_reflection_never_lies}`
