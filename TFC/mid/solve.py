#!/usr/bin/env python3
"""Char-by-char. Probe every 3 chars. On switch: redo 1 char. Total: 30*6 + 10 + 2 + 2 = 194."""
import socket, ssl

HOST = "mid2-d45cd93b048d33d2.challs.ctf.thefewchosen.com"
PORT = 1337
PLEN = 30; MAXQ = 195
ALPH = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
N = len(ALPH)

def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ss = ctx.wrap_socket(s, server_hostname=HOST)
    ss.connect((HOST, PORT))
    return ss

def read_until(sock, prompt=b"> "):
    d = b""
    while True:
        ch = sock.recv(4096)
        if not ch: break
        d += ch
        if prompt in d: break
    return d.decode()

def query(sock, state, guess):
    sock.sendall(f"{state} {guess}\n".encode())
    resp = read_until(sock)
    ans = flag = None
    for ln in resp.strip().split("\n"):
        ln = ln.strip()
        if ln in ("smaller", "larger", "equal"): ans = ln
        elif ln.startswith("TFCCTF"): flag = ln
    return ans, flag

def mg(prefix, ci):
    return prefix + ALPH[ci] + "0"*(PLEN - len(prefix) - 1)

def main():
    sock = connect()
    read_until(sock)
    zeros = "0"*PLEN; qc = 0; mood = 0

    a0, flag = query(sock, 0, zeros); qc += 1
    if flag: print(f"FLAG: {flag}"); return
    mood = 1 if a0 == "larger" else 0
    print(f"M={mood} Q{qc}", flush=True)

    prefix = ""; pos = 0; PROBE = 3

    while pos < PLEN and qc < MAXQ - 8:
        if pos > 0 and pos % PROBE == 0:
            pa, flag = query(sock, 0, zeros); qc += 1
            if flag: print(f"FLAG: {flag}"); return
            if mood == 0 and pa == "larger":
                print(f"Q{qc}: SWITCH pos={pos}", flush=True)
                mood = 1
                if pos > 0: prefix = prefix[:-1]; pos -= 1
                continue

        lo, hi = 0, N - 1
        while lo <= hi and qc < MAXQ:
            mid = (lo + hi) // 2
            ans, flag = query(sock, mood, mg(prefix, mid)); qc += 1
            if flag: print(f"FLAG: {flag}"); return
            if ans == "smaller": lo = mid + 1
            elif ans == "larger": hi = mid - 1
            elif ans == "equal": lo = mid; break

        ci = max(0, min(N-1, (lo+hi)//2 if lo > hi else lo))
        prefix += ALPH[ci]; pos += 1

        if pos % 6 == 0 or pos == PLEN:
            print(f"  {pos}/{PLEN} q={qc} {prefix[:14]}", flush=True)

    print(f"\nPWD: {prefix} ({len(prefix)}c q={qc})", flush=True)

    for st in [mood, 1-mood]:
        if qc >= MAXQ: break
        ans, flag = query(sock, st, prefix[:PLEN]); qc += 1
        if flag: print(f"FLAG: {flag}"); return
        print(f"  vfy s={st}: {ans}", flush=True)

    sock.close()

if __name__ == "__main__":
    main()