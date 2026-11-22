# Xenoglossophobia

Category: misc (Scripting, Log Analysis) | Points: 663 | Solves: 73

## Flag
spooky{supermarket_simulator}

## Steps

### 1. Understand the serial protocol
`serial-capture.log` is a UART capture. `>` lines are host->device writes,
`<` lines are 1-byte device reads (0x06 = ACK, one 0x15 = NAK).

The host->device stream is 2 single-byte writes (offsets 389136, 389401) plus
2950 framed 132-byte windows at global offsets 0,132,...,389268. Each window:

 byte 0 : 0x01 (SOH)
 byte 1 : seq (0..255)
 byte 2 : 0xff - seq (header checksum)
 bytes 3..130 : 128 data bytes
 byte 131 : sum(data[3:131]) & 0xff (trailer checksum)

The header and trailer checksums verify for all 2950 frames (0 failures), which
confirms the framing.

### 2. Reassemble
Take bytes `[3:131]` from each 132-byte window (drop the 3-byte header and the
1-byte trailer), concatenate in offset order (script `work/parse2.py`):

```python
stream = b"".join(c[3:131] for _, c in sorted(frames)) # 2950*128 = 377600 bytes
```

This yields a valid baseline JPEG (2560x1440) followed by a Latin message
(padded with 0x1a). `pre=3, suffix=1` is the only framing that decodes with ZERO
libjpeg errors.

### 3. The hint (Latin)
```
Ut clavem invenias ad plura de "loco" cognoscenda, intellegere debes
quid imago tibi significet. Est id quod "supermercado" vocant!
```
= "To find the key ... you must understand what the image signifies. It is
what they call a 'supermarket'!"

### 4. Identify the image
The recovered screenshot is first-person gameplay: shelves of parody brands
(Narvalo espresso, Susu powdered sugar, Crispy Chibi cereal, Kraftung flour,
Basmati rice, Ron's bread), a HUD with "Store Level 17", "$177.25", time
04:18PM, and a "V1.0.1(132)" build string.

Reverse image search (Yandex CBIR) resolves it to **Supermarket Simulator**
(Steam / developer Nokta Games).

=> the "place" (supermercado) is the game **Supermarket Simulator**, and the
flag is the game name: `spooky{supermarket_simulator}`.

No literal `spooky{...}` string exists in the recovered stream (checked) — the
flag is the identified game name, per the hint.
