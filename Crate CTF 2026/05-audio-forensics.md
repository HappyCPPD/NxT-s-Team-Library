# Audio Forensics (file.mp3)

- **Category:** Forensics / Stego
- **File:** [`file.mp3`](file.mp3)
- **Hint:** *"Artists express themselves with music, but the message is not always so clear."*
- **Flag:** `cratectf{kunde_inte_höra_den_komma}` ("couldn't hear it coming")

## Challenge
A single MP3. The ID3 metadata is full of clues (artist "lil hacker", genre "forensics"):

- **`TALB` (album):** *"compressed in the end under pressure"* → a ZIP is **appended at the end**
  (and "Under Pressure" is a Queen/Bowie song — *artists express themselves with music*).
- **Comment:** *"The waveform isn't the whole picture"* → look at the **spectrogram**.

## Solution
### 1. Carve the appended ZIP
A `PK\x03\x04` signature sits at offset 363267 (after the MP3 audio). Carving to EOF yields
[`appended_flag_AES.zip`](appended_flag_AES.zip), containing `flag.txt` (37 bytes) — but it is
**WinZip-AES encrypted** (`need PK compat. v5.1`), so it needs a password.

### 2. Recover the password from the spectrogram
Decoding the MP3 to PCM and running an STFT reveals text drawn in the audio (see
[`spectrogram_password.jpg`](spectrogram_password.jpg) /
[`spectrogram_password_full.jpg`](spectrogram_password_full.jpg)):

```
password:LJUDFREKVENSER
```
("ljudfrekvenser" = Swedish for *sound frequencies*.)

### 3. Decrypt
```python
import pyzipper
with pyzipper.AESZipFile('appended_flag_AES.zip') as z:
    z.setpassword(b'LJUDFREKVENSER')
    print(z.read('flag.txt').decode())
```
→ see [`flag_decrypted.txt`](flag_decrypted.txt).

## Flag
```
cratectf{kunde_inte_höra_den_komma}
```

## Lesson
Two channels cooperate: the audible track is cover, the **spectrogram** hides the password, and
the real payload is a **ZIP concatenated onto the end of the file**. Always check metadata, file
tails, and the spectrogram.

## Files
- `file.mp3` — the challenge file
- `appended_flag_AES.zip` — the carved AES-encrypted archive
- `spectrogram_password.jpg`, `spectrogram_password_full.jpg` — spectrogram showing the password
- `flag_decrypted.txt` — decrypted `flag.txt`
