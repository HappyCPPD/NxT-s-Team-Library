# OwlsAndDragons I (+ Part II progress)

- **Category:** Forensics / Stego (multi-layer)
- **Files:** [`owl_king.png`](owl_king.png) (the real 6 MB file), [`1_preview.webp`](1_preview.webp) (the app's lossy preview)
- **Story:** *"The ancient dragons have awoken and the Owl King is asking for your help… request aid from the hedgehog sage."*
- **Part I flag:** `cratectf{th4_AMaz1ng_hEdGehog}`

## Key gotcha
The chat preview was a **133 KB lossy `.webp`** (`1_preview.webp`) — a dead end (clean VP8, standard
sRGB ICC, no payload). The real artifact was the **6 MB `owl_king.png`** saved in Downloads. Lossless
PNG is where everything hides.

## Part I — extracting the hedgehog sage
1. `owl_king.png` contains **six `zTXt` chunks** named `SVG0`–`SVG5`. Decompressed and concatenated in
   numeric order they rebuild a single SVG (`extracted/reconstructed.svg`, ~5.7 MB).
2. The SVG embeds two base64 `data:` images: a **PNG** (`extracted/hedgehog_sage.png`) and a tiny
   **7-Zip archive** (`extracted/secret_artifact.7z`).
3. The decoded PNG is the hedgehog sage, and **Part I's flag is printed across the top banner**:
   `cratectf{th4_AMaz1ng_hEdGehog}`.

## Part II — identifying the vault (in progress)
After the two base64 images, the reconstructed SVG has a **~3.28 MB binary blob** appended after
`</svg>` (the `SVG3–SVG5` chunks). Its header `EC CB EC F3 … YUZU` XOR `0x13` → `FF D8 FF E0 … JFIF`:
a **JPEG XOR-encrypted with key `0x13`** ("YUZU"→"JFIF"). Decoded, it shows the **Owl King** with
*"Hurry and find the vault!"* and a faint **watermark** of ~170 random uppercase letters —
a **decoy** (letter frequency too skewed for any cipher).

The real key: `hedgehog_sage.png` has a **PDF appended after its `IEND`**. The PDF's one page is the
hedgehog image again, captioned with the string **`YHSAFNBTE`**.

That string is the **password** to `secret_artifact.7z` (7z with AES-256 **encrypted headers** — you
must pass the password at open time, not via `setpassword()`). It extracts **`thing.png`**, an
`LA`-mode image (a dark field with sparse white cells + a non-standard `orNT` chunk) that encodes the
Part II flag — **decoding still in progress** when this writeup was saved.

### Layer summary
```
1_preview.webp         (decoy, lossy)
owl_king.png (6MB)
 └─ zTXt SVG0..SVG5 → reconstructed.svg
     ├─ data:image/png  → hedgehog_sage.png   → banner = Part I flag
     │                     └─ appended PDF     → "YHSAFNBTE" (7z password)
     ├─ data:image/...  → secret_artifact.7z  --(pw YHSAFNBTE)--> thing.png (Part II, WIP)
     └─ trailing bytes  → JPEG XOR 0x13        → Owl King "find the vault" + decoy watermark
```

## Flags
- **Part I:** `cratectf{th4_AMaz1ng_hEdGehog}` ✅
- **Part II:** _pending_ (decode `thing.png`)
