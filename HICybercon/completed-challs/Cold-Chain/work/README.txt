ColdLink Technician Toolkit
===========================

Contents
--------
  coldlink_tech.py       Field service client (CLMP/1.1) for the CM-900.
  CLMP_reference.md      Protocol + register/command reference.
  historian_sample.log   Example of the controller's historian event feed.

Requirements
------------
  Python 3.8+ (standard library only; no third-party packages).

Connecting
----------
The hosted controller endpoints are TLS-terminated (SNI-routed): each one is
served over TLS on the per-instance hostname shown on the challenge page, NOT
as plain TCP. Plain `nc` will NOT work against the hosted instance -- you must
speak TLS and send the right SNI server name (the endpoint's own hostname).

  Control service  -> the "Challenge" endpoint        (CLMP/1.1, port 7601)
  Historian feed   -> the "Historian log feed" endpoint (read-only, port 7602)

Manual commands over the hosted (TLS) endpoint, e.g. the historian feed:

  openssl s_client -quiet -connect <HOST>:<PORT> -servername <HOST>

  (<HOST>:<PORT> is the endpoint host/port from the challenge page; the
   -servername value must equal <HOST> so SNI routes you to your instance.)

To use the Python toolkit against a TLS endpoint, front it with a local
plaintext->TLS tunnel and point the toolkit at the local port, e.g.:

  socat TCP-LISTEN:7601,reuseaddr,fork OPENSSL-CONNECT:<HOST>:<PORT>,snihost=<HOST>
  python3 coldlink_tech.py --host 127.0.0.1 --port 7601 cases
  # (ncat --ssl works too: ncat --ssl <HOST> <PORT>)

Usage (toolkit commands; --host/--port point at the control endpoint, or at a
local tunnel in front of it as shown above):
  python3 coldlink_tech.py --host <host> --port <port> cases
  python3 coldlink_tech.py --host <host> --port <port> sched-list
  python3 coldlink_tech.py --host <host> --port <port> status
  python3 coldlink_tech.py --host <host> --port <port> raw "SCHED GET S9"

Local testing only (docker compose up) -- no TLS in front of the compose
stack, so plain TCP / plain nc apply directly and no tunnel is needed:
  python3 coldlink_tech.py --host 127.0.0.1 --port 7601 cases
  nc 127.0.0.1 7602        # historian feed (plain read-only TCP stream)

Service note
------------
A site reported that every case went into continuous defrost overnight and
will not hold temperature. Use the toolkit to inspect the controller's
schedules and maintenance macros, correct the fault, and confirm the cases
hold below the compliance ceiling. Check STATUS for the site's compliance
evaluation.
