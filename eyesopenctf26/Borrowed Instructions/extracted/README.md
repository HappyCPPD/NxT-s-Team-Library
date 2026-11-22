# Challenge

**Category:** PWN | **Difficulty:** HARD

## Connection

The host and port of the live service are shown on the challenge page.
TLS is required: the service sits behind a proxy that terminates TLS and
routes on the TLS server name, so a plaintext client never reaches it —
and `--ssl` is not an option of GNU netcat.

```
ncat --ssl <host> <port>
openssl s_client -quiet -connect <host>:<port> -servername <host>
```


**Token:** `8a73939134264311dd99827549e1808e`

_Send the token when the service prompts for it. You have 30 seconds._

## Run the same service locally

`local/` rebuilds this challenge on your machine — same base image,
same binary, same token prompt — so you can debug without burning the
shared instance. Offsets found here transfer to the remote.

```
docker compose -f local/docker-compose.yml up --build -d
```

The replica listens in plaintext, so `nc localhost <port>` reaches it
directly — no TLS, no token.

The flag inside this copy of `challenge` is a stand-in. An exploit
that works locally prints it; the live service prints the real one.

## Generator note
> _structural floor is 'insane' — 'srop' cannot be made structurally simpler than that, but modifier 'hard' (source code, hints, addresses) is fully applied._

## Files
| File | Description |
|------|-------------|
| `challenge` | ELF binary (x86_64) |
| `local/` | Rebuild the same service on your machine |
