# lsd2

_TODO_

## lsd2 (Rev 500) — SOLVED
Flag: d4rk{tr1pPy_fr4ctl!}c0de

The handout is a Yosys netlist: `core` + `mix`. `tb.v` turns the 24-char flag into six
32-bit chunks and renders a 1024x1024 image (chall.png is the author's render of the real
flag), so the challenge is to invert "flag -> image".

1) `mix` turned out to be XOR-affine (not a colour blend):
 r = 0x60 ^ R0(l0) ^ R3(l3) ^ R5(l5), g = G1(l1) ^ G3(l3) ^ G4(l4),
 b = 0x60 ^ B2(l2) ^ B4(l4) ^ B5(l5) (each R*/G*/B* an 8x8 GF(2) map, all measured
 from the netlist's own `mix` oracle).
2) `core` was reversed from a cycle trace of the netlist (verilator + an instrumented copy):
 it is Newton's method in Q32.32 on the cubic whose coefficients are the chunk bytes,
 p(z) = H0 z^3 + H1 z^2 + H2 z + H3 with H_i = (byte_i - 79)/24, evaluated at the pixel
 coordinate z0 = ((px-512)*7/1024, (py-512)*7/1024), iterated until |step| < 1/2^20,
 then smooth-coloured through the log2 unit (unit_c), the isqrt unit (unit_d) and
 const_rom constants (9/8192, ln2/2, 1/4096, 1/20, 0.9922, 2^20, ...).
 Reimplemented as op_lvl.c (1 us/level) and validated 1200/1200 against the netlist oracle.
3) Because each output channel only touches a subset of the six levels, the chunks fall out
 one channel at a time: c3 from r, (c1,c4) from g by meet-in-the-middle on G1/G4, c2 from b.
 The flag format fixes l0 ("d4rk") and l5 ("c0de"), so those levels are oracle-exact.
 Result: d4rk | {tr1 | pPy_ | fr4c | tl!} | c0de.
4) Proof: with the netlist oracle, all six level fields reproduce chall.png's RGB at
 120/120 and 60/60 random pixels; every case variant of the flag fails.
