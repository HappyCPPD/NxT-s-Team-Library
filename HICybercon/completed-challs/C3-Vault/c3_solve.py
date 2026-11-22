#!/usr/bin/env python3
"""C3-Vault solver — plain mbedtls HMAC-SHA256 (no emulation).

Recovered from the decrypted firmware (project c3_vault_device, ESP-IDF v5.3.1):

    key  = HMAC_SHA256(seed_v2, "c3-vault/device-key/v2\\0" || device_id || generation_LE4)
    resp = HMAC_SHA256(key,     "C3VAULT-AUTH-V2\\0"        || challenge  || device_id)

md_info type 9 == SHA-256 (digest_size 0x20, block_size 0x40); refreshed live challenge
each connection. flag: hiCTF{efus3_cl34r_jt4g_0p3n_nv5_017026ab04}
"""
import hashlib, hmac, socket, ssl, sys, time

DEV = bytes.fromhex('ee0315f3953aad298d7f3f43973ad618')
SEED = bytes.fromhex('826e4e9e65c0ce89f413b7c291bb7e84185c64d4ec8769805227253b985083c5')
GEN = (7).to_bytes(4, 'little')
LABEL = b'c3-vault/device-key/v2'          # + NUL below (app memcpy's 23 bytes = 22 chars + NUL)
PREFIX = b'C3VAULT-AUTH-V2'                # + NUL (copied as 16 bytes)


def device_key():
    info = LABEL + b'\x00' + DEV + GEN      # 43 bytes
    return hmac.new(SEED, info, hashlib.sha256).digest()


def response(challenge):
    msg = PREFIX + b'\x00' + challenge + DEV  # 64 bytes
    return hmac.new(device_key(), msg, hashlib.sha256).hexdigest()


def connect(host, port, wait=60):
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = ctx.wrap_socket(socket.create_connection((host, port), timeout=12), server_hostname=host)
            s.settimeout(6)
            buf = b''
            while b'>' not in buf:
                d = s.recv(4096)
                if not d:
                    break
                buf += d
            if b'CHALLENGE' in buf:
                ch = None
                for ln in buf.decode(errors='replace').splitlines():
                    if ln.startswith('CHALLENGE'):
                        ch = bytes.fromhex(ln.split()[1])
                return s, ch, buf.decode(errors='replace')
            s.close()
        except Exception:
            pass
        time.sleep(3)
    return None, None, None


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else 'c3-vault-169f0ce3f14a.chall.hiddeninvestigations.net'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 1337
    print('[i] device key =', device_key().hex())
    s, ch, banner = connect(host, port)
    if s is None:
        print('[!] no service')
        return 1
    resp = response(ch)
    print('[i] challenge =', ch.hex())
    print('[i] response  =', resp)
    s.sendall(('auth ' + resp + '\n').encode())
    time.sleep(1.2)
    out = b''
    try:
        while True:
            d = s.recv(4096)
            if not d:
                break
            out += d
    except Exception:
        pass
    s.close()
    print('[=]', out.decode(errors='replace'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
