import binascii

SBOX = bytes.fromhex(
    "85dd94f670ae5d4d3482f15be97ff401"
    "d69556bb27d0086dccdec6cb8f5573a5"
    "b45c1e9d482c2eaae0e58eb31638e7e2"
    "83fa50527cf392b0c9f505ec44374084"
    "8b41fd58f0d19ce3c44e765fad5499cf"
    "b98832f9b68c3c12640adbe13efcb5c2"
    "62a7d8141b0b1307bab7f733d23ba4d7"
    "daa22203e898696859317802042497ac"
    "46cdfe57c5c86c60ca1d6bb22bc0a6d9"
    "0df82f23892db1674975bd71477e0ea1"
    "fb0c80c135103fbe9f2966bc1825d47a"
    "8174a91a63965a204f4a79afb842ceed"
    "450f6fa8872af2eae6001130c73d9390"
    "215ee44b8abf7b1f0653ff3a2872d517"
    "9adca039369b26ee8dab6a8651c3d309"
    "197d436561a36e4cdf9e77151c91efeb")

PERM = bytes.fromhex("0a08040e060703000905010d0f0b0c02")

TABLE = bytes.fromhex(
    "8dc4d82953eeab8725e95b51094ba8d7"
    "0aefb3c8ccafd989ae1132b5e71cf52f"
    "69862806f2af089075a388f2bcef41bc"
    "d5fc974537b8d9a0485c2aadebe66cfc"
    "8f1913605c308013ab323b674efb9b4a"
    "b07cb28516cd0215c126973ee975deba"
    "bc5a6a5a0eb7b7523b5c899ecfc4dfe7"
    "a169db92d06883a3de732dd285cafc30"
    "4fae219aef7d2bd4789cdfd700125176"
    "05ad8ad03a0a6fc4dc8b7c8184d37f46"
    "35ae19eaf4a8ff3d0fa05dfd87cd7abd"
    "928d26aa1416b06a24a9063a58673193"
    "e5bd4dcc2babe4652519535dec1a84e5"
    "55a559d81922dbb389d98b20b1e5173e"
    "50d66bd09f00392f0a7b4ef549c20361"
    "ba2f2f58286c9701b71316321578c631"
    "e44da5f3e7deb3c1f496591a95327cd8"
    "de9b2a4ba8f1deabd96f3bee17a9cfad"
    "f0315b1a70f90e7f3131c12387cecc52"
    "5b56751fbc7cf79cd973d73a6cd726e4")

TARGET = bytes.fromhex("976714880a500d160a21f6950eef3481")

assert len(SBOX) == 256 and len(PERM) == 16 and len(TABLE) == 320 and len(TARGET) == 16

SBOX_INV = [0]*256
for i, v in enumerate(SBOX):
    SBOX_INV[v] = i

b = list(TARGET)
for r in range(19, -1, -1):
    K = TABLE[16*r:16*r+16]
    # invert permutation: out2[PERM[i]] = b[i]  ->  b_pre[i] = b[PERM[i]]
    b = [b[PERM[i]] for i in range(16)]
    # invert SBOX
    b = [SBOX_INV[x] for x in b]
    # invert add
    b = [(b[i] - K[i]) & 0xff for i in range(16)]

payload = bytes(b).hex()
print("payload:", payload)
flag = "hiCTF{" + payload + "}"
print("flag:", flag, "len=", len(flag))

# --- verify against the binary's own algorithm ---
def enc(bb, traced=False):
    b = list(bb)
    if traced:
        b[0] ^= 1
    for r in range(20):
        K = TABLE[16*r:16*r+16]
        b = [(b[i] + K[i]) & 0xff for i in range(16)]
        b = [SBOX[x] for x in b]
        o = [0]*16
        for i in range(16):
            o[PERM[i]] = b[i]
        b = o
    return bytes(b)

print("re-encrypt matches TARGET:", enc(bytes(b)) == TARGET)
# gates (argc=1 for stdin, argc=2 for argv) with initial buf[0] = t[0]
t0 = bytes(b)[0]
for argc in (1, 2):
    n = argc + t0
    g1 = ((n*n + 1) % 4) == 0   # if True -> "unreachable"
    g2 = ((n*n) % 3) == 2       # if True -> return 98
    print(f"argc={argc} n={n} unreachable_gate={g1} gate98={g2}")
