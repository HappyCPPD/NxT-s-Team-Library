---
title: "Diceware"
ctf: "platypwnies 2026"
date: 2026-11-14
category: crypto
difficulty: 2
flags:
 - PP{y0u_4r3_7h3_5rv3r_n0w::LEKgDiYHMyGN}
 - PP{k3y_r3u53_41l0wS_r3sp0ns3_r3u5e::JsvKvFPyfnuK}
 - PP{g00d_r34ct10n_71m3::IvJY5DkQH3VN}
---

# Diceware (crypto, difficulty 2) — 3 flags

## Summary

A "privacy-preserving" password manager: a Flask app (`:8081`) that generates diceware
passphrases by fetching each word from a separate Rust **single-server PIR** service
(`:8080`). Three independent bugs, one per flag.

1. **(warmup)** `POST /reset_password` takes the *wordlist URL* straight from the request
 body. That URL is where the app is supposed to fetch words, so the attacker becomes the
 PIR **server**. In the InsPIR/Paillier scheme the server homomorphically combines the
 client's one-hot ciphertexts; because we know the client's public modulus `n` we can
 fabricate ciphertexts that the client's `extract` decrypts to **any word we like**.
 The app then stores that word as the user's *main password* → we can set the password
 of any user except `FlagUser` and log in.

2. **(user)** The wordlist server never deletes its per-request files and serves its whole
 root (which contains `tmp/`) statically — `GET /tmp/` leaks **every PIR query ever
 made**, including the six used to build `FlagUser`'s password. The app also gives us a
 Paillier **decryption oracle** (`/reset_password` stores the decrypted plaintext in an
 entry we can read). One call decrypts a whole batch at once, because Paillier
 decryption is a group homomorphism: `D(∏ ct_i^{w_i}) = Σ w_i·D(ct_i)`. Choosing
 `w_i = (0x30+pos_i)·256^i` packs the recovered one-hot positions into 24 ASCII bytes.

3. **(admin)** `Flask`'s `SECRET_KEY` is the **admin** diceware passphrase
 (`generate_password(CLIENT_ADMIN, …)`). `POST /_app_key` runs the same generation with
 *our* wordlist URL and throws the plaintext away — but `look_up_word` aborts the whole
 loop on the first word whose decrypted bytes are not valid UTF-8 (`.decode` raises).
 Replying `ct_j · E(0x7f)` decrypts to `0x7f` (valid) or `0x80` (**invalid** UTF-8), so
 the number of POSTs we receive equals `hot_index + 1` — a decryption oracle for the
 admin key. 24 calls → 6 words → forge a Flask session with `is_admin=True` → `GET /flag`.

The underlying PIR scheme itself is sound; every break is at the *integration* layer
(attacker-controlled wordlist URL, static file server exposing `tmp/`, discarded plaintext
+ a decode-error oracle).

## Solution / Exploit

Exploit: `diceware_exploit.py` (needs `--web`, `--wl`, `--listen-port`,
`--callback-url` — the URL the challenge container can reach you on).

```bash
python3 diceware_exploit.py \
 --web http://TARGET:8081 --wl http://TARGET:8080 \
 --listen-port 9090 --callback-url https://my-tunnel.example.com
```

### 0. The target

`web/app/diceware.py`:

```python
def generate_password(client_name, wordlist):
 words = [look_up_word(client_name, [secrets.choice(DICE) for _ in range(DICE_COUNT)], wordlist).decode
 for _ in range(PASSPHRASE_LENGTH)]
 return ' '.join(words)
```

`PASSPHRASE_LENGTH = 6`, `DICE_COUNT = 4`, dice ∈ {1..6}. `look_up_word` shells out to
`inspire query <client.bin> /dev/stdout d0-1 d1-1 d2-1 d3-1` to produce a **postcard-
serialized Paillier one-hot query**, POSTs it to `wordlist`, and pipes the response back
through `inspire extract`, which decrypts and returns the word. `generate_client` makes one
2048-bit Paillier keypair per client (`admin`, `users`).

### 1. Warmup — be the PIR server

The one-hot query is `4` selectors of length `6`; selector *s* contains 6 ciphertexts, the
`roll-1`-th of which encrypts `1`, the rest `0`. The server is supposed to reply with
`∑_s c_{s,hot}` (the plaintext of *its* DB slot). Paillier is additively homomorphic with
`g = n+1`, so `E(x) = E(1)^x mod n²`. We have `n` from the query, and multiplying the six
ciphertexts of a selector gives `E(1)` for that selector. Therefore:

```python
E1 = prod(selectors[0]) % n2 # == E(1)
cts = [pow(E1, 1, n2)]*7 + [pow(E1, t, n2)] # decode -> plaintext t
```

`inspire extract` decodes these 8 ciphertexts into the integer `t`, which becomes the word
bytes. So we reply with 8 ciphertexts that turn into any chosen string.

`/reset_password` accepts the wordlist URL and calls `generate_password(CLIENT_USERS, url)`
— six words, all from our server. We return `"pwnednow"` six times, so the stored main
password is `"pwnednow pwnednow pwnednow pwnednow pwnednow pwnednow"`. It refuses
`username == "FlagUser"` (403), but **`"Warmup User"` is fair game**. Log in with the
known password → the warmup flag is in the warmup user's entries.

### 2. User — leak `tmp/`, then one-shot decrypt the batch

`wordlist_server/src/main.rs` writes every query to `tmp/<8rand>.query` and never unlinks
it, and it serves the whole root statically:

```rust
actix_files::Files::new("/", &params.root)
 .show_files_listing // /tmp/ is listable
 .use_hidden_files // dotfiles too
```

`root` is `.` = `/var/www`, which contains `tmp/`. So:

```bash
curl http://TARGET:8080/tmp/ | grep -o '/tmp/[a-z0-9]*\.query'
```

gives every PIR query ever made — group them by modulus `n` (each client has its own key).
`FlagUser`'s password was generated with the `users` client, so its 6 queries are right
there.

Now the decryption oracle: `/reset_password` accepts a `wordlist` URL, decrypts into a
value, and **stores it in our own entry list**, which we can read:

```python
app.reset_password(app.user, {"kind": "decrypt", "ct": c})
digits = re.findall(r"New main password from[^<]*</b>: <code>(.*?)</code>", app.entries)
```

`inspire extract` decrypts with the *users* client key. Decryption is a group
homomorphism, so feeding it `∏ ct_i^{w_i}` yields `Σ w_i·D(ct_i)`. Each query's 6
ciphertexts are the one-hot vector for that word; its plaintext is `1` at the hot slot. To
learn all four digits of a word at once we weight slot `i` of selector `s` of query `q` by
`(0x30 + i)·256^(4q+s)`. The sum then is a 24-byte little-endian ASCII string
`"dddddddd…"` where each group of 4 chars is a word's dice rolls:

```python
c = 1
for q,(name,sel,ts) in enumerate(user_q[:6]):
 for s in range(len(sel)):
 for i,ct in enumerate(sel[s]):
 c = c * pow(ct, (0x30+i) * (256 ** (4*q+s)), n2) % n2
app.reset_password(app.user, {"kind":"decrypt","ct":c})
```

Decode `digits` → 6 words (via `index = d0*216 + d1*36 + d2*6 + d3` into
`eff_short_wordlist_1.txt`) → `FlagUser`'s password. **The 6-word order is ambiguous**
(`Last-Modified` has 1-second resolution, so several queries share a timestamp), so we try
the recovered order then all `6! = 720` permutations until `/login` as `FlagUser`
succeeds.

### 3. Admin — turn "throw the key away" into a key oracle

`app.py`:

```python
@app.post('/_app_key')
def _WIP_app_key:
 generate_password(CLIENT_ADMIN, str(request.form.get('wordlist', DEFAULT_WORDLIST)))
 raise NotImplementedError("changing the app key not implemented")
```

`SECRET_KEY` was set at boot to the **admin** passphrase. `/_app_key` regenerates it with
our URL and discards the plaintext — but `generate_password` aborts on the first word whose
extract output fails `bytes.decode` (invalid UTF-8), and we control the decrypted bytes.

Reply `ct_j · E(0x7f)` so the plaintext is `0x7f` (valid ASCII) or `0x80` (invalid UTF-8),
and the loop stops at the hot word:

```python
ct = (leaked_ct_for_slot_j * pow(E1, 0x7f, n2)) % n2
cts = encode_decrypt(n2, n, E1, ct) # decode -> 0x7f + (0 if cold, 1 if hot)
```

The number of POSTs we receive before the connection dies equals `hot_index + 1`, i.e. the
dice value of that position. 24 calls (4 dice positions × 6 words) recover the entire
passphrase word-by-word — again with one permutation check, this time via the flag:

```python
ck = forge_session(" ".join(cand), {"user_name": "admin", "is_admin": True})
requests.get(WEB + "/flag", cookies={"session": ck})
```

Flask signs its session cookie with `URLSafeTimedSerializer(SECRET_KEY, salt="cookie-session",
signer_kwargs={"key_derivation":"hmac","digest_method":hashlib.sha1})` — `is_admin=True`
gets us the admin flag.

## Flags

```
PP{y0u_4r3_7h3_5rv3r_n0w::LEKgDiYHMyGN} # warmup
PP{k3y_r3u53_41l0wS_r3sp0ns3_r3u5e::JsvKvFPyfnuK} # user
PP{g00d_r34ct10n_71m3::IvJY5DkQH3VN} # admin
```

## Notes / Pitfalls

- **`FlagUser` is the one user you cannot reset** (`reset_password` 403s on it) — that is
 precisely why the user flag needs the `tmp/` leak + decryption oracle instead of the
 warmup trick.
- **Query-format decoding.** The query is `postcard`-serialized: a varint modulus, a varint
 count of selectors, each a varint length then varint-limb `BigUint`s (32-bit limbs). The
 exploit re-implements `rd_varint`/`rd_biguint`/`wr_biguint` and the `Response::Ok` framing
 (`0` ⇒ Ok, then `len`, then each ciphertext).
- **`encode_decrypt`.** To make `decode` evaluate `D(ct)`, pass ciphertexts
 `E(1)^{A}` and `E(1)^{B}` at the two slots where `decode` splits a ciphertext into
 `A = ct mod n`, `B = ct // n mod n` — matching the InsPIR decomposition of product
 ciphertexts.
- **Word ordering is not recoverable from the leak.** `use_last_modified(true)` gives
 1-second mtime resolution, so ties are common; brute the ≤720 permutations and let the
 login (or the `/flag` fetch) confirm. Picking the password from the entries page rather
 than assuming order saves a lot of grief.
- **Rate limiting on the wordlist server** (`--rate-interval 60 --rate-burst 20`): the
 admin stage makes `4·6 = 24` `/reset`-style calls. Batch/reuse a connection and expect
 occasional `429`s; retry rather than assume the oracle misread.
- **Everything is per-client.** Group leaked queries by modulus, not by filename; the
 `users` and `admin` clients have distinct keys and must not be mixed.
- The PIR crypto (`inspire/src/{pir,pallier}.rs`) is genuinely a correct InsPIR/Paillier
 implementation — unlike the challenger's claim that "the database server can be
 fully untrusted", *the client* trusting the server's URL and the *file server* exposing
 `tmp/` are what broke it.
