#!/usr/bin/env python3
"""Exploit skeleton. Two targets, one script.

    python3 solve.py                    # the local replica (see local/)
    python3 solve.py <host> <port>      # the live service, over TLS

The live host and port are shown on the challenge page.
"""
import sys

from pwn import ELF, context, remote   # pip install pwntools

TOKEN = "acc077a7673d70fa34c2e5f769e90abe"
LOCAL_PORT = 13370

exe = ELF("./challenge", checksec=False)
context.binary = exe
# Shipped for libc-dependent challenges — the EXACT libc the remote runs.
# libc = ELF("./libc.so.6", checksec=False)


def connect():
    """Return a live io. Remote when given a host, local replica otherwise."""
    if len(sys.argv) >= 3:
        # Traefik terminates TLS on this port and routes on the SNI, so
        # the connection must be TLS and must carry the hostname.
        host, port = sys.argv[1], int(sys.argv[2])
        io = remote(host, port, ssl=True, sni=host)
    else:
        io = remote("127.0.0.1", LOCAL_PORT)
    io.sendlineafter(b"Token: ", TOKEN.encode())
    return io


def main():
    io = connect()
    # ── your exploit goes here ────────────────────────────────────────
    # offset = 0
    # io.sendline(b"A" * offset + p64(exe.symbols["win"]))
    io.interactive()


if __name__ == "__main__":
    main()
