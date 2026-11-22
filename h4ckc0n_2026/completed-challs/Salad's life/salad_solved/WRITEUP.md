# Salad's life — h4ckc0n 2026 (Crypto, 300, 73 solves)

Handout: `Salads_life.gba` (31560 bytes). Flag format: `d4rk{...}`
Description hints: "neo*sub", "geography", "Mr. [name ~ salad]", "a recent attack",
"a secure number starting with 'f'".

---

## 1. ROM structure (fully reversed)

Real GBA ROM: entry at `0x08000000` is ARM `b 0x080000C0` (devkitARM crt0), then the
game is **Thumb**. GBA header title at 0xA0 = `SALADS SIGHT` / gamecode `2D2B` / `01`.

State machine: a dispatch at `0x080002EA` reads `state = *(u8*)(struct+0x5D)` and jumps
through the handler table at ROM `0x4C64`:

| state | handler | meaning |
|-------|----------|---------|
| 0 | 0x08000A00 | title ("SALAD GOES SIGHT SEEING / A 2-BIT PLATFORMER / PRESS START OR A") |
| 1 | 0x08000B6C | walking / level |
| 2 | 0x080006F0 | **RSA-1024 chest UI** |
| 3 | 0x08000460 | "YOU FOUND THE PAINTING! / # GENUINE ARTIFACT #" + painting |
| 4 | 0x08000F7C | "MOCK PAINTING #2" decoy screen |

Key globals: struct base `0x02000084`; painting RAM buffer = **`0x020000FC`** (9216 bytes);
`0x02000008` holds the accepted key (value `4`).

## 2. The chest and the key

Chest screen strings (ASCII in ROM, `0x4A9C`…`0x4C60`):

```
* RSA-1024 CHEST *
ENCRYPTION: RSA-1024
PUB KEY E: 65537
N: 0XB4A7C93E10F82D5B...
C: 0X7F3A902E4C18D35F...
ENTER THE KEY TO / OPEN THE CHEST / [A] UNLOCK [B] CANCEL
YOU FOUND THE PAINTING! / # GENUINE ARTIFACT #
OH.. U GOT IT, / IS IT THE ONLY PLACE WHERE THE KEY IS / USED THO?
MOCK PAINTING #2 / MOCK #2 / DECOY
DECOY RSA KEY ENTERED! / NOT THE REAL PAINTING. / TRY THE CHEST AGAIN!
```

The chest UI is a single-digit spinner (`+1 % 10` on UP/RIGHT, `+9 % 10` on DOWN/LEFT,
confirm on A/START). At `0x08000734`:

```
cmp r0, #4 ; r0 = selected digit
bne skip
bl 0x08001FD4 ; success path
skip:
ldr r3,[r4,#4] ; r4 = 0x02000004 -> [0x02000008] == 4
cmp r0,r3
bne …
bl 0x08001FD4
… state = 4
```

So **the chest key is `4`** (both the hard-coded compare and the global agree on 4).
`E = 65537 = 0x10001 = F4`, the 4th **Fermat number** — that is the "secure number
starting with 'f'", and F4 → digit 4 → the key. That is the "key reuse" the game
teases ("IS IT THE ONLY PLACE WHERE THE KEY IS USED THO?").

### Success path (`0x08001FD4`)

```
divmod(digit,10) ; digit = 4
buf[0] = remainder + '0' ; "4"
buf[1] = 0
memcpy(0x020000FC, 0x08005744, 0x2400) ; 9216 bytes ROM -> EWRAM
rc4_inplace(buf) ; <-- key = the ASCII digit string
struct+0x68 = 1 ; "painting loaded" flag
state = 3
```

`0x08002CB0` is the RC4 routine: standard KSA/PRGA over a 256-byte stack S-box,
**XORing 9216 bytes at 0x020000FC in place**, key = `buf` (only `key[0]` is ever used).
So the effective key is the single byte `'4'` = `0x34`.

## 3. Painting extraction

`solve/extract_painting.py` reproduces it:

```python
ROM = open('Salads_life.gba','rb').read
ct = ROM[0x5744:0x5744+0x2400] # 9216 bytes, entropy 7.98 (encrypted)
pt = rc4(ct, 0x34) # RC4, single-byte key '4' (int, not b'4')
```

Result: **8501/9216 bytes are 0x00**, 706 bytes are 0x01, 9 bytes are 0x10
(9216 - 715 = 8501).
(The ROM blob equals the RC4('4') keystream for exactly those 8501 zero bytes — the
strongest confirmation that key `'4'` is correct; every other key yields pure noise.)

Rendering (confirmed against the real in-game screen bitmap at
`framerow = base + r*240`, `memcpy(fb_row, &paint[r*192], 192)` for 48 rows):

**The painting is 192 x 48, 8bpp, mode-4 bitmap, palette index 0/1/16 = dark blue /
pale green / dark green.** See `salad_solved/genuine_painting_192x48.png`.

Emulator (Unicorn + DMA) run of the patched ROM reaching the genuine screen:
`salad_solved/screen_genuine.png` — "YOU FOUND THE PAINTING!" + framed artwork +
"# GENUINE ARTIFACT #". Screen is mode 4, VRAM page 1 (`DISPCNT=0x414`).

## 4. The two paintings

* **GENUINE** (`state 3`): the 192x48 green bitmap above — a very wide (4:1) sparse
 line-art landscape: on the left an umbrella/mushroom-like canopy with a banded
 "skirt" (X marks) and a long S-curve; a large arch/hill; then a row of rounded
 bumpy "tree/foliage" masses and one triangular (conifer-like) shape.
* **MOCK #2 / DECOY** (`state 4`): a *different* scene drawn from sprites —
 crescent moon, scattered stars, a tall spire/monument with radiating lines, and a
 row of buildings. This is unmistakably **"The Starry Night" (Van Gogh)** pastiche.
 See `salad_solved/screen_mock2.png` / `mock_painting_2_zoom.png`.

The mock being a recognisable famous painting confirms the genuine one is meant to be
identified too, and that the "artifact" framing is the point of the challenge.

## 5. Hint mapping

| hint | reading |
|------|---------|
| "secure number starting with 'f'" | **Fermat number F4 = 65537 = e** (literally shown in-game) |
| the key `4` | F4 → 4 (the digit the chest wants) |
| "IS IT THE ONLY PLACE WHERE THE KEY IS USED THO?" | the same `4` is the RC4 key for the painting 9216-byte blob |
| "a recent attack" | Fermat's factorisation / a modern factoring result on RSA |
| "geography" | identify the place depicted by the painting (the painting is the "sight" being seen) |
| "Mr. [name ~ salad]" | the painter (e.g. **Salvador** Dalí — "Salvador"~salad, "Dalí"~deli **sub**; and "hallucinations" is a Dalí cue). Alternative: the artist of the genuine piece if it is Van Gogh's Provence period (mock is Van Gogh). |
| "neo*sub" | still unresolved; most consistent reading is a **substitution**-cipher hint ("neo-" + "sub(stitution)", narrator jokes about a "subway sub") |

## 6. Status

DEFINITELY SOLVED
* full ROM reverse (state machine, chest UI, success path, RC4 routine, draw routine)
* key `4` / `E = 65537 = F4` relationship
* exact 9216-byte painting blob, exact RC4 decryption, exact on-screen geometry/palette
* both paintings extracted and rendered; mock = "Starry Night"

NOT YET SOLVED
* the flag string. The chest only prints the top 64 bits of N and C
 (`B4A7C93E10F82D5B…`, `7F3A902E4C18D35F…`), those 64 bits are **not** enough to
 factor N, and the full N/C are **not** stored anywhere in the ROM (searched as
 big-endian and little-endian binary, as ASCII, and against all 54 RSA-challenge
 numbers — no match: RSA-1024 hex is `C05748BBFB5ACD7E…`, RSA-896 `C7A85633…`).
 The displayed N (as a bare 64-bit value) factors as
 5·31·37·1373·21647·76371103 — not a valid RSA modulus, so it is genuinely truncated.
* therefore either (a) the flag is the identified artwork/place title, or
 (b) the full N/C must be recovered from a game path not yet reached.

## 7. Files

```
salad_solved/
 genuine_painting_192x48.png exact decrypted painting, real palette
 genuine_painting_dilated.png same, dilated for legibility
 genuine_zoom.png / genuine_half_L.png / genuine_half_R.png
 screen_genuine.png real emulated screen, state 3
 screen_mock2.png real emulated screen, state 4 (MOCK PAINTING #2)
 mock_painting_2_zoom.png
 painting_encrypted_rom5744.bin ROM blob (9216 B)
 painting_decrypted_9216.bin RC4('4') plaintext
```
---

## 8. Final step — the painting is text (SceneScript)

"neo* sub" + "geography" = **r/neography**. The painting is written in **SceneScript**
(r/neography post "Behold, SceneScript!", key saved as
`behold-scenescript-v0-3qj9v6tb662e1.webp`): each letter is a scenery element.

Glyphs in the painting, left to right:

| glyph | SceneScript letter |
|-------|--------------------|
| snow cloud | J |
| big smooth arc | S |
| bridge over river (inside the arc) | Y |
| small plant | V |
| `x` mark | space |
| three small trees | W |
| rain cloud | G |
| small tree | I |
| river curl | R |
| small tree | I |
| three small trees | W |
| `_` mark | space |
| single bush | P |
| single pine | E |
| tall plant | X |
| small tree | I |
| small plant | V |

Ciphertext: `JSYV WGIRIW PEXIV`. "Mr. salad" = Caesar, and the key 4 is reused
("IS IT THE ONLY PLACE WHERE THE KEY IS USED THO?") → shift back by 4:

`FOUR SCENES LATER`

Flag (accepted): `d4rk{four_scenes_later}` — the format is `d4rk{...}`, with no `c0de` suffix.
