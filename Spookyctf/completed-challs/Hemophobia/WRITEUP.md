# Hemophobia

Category: web | Points: 173 | Solves: 129

## Flag
spooky{sepultura}

## Steps

1. `GET http://77.112.83.127/` -> index.html. A comment leaks the trail:
 > There's a song that plays in this nightmare, but it's no longer here...
 > I wrote it down somewhere though. I think it's in nightmare.txt...
 > The flag looks like spooky{band}

2. `GET /nightmare.txt`:
 ```
 The song from the nightmare.
 I wrote the title down so I wouldn't forget it:
 Roots Bloody Roots
 I think this is where I heard it:
 https://open.spotify.com/playlist/37i9dQZF1DWWOaP4H0w5b0?si=...
 Who made it?
 ```
 Page title is "Hometophobia", `<h1>Roots...Bloody Roots</h1>`.

3. "Roots Bloody Roots" is the Sepultura track (album *Roots*, 1996).
 => band = Sepultura.

4. Confirm against the client-side check in `script.js`:
 ```js
 const FLAG_HASH = '6423651715153126';
 if (hash(v.toLowerCase) === FLAG_HASH) { ... }
 ```
 Implemented the same hash (cyrb53-style) offline; `spooky{sepultura}`
 (lower-cased) hashes to exactly `6423651715153126`.
