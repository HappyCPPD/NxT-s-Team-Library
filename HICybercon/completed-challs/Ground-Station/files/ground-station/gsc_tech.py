#!/usr/bin/env python3
"""
GSC-7 field maintenance client (GSP/1.0).

A thin, protocol-aware terminal for the GSC-7 ground-station controller. It
handles the line framing and prints the controller's session greeting
(including the session NONCE), then relays the commands you type (or pipe in
on stdin) and prints the responses.

It does NOT compute the access-token response for you: the controller's
challenge-response is produced by the controller firmware's access routine
(ship-provided image: gsc-fw.bin). Recover that routine, compute the response
for the session NONCE this client prints, and send:

    AUTH <response-hex>

See GSP_reference.md for the full command/register reference and the control
narrative (the nominal safety program).

Usage:
    python3 gsc_tech.py --host <ip> --port 7603          # interactive
    printf 'AUTH <resp>\\nPROG LIST\\nQUIT\\n' | python3 gsc_tech.py --host <ip>
"""
import argparse
import socket
import sys
import threading


def reader(f):
    try:
        while True:
            raw = f.readline()
            if not raw:
                break
            sys.stdout.write(raw.decode("utf-8", "replace"))
            sys.stdout.flush()
    except OSError:
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=7603)
    o = ap.parse_args()
    s = socket.create_connection((o.host, o.port), timeout=15)
    f = s.makefile("rwb", buffering=0)
    t = threading.Thread(target=reader, args=(f,), daemon=True)
    t.start()
    try:
        for line in sys.stdin:
            f.write(line.rstrip("\n").encode() + b"\n")
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        # let the last responses flush
        import time
        time.sleep(0.3)
        try:
            s.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()
