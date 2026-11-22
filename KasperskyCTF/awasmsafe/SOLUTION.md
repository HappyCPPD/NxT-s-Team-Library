# awasmsafe — solution

**Flag:** `kaspersky{w4sm_3lectrif1ed_7d19ae15}`

## What it is

An Electron app (`safe.html` inside `resources/app.asar`) embeds a gzip-compressed
WebAssembly module in `window.codeBuffer`. The WASM's only interesting export is
`check_flag(ptr)`, which the page wires up as `window.checkFlag(password)`.

## How `check_flag` works

1. Requires the input to be exactly **36 bytes**.
2. Derives a 32-byte RC4 key `r` via a JS callback the WASM invokes through its
 single import `env.e` (a generic `eval` hook): it evaluates
 `window.return(h(document.querySelectorAll('script')[1].textContent, document.querySelectorAll('*')[5].content.split(' ')[1].slice(8,-1)))`.
 - `h(d, s)`: base64-decode `s` into 32 bytes, then add (mod 256) each char
 code of `d` into it cyclically.
 - `d` = the exact source text of the page's second `<script>` block (the
 terminal-emulator logic).
 - `s` = the first CSP `sha256-...` hash from the page's own
 `<meta http-equiv="Content-Security-Policy">` tag.
 So the "key" is self-referential: it's derived from the app's own shipped
 source text and its own CSP hash — both static and recoverable from the
 HTML.
3. Also runs ~55 `eval` fingerprint checks (`window.toString.length`,
 `navigator.toString.length`, `HTMLElement.toString.length`, etc.) plus
 `(typeof global).length` (9 in a real browser/Electron renderer since
 `global` is undefined there, vs. 6 under Node.js — a built-in anti-Node
 killswitch; there's also a literal `try{process.exit(1)}catch(e){}` eval
 for the same purpose). All ~56 results get folded via a small rolling XOR
 mixer into an 8-byte buffer, which is then XORed over a static 36-byte
 ciphertext embedded in the WASM data section. This means the ciphertext is
 only meaningful when evaluated in a genuine Chromium/Electron renderer.
4. A tiny LCG PRNG, seeded with the `(typeof global).length` result (9),
 XOR-decrypts that scrambled 36-byte blob into the real target.
5. The 36-byte input password is RC4-encrypted with key `r`; the result must
 `memcmp` equal to the target from step 4.

Since RC4 keystream XOR is self-inverse and doesn't depend on the message,
`password = target XOR RC4_keystream(r)` — no brute force needed, just
run the real derivation once and solve algebraically.

## How it was actually solved

Static analysis (disassembling the wasm to `.wat`) gave the algorithm, but
steps 2 and 3 needed a genuine browser engine (real `window`/`document`/
`navigator`/etc., and `typeof global === "undefined"`) to produce the correct
numbers — Node.js won't do, by design.

Fix used: patch `libgtk-3`/`libXdamage` into the bundled Electron binary via
user-space `dpkg-deb -x` extraction (no root needed) so the shipped
`awasmsafe` AppImage runs under Xvfb; repack `app.asar` with an
instrumented page that keeps the *original* second `<script>` and CSP `<meta>`
byte-for-byte (so the self-referential key derivation is unaffected), adds an
inert copy plus a small solver script, and reports results back to the Node
main process over Electron IPC (not `executeJavaScript`, which triggers a
DevTools-protocol side effect that hangs on the challenge's `debugger;`
anti-debug spam). That run computed the real `r`, the real scrambled
ciphertext, decrypted the target, solved for the password, and confirmed it
against the live `check_flag` — returned `1` (accepted).

`solve_harness.html` in this folder is an earlier Node.js-based exploration
attempt (kept for reference); it hits the Node killswitch and browser-global
gaps described above, which is exactly what led to the Electron-based
approach above.
