## Grammar

```
program := (fn | stmt)*
fn := 'fn' IDENT '(' [IDENT (',' IDENT)*] ')' block
block := '{' stmt* '}'
stmt := 'let' IDENT '=' expr ';' // declare a variable
 | IDENT '=' expr ';' // assign
 | IDENT '[' expr ']' '=' expr ';' // buffer element store
 | 'if' '(' expr ')' block ['else' block]
 | 'while' '(' expr ')' block
 | 'return' expr ';'
 | 'print' '(' expr ')' ';' // the ONLY output channel
 | 'register' '(' IDENT ')' ';' // IDENT must be a defined fn
 | 'resize' '(' IDENT ',' expr ')' ';' // IDENT must be a buffer
 | expr ';'
expr := INT | IDENT | '(' expr ')' | <unary> | expr <binop> expr
 | IDENT '(' [expr (',' expr)*] ')' // call a user fn
 | IDENT '[' expr ']' // buffer element load
 | 'alloc' '(' expr ')' // new zeroed buffer
 | 'len' '(' IDENT ')' // buffer length
```

* **Values** are 64-bit signed integers (`i64`) and opaque **buffer handles**.
 Decimal and `0x` hex literals; literals wrap mod 2^64.
* **Operators**: `+ - * / %`, comparisons `== != < <= > >=` (yield 0/1),
 logical `&& || !`. `/` and `%` by zero trap.
* Top-level statements are the program body (`main`). Functions may recurse.
 `main` is reserved.

## Buffers

* `b = alloc(n)` returns a handle to a fresh, zeroed buffer of `n` i64s.
 `len(b)` is `n`.
* `b[i]` reads and `b[i] = v` writes element `i`. Every access is
 bounds-checked against the buffer's current length; an out-of-range index
 (including a negative one, which is treated as a large unsigned value) traps
 and kills the program.
* `resize(b, n)` changes `b` to refer to a fresh, zeroed buffer of `n` i64s.
 Previous contents are not preserved.
* `register(f)` installs a defined `fn f` into a dispatch slot that the runtime
 invokes once, at program exit.
