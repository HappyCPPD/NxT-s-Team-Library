# Conservation Record

**Object:** `stego.png`  
**Condition:** Original file preserved

The visible image is only part of the record. The original pixel data must remain untouched. Resampling, colour correction, conversion, or re-encoding may destroy information that cannot be recovered from a visual copy.

## The Image Key

The key used to inspect this image is derived from the previously recovered master key using HKDF-SHA256:

- Input key material: `master`
- Salt: an empty byte string
- Information: `stego`
- Output length: 32 bytes

An empty salt means zero-length input, not the literal word `empty`.

## The Collector's Index

The collector did not follow a sequential path through the image. Each candidate position was selected using HMAC-SHA256 and a counter beginning at zero.

Represent each counter value as an unsigned eight-byte, big-endian integer. Use that representation as the HMAC message and the derived image key as the HMAC key.

Interpret the first eight bytes of each digest as a big-endian unsigned integer. Reduce that integer modulo the total number of RGB byte positions in the image to obtain a candidate position.

Treat the image as a row-major sequence of RGB bytes, with the red, green, and blue channels in that order. If a position has already been selected, skip it without extracting another bit. Otherwise, record the least significant bit of the selected byte.

Preserve the order in which new positions are selected.

## Reconstructing the Record

Assemble the recovered bits into bytes, most significant bit first.

The first four bytes represent the payload length as an unsigned, big-endian integer. Read exactly that many payload bytes, followed by a four-byte, big-endian CRC-32 checksum.

The checksum covers the payload alone. Use the standard CRC-32 calculation.

Do not trust a readable message merely because it looks plausible. The declared length must be consistent with the recovered frame, and the checksum must match before the record is accepted.

**A faithful image is not necessarily a complete record.**