# Message from miku

Category: Forensics | Points: 200 | h4ckc0n 2026
Live target: http://4.187.169.60:39393/ (event mirror of `https://h4ckc0n-playforge.chals.io/miku/`)

## Flag

```
d4rk{M1KU_G0T_C4UGHT_US1NG_0P1UM_4ND_M3T4M3T4PH1N3}
```

## Solve path

The target is a single static page served by nginx 1.31.8 (`/` -> 29,880-byte
`index.html`, ETag `6af9661a-74b8`, Last-Modified 07:58). Everything on the
surface is a normal Hatsune Miku one-screen fan stage.

Scrub of the delivered HTML found no leftover comments, no zero-width
characters, no trailing-whitespace / tab stego, and no extra files on the
web root (`robots.txt`, `.git/*`, `.env`, backups, source maps, archives all
return the stock nginx 404; only the stock `/50x.html` exists).

The hidden payload is on the "Tune in" button:

```
<button ... data-morse="--.. .---- -..- .... ..--.- - ----- --. ..--.-
 .--. ....- .... - ..- --. ..--.- .... ..-. .---- .- - ..--.-
 ----- -.-. .---- .... --.. ..--.- ....- .- --.- ..--.-
 --.. ...-- --. ....- --.. ...-- --. ....- -.-. ..- .---- .- ...--">
```

The JS behind the button just renders those tokens as 700 Hz audio (the
"broadcast"), so the transmission is recoverable straight from the attribute.

Layer 1 - Morse (`..--.-` is underscore in the ITU/Morse-with-punctuation set):

```
Z1XH_T0G_P4HTUG_HF1AT_0C1HZ_4AQ_Z3G4Z3G4CU1A3
```

That is still leetspeak gibberish, so Layer 2 is ROT13 (digits are leet and
unchanged). `Z1XH` -> `M1KU` confirms the shift:

```
M1KU_G0T_C4UGHT_US1NG_0P1UM_4ND_M3T4M3T4PH1N3
```

which wrapped in the given `d4rk{...}` template is the flag.

`solve.py` in this folder reproduces both layers from the token string.

## Decoys (organisers confirmed one exists)

Two flag-shaped strings are planted on the page and are *not* the answer:

1. `<b class="tx-id">d4rk{TX_0039_A}</b>` inside the `aria-hidden` "readout"
 block -- a transmission ID, not a message.
2. The JSON script block at the bottom of the page:

 ```json
 {"archive_reference":"d4rk{d0nt_t3ll_th3_p0l1c3_p75}","site":"M3554G3 FR0M M1KU","version":"2.0"}
 ```

 This is the planted decoy flag (the "don't tell the police" joke). It is
 exactly what a naive `grep d4rk` finds; the actual message is only
 revealed by decoding the broadcast.

Note: `M3T4M3T4PH1N3` decodes literally to "METAMETAPHINE" (the author's
spelling) -- the flag must be submitted exactly as decoded, not corrected to
"methamphetamine".