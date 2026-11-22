#!/usr/bin/env python3
import argparse
import hashlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from cryptography.hazmat.primitives.keywrap import InvalidUnwrap, aes_key_unwrap

SALT = bytes.fromhex("66bb7f773470945916f0a6e2d7a61cd5")
ITERATIONS = 260668
WRAPPED = bytes.fromhex("4dcfae7d63aa3dbaba2debfa20fee1feba1d7f001e63d138")


def check(candidate: bytes):
    key = hashlib.pbkdf2_hmac("sha256", candidate, SALT, ITERATIONS, 16)
    try:
        aes_key_unwrap(key, WRAPPED)
    except InvalidUnwrap:
        return None
    return candidate


def main():
    parser = argparse.ArgumentParser(description="Verify FileVault 2 user-password candidates")
    parser.add_argument("dictionaries", nargs="+", help="candidate files; use - for stdin")
    parser.add_argument("--threads", type=int, default=16)
    args = parser.parse_args()

    candidates = []
    seen = set()
    for path in args.dictionaries:
        stream = sys.stdin.buffer if path == "-" else open(path, "rb")
        with stream if path != "-" else _nullcontext(stream):
            for line in stream:
                candidate = line.rstrip(b"\r\n")
                if not candidate or len(candidate) > 256 or candidate in seen:
                    continue
                seen.add(candidate)
                candidates.append(candidate)

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        for index, result in enumerate(executor.map(check, candidates), 1):
            if result is not None:
                elapsed = time.monotonic() - started
                print(f"FOUND\t{result.decode('utf-8', 'backslashreplace')}\tattempt={index}\telapsed={elapsed:.3f}s")
                return 0
            if index % 10000 == 0:
                elapsed = time.monotonic() - started
                print(f"tested={index} rate={index / elapsed:.1f}/s", file=sys.stderr, flush=True)

    elapsed = time.monotonic() - started
    print(f"tested={len(candidates)} found=0 elapsed={elapsed:.3f}s rate={len(candidates) / elapsed:.1f}/s", file=sys.stderr)
    return 1


class _nullcontext:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_):
        return False


if __name__ == "__main__":
    raise SystemExit(main())
