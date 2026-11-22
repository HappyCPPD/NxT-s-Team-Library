# Trust Issues

OSINT, 100 pts. Start: https://github.com/codrrr-max

## Flag

`d4rk{ƒU_0S1Nt}` (accepted, with the literal `ƒ`)

## Chain

1. `codrrr-max/FirstRepo` has six commits. Five use the GitHub noreply address,
 but `7582edc` ("Initialize package.json for server side project") leaks the
 real author email: `testing.saydo@gmail.com`.
2. "Trust" + display name "Wandering Web" points at the PGP web of trust.
 Searching the email on keyserver.ubuntu.com returns key
 `C0306EE0E58F584D55E6BC75F6B4A4E01AD8FF80` with UIDs
 `Say Do (notes https://pastebin.com/q8iDMZf4) <testing.saydo@gmail.com>`.

 ```bash
 curl -s "https://keyserver.ubuntu.com/pks/lookup?search=testing.saydo%40gmail.com&op=index&options=mr"
 ```
3. Paste `q8iDMZf4` ("hmm", by pastebin user `testinnn`) gives the first half:
 `{ƒU_`
4. `pastebin.com/u/testinnn` lists a second, untitled paste `UH2YMQ1u` with the
 second half: `0S1Nt}`

Dead ends: Gravatar for the email is the default image, no public Google
calendar, nothing hidden in SecondRepo or package-lock.json.
