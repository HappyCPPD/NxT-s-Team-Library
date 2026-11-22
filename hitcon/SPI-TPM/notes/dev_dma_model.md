# spi-tpm-dma — device model + bounds-analysis verdict

Artifact: `SPI-TPM/spi-tpm-pwn/src/qemu-system-aarch64`
(x86-64, 11 MB, stripped, PIE). Source file per embedded assert strings:
`/tmp/spi-tpm-build/build/sources/qemu/hw/ssi/spi_tpm_dma.c` (+ `include/hw/ssi/spi_tpm_dma.h`).

Address conventions: **all addresses below are objdump/r2 vaddrs** (file vaddr). Ghidra loads the
PIE at 0x100000, so `ghidra_addr = vaddr + 0x100000`.
Evidence: `objdump -d --start-address=0x2ae000 --stop-address=0x2b1e00` (dumped at
`/var/tmp/spitpm/dev.txt`), r2dec pseudo-code (`/var/tmp/spitpm/r2dma.out`),
cached Ghidra decompile of `0x3ae3f0`, and the raw `.rodata` jump tables at 0x7e3de0 / 0x7e3e34.
Every claim is tagged **[CONFIRMED]** (instruction read + table decoded) or **[INFERRED]**.

Key vaddrs: MMIO ops table `0x9b6b60`; write handler `0x2ae5b0`; read handler `0x2ae9f0`;
`realize` `0x2aeb70`; reset `0x2aed00`; unrealize/reset-helper `0x2aed90`; per-channel free
`0x2ae3f0`; per-channel abort `0x2ae380`; channel validate/start `0x2ae520`;
mdma chain step `0x2aee50`; timer bottom-half `0x2af000`; TX path `0x2af1e0`; RX path `0x2af350`;
`address_space_{read,write}` helper `0x2ebd70`; global system AddressSpace `0xb39e40`;
debug/enable flag byte `0xb3b6c1` (bit 3 = "unsupported register" logging).

---

## 1. Device model

### 1.1 `realize` (`0x2aeb70`) — [CONFIRMED]

```
S = rdi (DeviceState*)
S+0x50c = 0x400 ; 2aebb3 movl $0x400,0x50c(%rax)
memory_region_init_io(S+0x330, owner, &ops(0x9b6b60), S, name, /*size*/0x200) ; 2df110
 -> MMIO region is 0x200 bytes, opaque = S
S+0x530 = timer_new(QEMU_CLOCK_VIRTUAL, cb = 0x2af000) ; g_malloc0(0x30) + 0x7421a0
```
Note the class also registers reset `0x2aed00` (class+0x70) and `0x2aec90` (class+0x90).
**[CONFIRMED] the max-chunk constant S+0x50c is `0x400`, not 0x200** (0x200 is the MMIO window size).

`reset` (`0x2aed00`): timer_del(S+0x530); g_free(S+0x520); zero S+0x510..0x52f; `for ch in 0..2:
0x2ae3f0(S,ch)`; S+0x508 = 0; `qemu_set_irq(S+0x440, 0)`. **[CONFIRMED]**

### 1.2 Register file — guest MMIO offsets

There are **three channels**, `ch = (off >> 6)` for `off <= 0xff`; offsets 0xc0–0xff (`ch == 3`) are
rejected. Register index inside a channel is `off & 0x3f`. **[CONFIRMED]** from both handlers and
from the two `.rodata` jump tables (write table @0x7e3de0, read table @0x7e3e34).

| guest off | ch-base off | name | R/W | meaning |
|---|---|---|---|---|
| `ch*0x40 + 0x00` | +0x00 | `sg_lo` (reg0) | RW | low 32 bits of SG-table guest address. Read returns **8 bytes** (`ch+0x00..0x07`). |
| `ch*0x40 + 0x04` | +0x04 | `sg_hi` (reg1) | RW | high 32 bits of the SG-table guest address (read as u32). |
| `ch*0x40 + 0x08` | +0x08 | `count` (reg2) | RW | number of SG entries; must be 1..0x100 at arm time. |
| `ch*0x40 + 0x0c` | +0x0c | `total` (reg3) | RW | "declared total length" (sum of SG entry lengths). |
| `ch*0x40 + 0x10` | +0x10 | `mode` (reg4) | RW | must be 1, 2 or 4 for a channel to start. |
| `ch*0x40 + 0x14` | +0x14 | `cmd` | **W only** | bit0 = ARM/start, bit1 = STOP/free. (read → default/0) |
| `ch*0x40 + 0x18` | +0x18 | `state` | **R only** | 1=ARMED, 2=RUNNING, 4=DONE, 8=IDLE. (write → default) |
| `0x100` | — | `irq/status` | R | `S+0x508` done-channel bitmask |
| `0x104` | — | `irq_ack` | W | `S+0x508 &= ~value`; then irq = (S+0x508 != 0) |
| `0x108` | — | `busy` | R | `(S+0x520 != 0)` — mdma staging buffer busy |

Any other offset ≤0xff, or >0xff other than 0x100/0x104/0x108, is "unsupported": if
`(*(u8*)0xb3b6c1 & 8)` it logs `"%s: unsupported read/write at 0x%lx\n"`, else returns 0
(write: `0x2ae5f9`/`0x2ae640`; read: `0x2aea30`/`0x2aea80`). **[CONFIRMED]**

### 1.3 State layout (offsets from device base `S`)

```
S+0x330 : MemoryRegion (mmio, size 0x200)
S+0x440 : qemu_irq out (level = (S+0x508 != 0), driven by qemu_set_irq @0x5d4560)
S+0x448 : channel[0] (0x40 bytes each; channel[n] at S+0x448+0x40*n)
S+0x488 : channel[1]
S+0x4c8 : channel[2] ("mdma")
S+0x508 : u32 done_mask (bit n = channel n done)
S+0x50c : u32 max_chunk = 0x400 (set in realize)
S+0x510 : u64 mdma/ch2 dest guest address (staging write target)
S+0x518 : u32 mdma/ch2 current chunk length
S+0x520 : void* mdma staging buffer (g_memdup2 copy, freed after the timer write)
S+0x528 : u32 phase (= channel index 2 inside the timer BH; also "chunk in flight" flag)
S+0x52c : u32 generation snapshot for the in-flight chunk
S+0x530 : QEMUTimer* (callback 0x2af000, virtual clock)

channel (0x40 bytes):
 +0x00 sg_lo (u32) +0x04 sg_hi (u32) -> 64-bit SG-table guest address
 +0x08 count (u32) 1..0x100 +0x0c total (u32)
 +0x10 mode (u32) in {1,2,4}
 +0x14 state (u32) 1=ARMED 2=RUNNING 4=DONE 8=IDLE
 +0x18 void* sg (host copy of the descriptor table, count*0x18 bytes, g_malloc0_n)
 +0x20 u32 sg_index +0x24 u32 byte_offset_in_entry
 +0x28 u32 generation
 +0x30 void* data buffer (g_memdup2, *caller supplied* size) +0x38 u32 data_len_used

SG entry (0x18 bytes, guest-supplied, read in by address_space_read at arm time):
 +0x00 u64 tx_addr (source guest physical address for the TX path 0x2af1e0)
 +0x08 u64 dst_addr (destination guest physical address for the RX path / mdma chain)
 +0x10 u32 length (LOADED AS 32-BIT; the only field the arm-time validator inspects)
```
**[CONFIRMED]** for the channel layout (all reads/writes in the handlers use
`0x448+ch*0x40+{0,4,8,c,10,14,18,20,24,28,30,38}`) and for the entry layout
(`mov 0x10(%rcx),%edx` = len, `add 0x8(%rcx),%rax` = dst, `mov (%rax),%rsi` = src).
Corrections to the earlier map: `S+0x50c` is 0x400 (not 0x200); `ch+0x04` is *not* unused — it is
the high half of a 64-bit SG-table address (the arm code does a **64-bit** load of `ch+0x00`).
`S+0x528` (phase) is literally the channel index of the in-flight mdma chunk (always 2).

### 1.4 MMIO write handler `0x2ae5b0` — [CONFIRMED]

```
w(S, off, value):
 if (off > 0xff) { if (off == 0x104) goto ack; else unsupported; return; }
 ch = off >> 6; if (ch == 3) unsupported;
 r = off & 0x3f; if (r > 0x14) unsupported;
 switch (r) via table @0x7e3de0: # index = raw offset, word width 4
 0x00: *(u32*)(S+0x448+ch*0x40+0x00) = value # sg_lo
 0x04: *(u32*)(S+0x448+ch*0x40+0x04) = value # sg_hi
 0x08: *(u32*)(S+0x448+ch*0x40+0x08) = value # count
 0x0c: *(u32*)(S+0x448+ch*0x40+0x0c) = value # total
 0x10: *(u32*)(S+0x448+ch*0x40+0x10) = value # mode
 0x14: ch_cmd(S, ch, value) # 0x2ae660
ack: S+0x508 &= ~value; qemu_set_irq(S+0x440, (S+0x508 != 0));
```
`ch_cmd` (`0x2ae660`):
```
 if (value & 2) { 0x2ae3f0(S, ch); } # STOP: full channel free/reset
 if (value & 1) { arm(S, ch); } # ARM (0x2ae768)
 return 0;
```
**No channel-state check precedes any of these stores** — sg_lo/sg_hi/count/total/mode can be
rewritten at any time, including while the channel is RUNNING or while an mdma chain is in flight.
This is the enabler for the bugs in §3.

### 1.5 `arm(S, ch)` (`0x2ae768`) — [CONFIRMED]

```
S+0x508 &= ~(1<<ch) # rol 0xfffffffe
ch->gen++; g_free(ch->sg); ch->sg = 0; ch->state = 1 (ARMED); ch->sg_index = 0;
if (*(u64*)(ch+0x00) == 0) -> abort_ch(S,ch) # reg0:reg1 == 0
if ((u32)(ch->count - 1) > 0xff) -> abort_ch(S,ch) # count in 1..0x100
ch->sg = g_malloc0_n(count, 0x18);
r = address_space_read(as, ch->sg_addr64, 0x100000000, ch->sg, count*0x18, /*write*/0);
if (r != 0) -> g_free(ch->sg); ch->sg = 0; abort_ch(S,ch);
sum = 0;
for (i=0; i<count; i++) { if (entry[i].len == 0) -> g_free(ch->sg); abort_ch(S,ch); sum += entry[i].len; }
if (sum != ch->total) -> g_free(ch->sg); abort_ch(S,ch);
qemu_set_irq(S+0x440, S+0x508 != 0);
```
So at arm time: descriptor table is copied from guest `sg_addr64`, `count*0x18` bytes, into a host
buffer allocated with exactly that size; every entry must have non-zero length; and
`sum(entry.len) == total`, where lengths are treated as 32-bit.
`abort_ch` = `0x2ae380`: free `ch+0x30` buffer, free `ch+0x18` sg, `ch+0x38=0`, `ch+0x20=0`,
`ch+0x14=8` (IDLE), `ch->gen++`. It does **not** clear the done bit or touch reg0..reg4.
(The STOP path uses `0x2ae3f0` instead, which additionally zeroes reg0..mode/state and clears the
done bit for that channel.)

### 1.6 MMIO read handler `0x2ae9f0` — [CONFIRMED]

```
r(S, off):
 if (off == 0x100) return S+0x508;
 if (off == 0x108) return (S+0x520 != 0) ? 1 : 0;
 if (off > 0xff) unsupported;
 ch = off>>6; if (ch==3) unsupported; r = off & 0x3f; if (r > 0x18) unsupported;
 switch (r) via table @0x7e3e34:
 0x00: return *(u64*)(S+0x448+ch*0x40+0x00) # sg_lo|sg_hi<<32
 0x04: return *(u32*)(...+0x04) # sg_hi
 0x08: return count
 0x0c: return total
 0x10: return mode
 0x18: return state
```
Note the asymmetry: the *command* register is at guest offset `+0x14` (write-only) and the *status*
register is at `+0x18` (read-only), even though both refer to the same internal field `ch+0x14`
(`state`).

### 1.7 `validate/start` (`0x2ae520`) — [CONFIRMED]

```
int start(S, ch, arg): # called as start(S, 1, len) / start(S, 0, len) / start(S, 2, len)
 if (arg == 0) goto fail;
 if (ch->state != 1) goto fail;
 if (ch->total != arg) goto fail;
 if (ch->sg == 0) goto fail;
 if (ch->mode != 1 && ch->mode != 2 && ch->mode != 4) goto fail;
 ch->state = 2; return 1;
fail: abort_ch(S,ch); return 0;
```
Crucially, it re-checks only `total == arg` and `state == 1`; it does **not** re-check
`sum(entry.len) == total` and does **not** re-read the descriptor table. Since `total` is freely
guest-writable (§1.4), the invariant established at arm time (`sum == total`) is broken by a single
MMIO store between arm and start.

---

## 2. The three data-movement paths

All three funnel through `0x2ebd70`, whose signature is
`(AddressSpace *as, hwaddr guest, u64 max, void *hva, size_t len, bool is_write)`
with `as = &system address space` at `0xb39e40`, `max = 0x100000000` and `is_write` in `r9d`.

### 2.1 TX / "spi read" path `0x2af1e0(S, len, dstbuf)` — called from the SPI-TPM device @`0x2b0eba`

```
if (!start(S, 1, len)) return 0; # channel 1; requires ch1.total == len
sg = ch1->sg; # 0x4a0
ebp = 0; idx = 0;
while (ebp < len) {
 e = &sg[idx]; # sg + idx*0x18 <-- NO bounds check on idx
 chunk = min((u32)e->len, len - ebp);
 address_space_read(as, e->tx_addr /*+0x00*/, 0x100000000, dstbuf + ebp, chunk, 0);
 ebp += chunk; idx++;
}
```
Copies exactly `len` bytes from guest physical addresses listed in `sg[i].tx_addr` into the SPI
device buffer. On an `address_space_read` error it frees ch1's buffer and sg and sets ch1 IDLE
(`0x2af2bd`). Note the loop advances `idx` until `ebp >= len` **with no `idx < count` test**.

### 2.2 RX path `0x2af350(S, len, srcbuf)` — called @`0x2b0afc` and @`0x2b0d58`

```
if (ch2->state == 1 && ch2->total == len && ch2->sg != 0) { # 0x2af508
 if (!start(S,2,len)) return 0; if (!start(S,0,len)) {free ch2; return 0;}
 ...
}
else if (!start(S,0,len)) return 0; # 0x2af380

if (len) {
 sg0 = ch0->sg; ebp = 0; idx = 0;
 while (ebp < len) {
 e = &sg0[idx]; # NO bounds check on idx either
 chunk = min((u32)e->len, len - ebp);
 address_space_write(as, e->dst_addr /*+0x08*/, 0x100000000, srcbuf + ebp, chunk, 1);
 ebp += chunk; idx++;
 }
 if (ch0->state == 2) { ch0->state = 4; S+0x508 |= 1; free ch0 buf/sg; qemu_set_irq(S+0x440,1); }
 else { S+0x508 |= 1; ch0->state = 4; } # 0x2af650
 ...
}
# mdma mirror: only in the "ch2 was armed and matched" branch (reached via 0x2af748)
if (flag == 1 && len != 0) { # 0x2af5d0
 g_free(ch2->buf /*0x4f8*/); ch2->buf = g_memdup2(srcbuf, len); ch2->buflen /*0x500*/ = 0;
 if (ch2->state == 2 && S+0x520 == 0) 0x2aee50(S); # kick the DMA chain
}
```
The RX path therefore (a) writes the response to guest memory through ch0's descriptors using
`sge->dst_addr` (`+0x08`), and (b) allocates the ch2 mirror buffer with **exactly `len` bytes**
(`g_memdup2(srcbuf, len)` @0x2af5fb, stored to 0x4f8 @0x2af600) and starts the mdma chain.

### 2.3 mdma chain step `0x2aee50(S)` — [CONFIRMED, this is the bug site]

```
idx = S+0x4e8; if (idx >= S+0x4d0 /*count*/) goto done; # count re-read live
buf = S+0x4f8; if (buf == 0) goto fail;
e = S+0x4e0 + idx*0x18; # sg = S+0x4e0
chunk = (u32)e->len /*+0x10*/ - (u32)S+0x4ec /*offset*/; # 32-bit sub
chunk = min(chunk, S+0x50c /*0x400*/); # cmova
buflen = S+0x500;
if (S+0x4d4 /*total*/ < buflen + chunk) goto fail; # <-- THE ONLY GUARD
S+0x520 = g_memdup2(buf + buflen, chunk); # src = buf+buflen, len = chunk <-- OOB READ
S+0x500 += chunk;
S+0x510 = (u32)e->dst_addr /*+0x08*/ + S+0x4ec /*offset*/; S+0x518 = chunk;
S+0x528 = 2 /*phase == ch index*/; S+0x52c = S+0x4f0 /*gen*/;
timer_mod(S+0x530, qemu_clock_get_ns + 10ms); # 0x989680 ns
done: free buf/sg; gen++; S+0x508 |= 4; ch2->state = 4; qemu_set_irq(S+0x440,1);
fail: free buf/sg; gen++; ch2->state = 8;
```

### 2.4 timer bottom-half `0x2af000(S)` (hardwired to channel 2) — [CONFIRMED]

```
if (S+0x520 == 0 || S+0x528 /*phase*/ > 2) return;
chunk = S+0x518; gen = S+0x52c; dst = S+0x510;
err = address_space_write(as, dst, 0x100000000, S+0x520, chunk, 1); # staging -> guest
g_free(S+0x520); S+0x510..S+0x52f = 0; # staging cleared
c = S + phase*0x40; # phase == 2 -> channel 2
if (err) { if (c->state == 2 && c->gen == gen) { free buf/sg; gen++; state = 8; } return; }
if (c->state == 2 && c->gen == gen) {
 S+0x46c /*offset*/ += chunk;
 if (S+0x46c == sg[S+0x468].len) { S+0x46c = 0; S+0x468 /*idx*/++; }
}
if (S+0x4dc == 2 && S+0x520 == 0) 0x2aee50(S); # next chunk
```
Offset is clamped to the current entry's length here, so `offset <= entry.len` is maintained by the
device itself as long as the sg array is not modified — see however §3(a)/§3(b) below, where the
buffer the copy reads from is *not* covered by that invariant.

---

## 3. Bounds-analysis verdict

Notation: `buf2 = *(void**)(S+0x4f8)` (ch2 mirror buffer), `buflen = *(u32*)(S+0x500)`,
`total = *(u32*)(S+0x4d4)` (= ch2 guest reg3), `cnt = *(u32*)(S+0x4d0)` (= ch2 guest reg2).

### 3.1 Every read/write of a device heap buffer or guest memory

| # | site | intended size | actual length used | offset/index bound | verdict |
|---|---|---|---|---|---|
| 1 | `arm` `g_malloc0_n(count,0x18)` + `address_space_read(...,count*0x18)` (0x2ae841/0x2ae881) | `count*0x18` | same, `count ∈ 1..0x100` checked | n/a | **safe** |
| 2 | `arm` entry scan `mov (%rdx),%eax` @0x2ae8d0 | `count` entries | exactly `count` | loop bounded by `count*0x18` end pointer | **safe** |
| 3 | `0x2aee50` `g_memdup2(buf2+buflen, chunk)` @0x2aef1e | `sizeof(buf2)` = **`len` at allocation time** | `chunk = min(sge[idx].len - offset, 0x400)` | only `total >= buflen+chunk`, and `total` is a **live guest register** | **BROKEN — host heap OOB read (see 3.2b)** |
| 4 | `0x2aee50` `sg` array read `S+0x4e0 + idx*0x18` @0x2aee7a/0x2aee8b | `count_arm*0x18` | `idx < cnt` (live guest `count`) | **not** bounded by `count_arm` | **BROKEN — host heap OOB read (3.2a)** |
| 5 | `0x2af1e0` loop `sg[idx]` @0x2af283/0x2af287/0x2af28a | `count_arm*0x18` | `idx` unbounded (loop ends on `ebp >= len`) | **no `count` check at all** | **BROKEN — host heap OOB read (3.2c)** |
| 6 | `0x2af350` loop `sg0[idx]` @0x2af40f/0x2af413 | `count_arm*0x18` | `idx` unbounded (loop ends on `ebp >= len`) | **no `count` check at all** | **BROKEN — host heap OOB read (3.2c)** |
| 7 | `0x2af1e0` write into caller buffer `dstbuf+ebp` | caller buffer (`len` bytes, memset by caller) | `chunk ≤ len-ebp`, loop `ebp < len` | ok | **safe** |
| 8 | `0x2af350` write into guest via `dst_addr` | `chunk` | `chunk ≤ len-ebp` | guest address is unchecked but goes through `address_space_write` (guest phys only) | **safe w.r.t. host; arbitrary guest-physical write (by design)** |
| 9 | `0x2af000` `address_space_write(dst,staging,chunk)` | `chunk` = `S+0x518` | staging size == chunk (from #3) | n/a | **safe** (reads the OOB data produced by #3) |
| 10 | `0x2af350` `g_memdup2(srcbuf, len)` @0x2af5fb | `len` | `len` | n/a | **safe** (this is what sets the buffer size used by #3) |

### 3.2 The four chase questions

**(a) Is the SG array indexed with a guest-controlled index, and is the entry count bounded?**
- The index itself (`ch+0x20` = `S+0x4e8`) is *not* directly guest-writable — the MMIO map exposes
 only `+0x00/+0x04/+0x08/+0x0c/+0x10/+0x14` and `+0x18` per channel. So the index is device-driven.
- **But the bound is guest-controlled and live.** `0x2aee5e: cmp 0x4d0(%rbx),%eax` reads the *live*
 `count` register (guest offset `ch*0x40+0x08`). The sg array was allocated with
 `count_at_arm` entries. Writing a larger `count` after arming lets `idx` walk past the allocation.
- Worse, paths `0x2af1e0` and `0x2af350` perform **no `count` check whatsoever** — their loop
 condition is purely the byte counter (`ebp < len`). So there the walk length is controlled only by
 whether `sum(entry.len)` reaches `len`.
**Verdict: CONFIRMED — the entry count is a live guest register, and two of the three SG walkers do
not check it at all.** Where does `sg_lo/count/total` get used? `reg0`/`reg1` are latched only at arm
time (used once as the `address_space_read` source); `count` is used at arm time for the allocation
*and* re-read live in `0x2aee50`; `total` is used at arm time for the sum check and re-read live in
`0x2aee50` and in `validate`.

**(b) Is `declared_total` (S+0x4d4) equal to the allocation size of the buffer at S+0x4f8?**
**No — and it can be made larger, giving a host heap OOB read leaked to the guest. CONFIRMED.**
- The buffer is allocated in the RX path only: `0x2af5fb call g_memdup2` with `rsi = r13d = len`
 (the SPI transfer length), stored to `S+0x4f8` at `0x2af600`, and `S+0x500 = 0` at `0x2af5ef`.
 ⇒ **allocation size == `len` at that instant**.
- `S+0x4d4` (ch2 `total`) is only ever *compared*, never used as an allocation size
 (`0x2aeea2`, `0x2af508`). It is set by the guest write to offset `0x80+0x0c = 0x8c`
 (write table index 0x0c → `0x2ae718`, `mov %eax,0x454(%r11,%rcx,1)` with `rcx = ch*0x40`).
- The only link between them is the transient equality check `total == len` at `0x2af508` /
 in `validate`, and the guard `total >= buflen + chunk` in `0x2aee50`. Both read `total` **fresh**,
 10 ms apart from the allocation, while the guest can rewrite it at any time:
 `0x2aeea2: cmp %esi,0x4d4(%rbx); jae 0x2aef10`.
- Consequence: `chunk = min(sge[idx].len - offset, 0x400)` is bounded by the entry lengths that were
 only ever validated against the **arm-time** value of `total`; `buflen` accumulates real data
 length. Raising `total` after the chain starts lets `buflen + chunk` grow past the `len`-byte
 allocation, and `g_memdup2(buf2 + buflen, chunk)` at `0x2aef12/0x2aef1e` reads **out of bounds**.
 The stolen bytes are then `address_space_write`-n to the guest at `sge[idx].dst_addr`
 (`0x2af05c`..`0x2af07e`) → **direct host-heap disclosure to the guest**.
- Note the asymmetry that makes it reachable without triggering the "not armed" fallback: the chain
 only starts when `total == len`, so arm ch2 with `total = A` (entries summing to `A`, `A ≥ 0x800`),
 then set `total = len = 0x400` right before the SPI RX, then set `total = A` again immediately
 after the RX MMIO access returns. No MMIO store happens during the first chain step, so the first
 `chunk` is validated against `total == len == 0x400` (in bounds), and every subsequent step sees
 the raised `total`.

**(c) Can the guest control SG entry addresses/lengths so that address_space_read/write reach
outside guest RAM, or overflow the device buffer?**
- Addresses: yes, the guest fully controls `e->tx_addr` / `e->dst_addr`, and they are passed
 unvalidated (other than `max = 0x100000000`) to `address_space_read/write`. Because they go
 through the address space, they cannot reach **host** memory — only guest physical space, which
 includes other devices' MMIO and RAM. So this is an "arbitrary guest-physical DMA" primitive, not
 a host escape by itself. **INFERRED** (the helper's bounds behaviour is not in this code; QEMU's
 `address_space_*` always resolves through MemoryRegions).
- Lengths: `chunk = min(sge.len, len - ebp)`, clamped by the loop bound, so device-buffer **writes**
 (`#7`) stay inside the caller buffer, and the total guest traffic is exactly `len`. **CONFIRMED
 safe** for #7/#8.
- The one thing that *does* escape is the sg **index** (rows #4/#5/#6): if `sum(entry.len) < len`
 (i.e. `total` raised above the arm-time sum, or ch0/ch1's `total` swapped to `len` ≠ arm-time sum)
 the walkers read `sg + idx*0x18` past the `count_at_arm*0x18` allocation. The garbage `len`/`addr`
 harvested there drives further `address_space_read`/`write` — 24 bytes of host heap per step are
 consumed as (address,length) and, in the RX path, the device buffer contents are written to
 `garbage_addr + offset`. **CONFIRMED** (instructions quoted in rows #5/#6; no `count` operand
 exists in those loops).

**(d) Any host pointer or length derived from a guest register without validation?**
- `sg_lo/sg_hi` (ch+0x00) → used only as `address_space_read` source at arm time; destination is a
 freshly sized host buffer. **Safe.**
- `count` (ch+0x08) → allocation size (`g_malloc0_n(count,0x18)`, count ≤ 0x100 enforced at arm) but
 **re-read live** as a loop bound in `0x2aee50`, and ignored entirely in `0x2af1e0`/`0x2af350`.
 **Unvalidated re-use — OOB (rows #4/#5/#6).**
- `total` (ch+0x0c) → used as a *length guard* against a buffer whose size is unrelated to it, and
 re-read live. **Unvalidated re-use — OOB read (row #3).**
- `mode` (ch+0x10) → only `∈ {1,2,4}` checked. Safe.
- The 32-bit subtraction `sge.len - offset` (`0x2aee8e`): if `offset > sge.len` the u32 underflow
 makes `chunk` huge, which `cmova` then clamps to `0x400` (`0x2aee96`) — the clamp saves the chunk
 size, but the following guard still only compares against `total`, so this is another route to the
 same #3 OOB (reachable when `total` is large). **CONFIRMED (mechanism), INFERRED (reachability).**

---

## 4. Ranked candidate memory-safety violations

### V1 — ch2 mdma mirror buffer: host heap OOB read disclosed to the guest (CRITICAL) [CONFIRMED]
Site `0x2aee50` (`g_memdup2(buf2+buflen, chunk)` @ `0x2aef12`/`0x2aef1e`) guarded only by
`0x2aeea2 cmp %esi,0x4d4(%rbx)`.
Trigger:
1. In guest RAM build a descriptor table for **ch2** with ≥2 entries of `len = 0x400`
 (`dst_addr[i]` = a guest address you can read back, e.g. scratch RAM). Sum = `A` (e.g. 0x800/0x1000).
2. `w(0x80, table)`, `w(0x84, 0)`, `w(0x88, N)`, `w(0x8c, A)`, `w(0x90, 1)`, `w(0x94, 1)` → ch2 ARMED.
3. Build a ch0 (RX) descriptor table with 1 entry of `len = L = 0x400`; `w(0x00, tbl)`,
 `w(0x08, 1)`, `w(0x0c, L)`, `w(0x10, 1)`, `w(0x14, 1)` → ch0 ARMED.
4. `w(0x8c, L)` — make ch2 `total` equal the transfer length (needed to pass `0x2af508`).
5. Perform an SPI RX of `L` bytes on the SPI-TPM device so the SPI device calls
 `0x2af350(S, L, T+0x30485)`: both channels validate, `buf2 = g_memdup2(src, L)` (0x400 bytes),
 chain step 1 copies `buf2[0..0x400)` (in bounds) and arms the 10 ms timer.
6. Immediately `w(0x8c, A)` (or `0xffffffff`).
7. On each subsequent 10 ms tick, `0x2aee50` computes `chunk = 0x400` and the guard
 `total(A) >= buflen+chunk` passes, so `g_memdup2(buf2+0x400, 0x400)`, `...buf2+0x800,...` read past
 the 0x400-byte allocation; `0x2af000` writes those bytes to guest `entry[i].dst_addr`.
Expected effect: up to `(N-1) * 0x400` bytes of host heap (glib chunk metadata / neighbouring
allocations) leaked into guest-readable RAM; also a latent read-past-end crash if the heap ends.
Same trick works with `total` raised and `chunk` forced by the u32-underflow clamp.

### V2 — unbounded SG walk in the TX/RX loops → host heap OOB read + arbitrary guest-physical DMA (HIGH) [CONFIRMED]
Sites `0x2af283`–`0x2af2b4` (ch1/TX) and `0x2af40f`–`0x2af442` (ch0/RX): loop bound is only
`ebp < len`; `sg[idx]` has no `count` test.
Trigger: arm ch0 (or ch1) with `total = X` and entries summing to `X` (small, e.g. one entry
`len = 0x10`), then `w(ch*0x40+0x0c, len)` with a **larger** `len`, then drive an SPI transaction of
`len` bytes. `validate` only checks `total == len` ⇒ passes. The loop then reads `sg[1], sg[2], …`
past the `count*0x18` allocation, using the garbage as guest addresses/lengths.
Expected effect: ~24 bytes of host heap consumed per iteration as an (addr,len) pair; in the RX
direction the device buffer is written to heap-derived guest addresses (guest-memory corruption /
targeted MMIO writes); plus a likely crash if the heap value is an invalid guest address.

### V3 — `count` raised after arm → OOB read of the ch2 sg array (MEDIUM) [CONFIRMED mechanism]
Site `0x2aee58/0x2aee5e` (live `count`) + `0x2aee7a` (`sg + idx*0x18`).
Trigger: arm ch2 with `count = 2`, start the chain as in V1, then `w(0x88, 0x100)`; as entries are
consumed `idx` grows past 2 and `sg[idx]` reads past the 0x30-byte allocation, taking `len`/`dst_addr`
from the heap. Effect: OOB read driving a guest-physical write to a heap-derived address; the leaked
heap bytes themselves are not directly disclosed (unlike V1).

### V4 — unvalidated descriptor addresses ⇒ arbitrary guest-physical DMA from device context (LOW/INFO) [CONFIRMED]
`e->tx_addr` (`+0x00`) and `e->dst_addr` (`+0x08`) are passed straight into `address_space_read/write`
(`0x2af2b4`, `0x2af442`, `0x2af07e`). Guest RAM is the guest's own; the interesting part is that the
copy is performed by the device (different execution context) into any guest MMIO region, e.g. the
DMA device's own registers (re-entrancy), the SPI-TPM device, or the GIC. No host-memory access.

### V5 — writes with no channel-state check (LOW, enabler) [CONFIRMED]
`sg_lo/sg_hi/count/total/mode` are writable at any time (no state test in the write table cases).
This is what lets `total` be swapped between arm/validate/chain and `count` be enlarged.

---

## 5. What would settle the remaining uncertainty (no fabrication)
1. **Buffer size of `0x4f8`** — set a breakpoint on `g_memdup2` at `0x2af5fb` (rsi) and on the arm
 allocation at `0x2ae841` (rdi/rsi) while running the guest with `count=2, len=0x400` to confirm
 the 0x400 allocation and the 0x400/0x800 chunk sequence.
2. **Leak confirmation** — with `entry[1].dst_addr` pointing at guest scratch RAM, read it back after
 the second timer tick; bytes beyond the 0x400-byte allocation = proof (compare with a
 `G_DEBUG=gc-friendly` / `QEMU_MALLOC` pattern or a heap canary).
3. **Sizes of the SPI device buffers** `T+0x20486` (TX destination) and `T+0x30485` (RX source):
 the caller `memset`s them with a length taken from `*(u16*)(T+0x464)`; the field spacing is
 0xFFFF/0xFFFF, so `len` can be at most 0xffff — verify the declared array sizes before assuming
 the SPI-side buffers are ≥ `len` (this is the SPI-TPM device, not this device).
4. **Reachability of `len ≥ 0x800`** — confirm the guest can drive a SPI transfer long enough to need
 ≥2 mdma chunks (i.e. `T+0x464`/`T+0x40490` can exceed 0x400).
5. **`*0xb39e40` identity** — confirm it is `address_space_memory` (system AS) by checking the
 initialiser that stores the symbol; this decides whether the DMA can target the whole guest
 address space or only a restricted one.

## 6. Corrections/extensions to the provided state map
- `S+0x50c` = **0x400** (max chunk); 0x200 is the MMIO region size (`memory_region_init_io` r9).
- `ch+0x04` (`sg_hi`) is **not** unused: `arm` loads `*(u64*)(ch+0x00)`, so `sg_lo:sg_hi` is the
 64-bit descriptor-table guest address (also why the read handler returns 8 bytes at offset 0x00).
- Guest-visible per-channel register set: `+0x00,+0x04,+0x08,+0x0c,+0x10,+0x14(w-only cmd),
 +0x18(r-only state)`. Internal `sg_index/sg/offset/gen/buf/buflen` are **not** guest-visible.
- `S+0x528` (`phase`) is the channel index of the in-flight chunk — the timer BH is ch2-only.
- `S+0x510/0x518/0x520/0x528/0x52c` are exactly the "phase 2" staging state (not generic chained
 DMA); the "generation" guard is `S+0x470` (ch2 gen) vs `S+0x52c`.
- `0x2ae380` (abort) and `0x2ae3f0` (stop/free) differ: only the latter clears reg0..mode/state and
 the done bit.
