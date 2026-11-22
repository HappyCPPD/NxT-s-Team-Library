# Socket-Malfunction

**Category:** forensics (network)
**Flag:** `SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}`

## The challenge

> A WebSocket session between a door controller and its operator app, captured after the initial handshake. The controller's responses are readable, but the client's messages are not. Recover the credential the client sent to release the lock.

The zip holds one file, `control-socket.pcap`, about 1.2 KB of plain Ethernet capture.

## Looking at the traffic

There is no HTTP upgrade in the capture. It starts after the handshake, so what is on the wire is bare WebSocket frames over TCP between ports 51788 and 47821. The description already tells you the split: server-to-client frames read as plaintext, client-to-server frames look like noise.

That split is the RFC 6455 masking rule. A client MUST mask every frame it sends, a server MUST NOT. Masking XORs the payload with a 4-byte key that is carried in the frame header, so anyone holding the capture can undo it. It is not encryption and was never meant to be.

## Unmasking the frames

Each frame is a 2-byte header (FIN + opcode, then MASK + length) followed by an optional extended length, then the 4-byte masking key if MASK is set, then the payload. The client frames have the MASK bit set, so you strip the key and XOR:

```python
frames = {
 5: "81 85 73ffda6b ...",
 7: "81 bd 34315918 ...",
 9: "81 91 bcfb74a9 ...",
}
for n, h in frames.items:
 b = bytes.fromhex(h)
 fin = b[0] & 0x80; op = b[0] & 0x0f
 masked = b[1] & 0x80; ln = b[1] & 0x7f
 i = 2
 if ln == 126:
 ln = int.from_bytes(b[i:i+2], "big"); i += 2
 elif ln == 127:
 ln = int.from_bytes(b[i:i+8], "big"); i += 8
 mask = b[i:i+4]; i += 4
 data = b[i:i+ln]
 out = bytes(data[j] ^ mask[j % 4] for j in range(len(data)))
 print(n, "fin", fin, "op", op, "masked", masked, "len", ln,
 "mask", mask.hex, "->", repr(out))
```

Output:

```
5 fin 128 op 1 masked 128 len 34 mask 73ffda6b -> b'{"cmd":"subscribe","topic":"door"}'
7 fin 128 op 1 masked 128 len 58 mask 34315918 -> b'{"cmd":"auth","key":"SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}"}'
9 fin 128 op 1 masked 128 len 17 mask bcfb74a9 -> b'{"cmd":"release"}'
```

All three are text frames (opcode 1, FIN set). The middle one is the credential the client sent.

## What the server side shows

The unmasked server frames fill in the story. The controller boots with an `ev=hello` banner (`fw 2.4.1`, `dev bay-door-ctl`), reports state, then confirms `auth ok` with a `scoped operator` role after the auth frame, and finally opens the door once the client sends `release`. The `key` in the auth frame is the flag.

## Flag

```
SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}
```

## Notes

Nothing here is a cipher. WebSocket masking is a fixed 4-byte XOR with the key sitting in the frame header, so "the client's messages are not readable" only means nobody reassembled the frames. Once you parse the frame layout the key comes for free. Readable server frames plus scrambled client frames is the signature to look for.
