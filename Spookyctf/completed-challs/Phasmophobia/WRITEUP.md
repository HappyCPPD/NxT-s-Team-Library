# Phasmophobia

Forensics / steganography, 500 pts.

**Flag:** `spooky{OOOGABOOGABOOGABOOspoopedBOOgotyou}`

## How the story maps to the files
- "haunted house like music": the WAV file
- "heard… whispering": text hidden in the WAV spectrogram
- "at the same time… saw a portrait shift": the portrait (PNG) holds the shift to apply
- "a ghost wearing a laurel": Caesar cipher
- "from the corner of my eye": the PNG message is in the LSBs starting at the top-left corner

## Part 2: the image (ebersecret.png)
The red, green and blue LSBs, read row by row (zsteg `b1,rgb,lsb,xy`), hold a 4-byte big-endian
length (34) followed by:

 JWWowbgwc (2) (18 salads. yummers)

"18 salads" means a Caesar cipher with shift 18. Shifting each letter forward by 18
(equivalently, back by 8) gives `BOOgotyou`. The "(2)" marks it as the second piece of the flag.

## Part 1: the audio (PhasmophobiaChallenge.wav)
Between 7.3 s and 14.4 s, text is drawn into the spectrogram at about 8.4–10.5 kHz:

 WWWOIJWWOIJWWOIJWWaxwwxml

Things that make it hard to read:
- Each capital W looks like two V shapes, which makes it easy to count too many W's.
- Sound-effect bursts at about 8.3, 12.05 and 12.95 s cover parts of some letters.

The same shift of 18 decodes it to:

 OOOGABOOGABOOGABOOspooped

## Flag
Join part 1 and part 2 with no separator and keep the case:

 spooky{OOOGABOOGABOOGABOOspoopedBOOgotyou}

## Dead ends
The intended solution never uses these: steghide on the WAV (clue words and the top
300k rockyou passwords), sample LSBs, Whisper transcription of the bursts, the 11–22 kHz band,
PNG chunks and dimensions, and OpenStego/cloacked-pixel.
