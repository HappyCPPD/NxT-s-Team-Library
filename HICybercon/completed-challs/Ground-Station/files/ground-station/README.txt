GSC-7 Ground Station Controller -- Validation Toolkit
=====================================================

You are a contracted security engineer validating the GSC-7 fueling/cooling
controller at a satellite ground-support station before a scheduled payload
test is authorized. The controller is reachable over the network. Confirm it
will run the fueling/cooling test SAFELY, correcting whatever is wrong, and the
controller will issue a validation token on a clean test run.

Contents
--------
  gsc-fw.bin         Controller firmware image (maintenance/diagnostic build).
                     Reverse this to recover how the controller authenticates
                     an engineer (the challenge-response for the session nonce).
  GSP_reference.md   Protocol + register/command reference, and the control
                     narrative (the nominal safety program to validate against).
  gsc_tech.py        Thin GSP/1.0 client (framing + relay). Does NOT compute
                     the access response for you.

Requirements
------------
  Python 3.8+ (standard library only) to run gsc_tech.py.
  Your own tools to analyze gsc-fw.bin (a disassembler/decompiler, etc.).

Connecting
----------
  The control service speaks GSP/1.0 (see GSP_reference.md). How you reach it
  depends on where it is running. On the competition deployment the platform
  shows you a HOST and PORT for each exposed endpoint (one for the control
  service, one for the telemetry feed).

  Hosted instance (TLS / SNI) -- the competition deployment:
    The platform's instancer puts a TLS front end in front of the service and
    routes by SNI, so you must speak TLS and send the host as the SNI server
    name. Plain `nc` / plain TCP will NOT work against a hosted instance.

    Manual control session:
        openssl s_client -quiet -connect <HOST>:<PORT> -servername <HOST>

    To keep using gsc_tech.py (it speaks plain TCP), open a local TLS tunnel
    with socat and point the toolkit at the local plaintext port:
        socat TCP-LISTEN:7603,reuseaddr,fork \
              OPENSSL-CONNECT:<HOST>:<PORT>,snihost=<HOST>
        python3 gsc_tech.py --host 127.0.0.1 --port 7603

    Telemetry feed (read-only), same pattern on its own endpoint:
        openssl s_client -quiet -connect <THOST>:<TPORT> -servername <THOST>
      or tunnel it:
        socat TCP-LISTEN:7604,reuseaddr,fork \
              OPENSSL-CONNECT:<THOST>:<TPORT>,snihost=<THOST>

    Use the exact HOST/PORT values the platform shows for your instance.

  Local testing only (docker compose up):
    The local compose stack has no TLS in front of it, so plain TCP applies:
        python3 gsc_tech.py --host 127.0.0.1 --port 7603
        nc 127.0.0.1 7604          # telemetry feed

  Either way, once connected the client prints the session greeting, including:
      NONCE <16 hex>
  Compute the access response for that nonce (from your analysis of gsc-fw.bin)
  and send:
      AUTH <response-hex>
  then proceed with PROG / BACKUP / WDOG / RUNTEST as documented.

Outline
-------
  1. Recover the access derivation from the firmware; authenticate.
  2. Compare the live ladder program (PROG LIST) to the control narrative;
     a safety interlock has been altered. Correct it (PROG SET).
  3. A change alone will not hold -- an integrity watchdog restores a backup
     at test arm. Diagnose and neutralize it.
  4. Run the validation test (RUNTEST). A clean, safe, complete run yields the
     token (hiCTF{...}).
