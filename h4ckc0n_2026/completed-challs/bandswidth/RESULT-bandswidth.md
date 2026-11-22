# RESULT - bandswidth

STATUS: SOLVED

FLAG: d4rk{4kb_isn't_all_that_bad_tbh_1t's_much_b3tter_th4n_n0thing...}

## MECHANISM

Target: https://h4ckc0n-bandwidth.chals.io/download (no redirect; final URL is the given one)
Server: gunicorn, `Accept-Ranges: bytes`.

1. HEAD/`-sI` reveals a fake-looking, enormous body:
 ```
 HTTP/1.1 200 OK
 Content-Type: application/octet-stream
 Content-Length: 1099511627776 # 1 TiB = 2^40
 Accept-Ranges: bytes
 ```
 Root `/` returns `{"challenge":"BANDSWIDTH","download_size":1099511627776,"unit":"bytes"}`.
 A fresh `bw_session` cookie is issued on every request (no per-session state).

2. Range requests work. Head/tail are pure zeros (first ~4.5 MiB = 0x00; last 4096 = 0x00),
 so the needle is NOT at offset 0 and NOT in the final few KB.

3. The server caps a single Range to 1 MiB: `Range: bytes=0-1048575` -> 206,
 `bytes=0-1048576` -> 416 "Requested range too large". Bisection confirmed the limit is
 0x100000 (1 MiB). Multi-range and open-ended ranges -> 416 "Invalid or unsatisfiable range".

4. Scanning the LAST 1 MiB window (the natural place to look, since the tail did not match)
 for non-zero bytes found the payload:
 ```
 $ curl -s -r 1099510579200-1099511627775 --max-time 60 \
 https://h4ckc0n-bandwidth.chals.io/download -o bw_last1MiB.bin
 # 65 non-zero bytes out of 1,048,576, clustered at window index 1046528..1046592
 ```

5. Minimal proof — an exact range yields the flag verbatim:
 ```
 $ curl -s -r 1099511625728-1099511625792 --max-time 60 \
 https://h4ckc0n-bandwidth.chals.io/download
 d4rk{4kb_isn't_all_that_bad_tbh_1t's_much_b3tter_th4n_n0thing...}
 ```
 Flag occupies file offsets 1099511625728 .. 1099511625792 (i.e. the 65 bytes ending
 ~183 bytes before EOF).

## NOTES / PITFALLS
- Do NOT download the whole file (1 TiB, server throttles to ~200-250 KB/s).
- The flag is in the final 1 MiB region but ABOVE the last 4 KiB, so `curl -r -4096` misses it.
 Fetch a full 1 MiB suffix range (`curl -r 1099510579200-1099511627775`).
- Max single range is 1 MiB; larger ranges 416. Params/endpoints are a dead end (`/health` only).
- No outbound callbacks used; no scoring-platform contact; only gentle ranged GETs.

## ARTIFACTS
- work/bw_head.bin - first 4096 bytes (zeros)
- work/bw_tail.bin - last 4096 bytes (zeros)
- work/bw_full_head.bin - first ~4.5 MiB of a full GET (all zeros)
- work/bw_last1MiB.bin - last 1 MiB window containing the flag
- work/bw_wl.txt - small discovery wordlist used
