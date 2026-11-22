# Stadia (h4ckc0n 2026, Rev, 300)

**Flag (brace-delimited, as found): `d4rk{w3_br0ught_0urs3lv3s_h3r3_7ars}`**
Literal 3D text line found inside the server-side scene: `d4rk{w3_br0ught_0urs3lv3s_h3r3_7ars}c0de`
(the trailing `c0de` sits *after* the closing `}` and reads as the author/handler tag —
`d4rk` + flag + `c0de` ⇒ "d4rkc0de").

Live target: `http://h4ckc0n.centralindia.cloudapp.azure.com:40100`

## TL;DR
The "game" is a distributed raymarcher: `client.wasm` (4 KB) walks rays in the browser and
asks the server for the scene's distance at each point. The **server** holds the scene.
The flag is a 3D-extruded text card in that server-side distance field, at
x≈0…134, y≈-2…2, z≈0. The client can never show it plainly because it **truncates every
coordinate to a period of 8 world units** before sending it — so the text card gets tiled
into a scrambled "pattern" that looks like a fractal sponge ("…secrets behind its patterns").

Solve = reverse the wasm, learn the (plaintext-count / XOR-scrambled-points) WS framing, then
talk to the server **directly** with full-range coordinates to read the un-tiled object.

## 1. Recon
- `GET /` → page `stad1a-3d`, `<canvas width=128 height=128>`, loads `glue.js`.
- `GET /glue.js` → instantiates `client.wasm`, opens `ws://host/ws`, forwards server frames to
 `on_frame`, drives `tick` on rAF, key presses → `on_key(code)`.
- `GET /client.wasm` → 4241 bytes. Route fuzz (`ffuf`, ~73 paths): only `/`, `/glue.js`,
 `/client.wasm`, `/ws` exist.

## 2. Reversing client.wasm
`wasm-objdump -x` / `wasm-decompile` / `wasm2wat`. Imports: `env.present`, `env.ws_send`,
`env.js_cos`, `env.js_sin`. Exports: `rx_buf, on_frame, on_key, progress, init, tick`.
One data segment: `Z\xd1 7\xc4` at 0x10000 — a 4-byte XOR key.

Key memory layout (byte addresses, from the .wat):
- `0x10000` : 4-byte XOR key `5a d1 37 c4`
- `0x18030 / 0x18034 / 0x18038 / 0x1803c` : throttle / state / count / iteration
- `0x10010` : rx buffer (server frames)
- `0x98010` : object-id list (uint16)
- `0x67F20` : per-object positions (12 floats each)
- `0x98040` : framebuffer base (128*128*4 RGBA at 0x98040)
- `0xA80E0` : saved camera poses (32 slots × 24 B) + saved frame snapshots

**Uplink framing** (`f_g`): `ws_send(0x2A80B0, 6*count+2)`.
Frame = `[count:int16LE, PLAINTEXT]` followed by `6*count` bytes = `count` × `(x,y,z):int16LE`,
XOR'd with the 4-byte key `5a d1 37 c4` (payload only, count is cleartext).

**The truncation bug** (`f_g`, per coordinate):
```
v = (floor(p*0.125 + 0.5) * -8.0 + p) * 128.0 // = 128 * (p - 8*round(p/8))
```
i.e. the client sends `p mod 8` (a 128-units-per-world-unit fixed point in `[-512,512]`).
The client can therefore only ever sample one 8×8×8 periodic cell — the tiling that hides the flag.

**Downlink** (`on_frame`): `len == 2*count`; each int16 = `round(distance * 128)` at the
corresponding query point. The client colours with `d/128`; it is otherwise a pure SDF oracle.

## 3. Talking to the oracle
Frame = `writeUInt16LE(count)` ++ `xor(6*count bytes of int16 xyz)`.
Any valid frame gets a reply of `2*count` bytes (XOR'd with the same key).
Raw probes:
```
pt [0,0,0] -> 102 (d = 0.797)
pt [1,2,3]*128 -> 77 (d = 0.602)
pt [0.5,.5,.5] -> 38 (d = 0.297)
```
So `d = reply/128` (world units), clamped to int16. `len` not of the form `2*count` → dropped.

## 4. Reading the scene
2D slice scans of the field (`ops/rect.js`, `ops/scan2.js`) render `sign/|d|` as pixels.
- Slices through `z≈0` show a rounded-rectangle "card" spanning x≈0…134, y≈-2…2.
- The caption is extruded 3D text.
- `ops/sdf/full_xy.png` (x=-20…145, y=-18…18, z=0) shows it in full; flip vertically
 (`full_xy_flipv.png`) because the render maps +y downward.
- High-res halves: `ops/sdf/half1_xy_fv.png`, `ops/sdf/half2_xy_fv.png`.

Read: `d4rk{ w3_br0ught_0urs3lv3s_h3r3_7ars } c0de`
- half1: `d4rk{w3_br0ught_0urs`
- half2: `s3lv3s_h3r3_7ars}c0de`

Volume checks (`ops/sdf/xz_y0_fv.png`, `yz_x60_fv.png`, extent line-scan to x=255) confirm
this is the **only** object; nothing follows `c0de`, and there is no second text line.

## 5. Flag
```
d4rk{w3_br0ught_0urs3lv3s_h3r3_7ars}
```
The rendered line literally terminates `...7ars}c0de`; the `}` closes the brace group and
`c0de` is the trailing handler tag (`d4rk`…`c0de`). If the platform rejects it, the only
non-guessed alternative is the full literal with the tag inside the braces, but the glyph
order in the SDF clearly shows the `}` before `c0de`.

## Artifacts
- `ops/client.wasm`, `ops/glue.js`, `ops/client.wat`, `ops/client.dcmp`
- `ops/drive.js` (headless client), `ops/sweep.js`/`sweep2.js` (camera sweeps)
- `ops/query.js`, `ops/linescan.js`, `ops/scan.js`, `ops/scan2.js`, `ops/rect.js`,
 `ops/probe*.js`
- `ops/sdf/*.png` — the slice images, incl. the flag card
- `ops/frames*/`, `ops/dl/` — client renders and raw streamed frames
