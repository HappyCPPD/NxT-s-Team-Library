# v8ackup

The service accepts one base64 encoded JavaScript program per connection. It
runs each connection in its own modified V8 `d8` process, prints `--END--`
after that program, and closes the connection. A program can run for up to
180 seconds. Several clients can connect at once.
The handout includes the patch against V8 10.2.154.26.

Available functions:

```js
globalThis.note = "hello";
store("note"); // save the named global string and remove it
print(typeof globalThis.note);
print(use("note")); // restore it and set globalThis.note
show; // list saved names, text in hex, and sizes

globalThis.bytes = new Uint8Array([0, 1, 255]);
store("bytes");
print(Array.from(use("bytes")));
```

Names are strings of 1 to 64 UTF-8 bytes. Values supported by V8's structured
clone format can be stored, up to 2048 serialized bytes. The database persists
across connections and server restarts.

The service runs as `ctfplayer`. The flag is available through the `/readflag`
helper inside the container.

To connect locally: `nc 127.0.0.1 31337`. Send one base64 line per connection.

```sh
(printf 'print(1+2)' | base64 -w0; printf '\n') | nc -N 127.0.0.1 31337
```
