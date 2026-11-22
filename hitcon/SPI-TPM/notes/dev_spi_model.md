# SPI-TPM — QEMU device model + bounds verdict

Target: stripped x86-64 `qemu-system-aarch64` (PIE). All addresses below are **ELF vaddrs**
(= "r2 vaddr"); ghidra addr = vaddr + 0x100000.
Sources used: `objdump` of the whole binary (`/var/tmp/spitpm/full.asm`), the pre-dumped
`/var/tmp/spitpm/dev.txt` (0x2ae000–0x2b1e00), ghidra pseudocode (cached project), the
rodata/data tables read directly from the file, and the firmware
`libspi_tpm_firmware.so` decompile (`spitpm/fw_decomp.c`, loaded at base
0x100000 in that decompile).

Legend: **[C]** = confirmed by instruction/disassembly, **[I]** = inferred (naming/semantics
only, the offset+instruction is confirmed).

---

## 0. Device inventory / TypeInfos

| Device | source file (string) | desc string | MMIO |
|---|---|---|---|
| `stm32h7-spi` | `hw/ssi/stm32h7_spi.c` | "Minimal STM32H7 SPI controller" | sysbus region **0x400** @ DT 0x0c000400 |
| `spi-tpm-sram` | `hw/ssi/spi_tpm_sram.c` | "MMIO SRAM pool for spi-stm32 RX DMA/MDMA chaining" | sysbus RAM region, size property |
| `spi-tpm-dma` | `hw/ssi/spi_tpm_dma.c` | "Simple DMA backend for the spi-tpm testbed" | sysbus region **0x200** |
| `spi-tpm` | `hw/ssi/spi_tpm.c` | "Programmable SPI firmware peripheral" | **none** — SSI peripheral on the SPI controller's SSI bus |

Key function map (vaddr):
- stm32h7-spi: realize **0x2b0090** [C], class_init **0x2afcc0** [C], unrealize 0x2b01f0 [C],
 MMIO **write 0x2b0fd0**, **read 0x2b05c0**, start-transfer **0x2b0c10**,
 SR compute **0x2afad0**, flush/reset **0x2b02e0**, finish **0x2b03f0**,
 PIO emit (fill RX) **0x2afd40**, schedule-RX-only **0x2aff50**, delay callback **0x2b0850**,
 vmstate/state validator **0x2b04c0**, trace printf **0x2afb70**, SSI broadcast **0x2ae2e0**.
- spi-tpm-sram: instance_init 0x2af9e0 [C], realize **0x2af8d0** [C], class_init 0x2af870 [C].
- spi-tpm: realize **0x2b12f0** [C], class_init 0x2b15b0 [C], instance/reset 0x2b1670 [C],
 **SSI transfer 0x2b16e0** [C], unrealize 0x2b1750 [C], "load/restore" **0x2b17f0** [C],
 "dump/run-tx" **0x2b18c0** [C].
- spi-tpm-dma: realize **0x2aeb70** [C], MMIO **read 0x2ae9f0 / write 0x2ae5b0** [C],
 channel reset 0x2ae380 [C], channel teardown 0x2ae3f0 [C], state check 0x2ae520 [C],
 desc→host copy **0x2af1e0** (mem→dev), host→desc copy **0x2af350** (dev→mem),
 chunk writer 0x2ae f... (0x2aee50/0x2af000) [C].

---

## 1. `stm32h7-spi` — MMIO register model

### 1.1 realize (0x2b0090) [C]
```
FUN_003df110(state+0x330, owner, ops=0x9b6d40, state, "stm32h7-spi", 0x400) // memory_region_init_io
sysbus_init_mmio(sysbus, state+0x330) // 0x400-byte MMIO region
sysbus_init_irq (sysbus, state+0x440) // qemu_irq at +0x440
state+0x448 = qdev_get_child_bus(DEVICE, "ssi") // the SSI bus (0x2ae2e0 uses it)
*(u64*)(state+0x478) = 0x20016e3600 // 24 MHz default clock at +0x478 (0x016e3600), +0x47c default small
state+0x404a8 = timer_new(cb=0x2b0850, state) // delayed/RX-batch timer
```
The MemoryRegionOps struct is at vaddr **0x9b6d40**: `{ .read = 0x2b05c0, .write = 0x2b0fd0, ...,
impl.max_access_size = 4 }` (0x9b6d68 = 0x400000001 → min 1 / max 4) [C]. A read/write is
therefore at most 4 bytes (`param_4`/`param_3` ≤ 4).

Props (table at 0x9f35c0, 0x20-byte records) [C]: `dma-backend` → **state+0x450**, type
`spi-tpm-dma`; `sram-backend` → **state+0x458**, type `spi-tpm-sram`; plus `clock_hz`
(class prop) and `fifo-size` (+0x47c).
**Notable:** state+0x450 is *used* (start-transfer calls the DMA helper with it), but
**state+0x458 (`sram-backend`) is never read** by any stm32h7-spi code [C — grep of
0x2ae000–0x2b2000 shows every +0x458 access there belongs to `armv7m_systick`, not the SPI
device]. The property is effectively dead. This matters for §3/§5.

### 1.2 write handler 0x2b0fd0 (`fn(state, offset, value, size)`) [C]
| off | action |
|---|---|
| 0x00 | CR1 → +0x460. bit0=SPE, bit9=0x200 (start). If SPE is being cleared (old bit0 set, new bit0 clear): log `"disable-spe …"` and call flush 0x2b02e0. If the new value has (bit0 & bit9) set → chain into **start-transfer 0x2b0c10**. |
| 0x04 | +0x464 (CR2) — **low 16 bits are the transfer length** read by start-transfer |
| 0x08 | +0x468 (CFG2) — bits 0xc000 select the DMA path in start-transfer |
| 0x0c | +0x46c (CFG1) — `(val & 0x60000) == 0x40000` selects an "async/queued" mode |
| 0x10 | +0x470 (IER) — then recompute SR and drive the IRQ |
| 0x18 | +0x474 (ISR) `& = ~val` — write-1-to-clear of status bits |
| 0x20 | **TXDR**: push `size` bytes of `value` into the TX FIFO |
| other | `"%s: unsupported write at 0x%lx\n"` |

TX FIFO push (0x2b1030–0x2b10a3) [C]:
```
uVar4 = tx_count = *(u32*)(state+0x40484);
uVar2 = fifo_size = *(u32*)(state+0x47c); if (0xffff < fifo_size) fifo_size = 0xffff; // clamp
puVar7 = state + 0x488 + tx_count;
do { if (fifo_size <= tx_count) break; // stop at fifo_size
 tx_count++; * (state+0x40484)=tx_count; *puVar7++ = value >> (8*i);
} while (tx_count != size_prev + tx_count); // exactly `size` bytes
```
→ index range `[0, min(fifo_size,0xffff))`, buffer is 0xFFFF bytes at +0x488.

### 1.3 read handler 0x2b05c0 (`fn(state, offset, size)`) [C]
| off | returns |
|---|---|
| 0x00 | +0x460 (CR1) |
| 0x04 | +0x464 |
| 0x08 | +0x468 |
| 0x0c | +0x46c |
| 0x10 | +0x470 (IER) |
| 0x14 | **SR = FUN(0x2afad0)** (computed, not a stored reg) |
| 0x30 | **RXDR**: pop `size` bytes from the RX FIFO |
| other | `"unsupported read"` |

RX FIFO pop (0x2b06xx) [C]:
```
limit = *(u32*)(state+0x40488); // rx fill level
pos = *(u32*)(state+0x4048c);
pbVar5 = (byte*)(state + 0x10487 + pos);
do { if (limit <= pos) goto drained;
 if (0xfffe < pos) goto end;
 pos++; byte = *pbVar5++; ...
} while (pos != pos_start+size);
```
→ index `[0,min(limit,0xfffe)]`, buffer 0xFFFF bytes at +0x10487.

### 1.4 Four 0xFFFF-byte FIFOs (contiguous) [C]
| base | role |
|---|---|
| +0x488 | TX FIFO (SPI host→device staging) |
| +0x10487 | RX FIFO (device→host staging) |
| +0x20486 | staging buffer for the DMA "mem→dev" channel |
| +0x30485 | staging buffer for the DMA "dev→mem" channel |

Other state: counts/pointers at `+0x40484 (tx_count)`, `+0x40488 (rx_count/fill)`,
`+0x4048c (rx_pos)`, `+0x40490 (total)`, `+0x40494 (resp_pos/emit pos)`,
`+0x40498 (dma flag)`, `+0x40499 (pending flag)`, `+0x4049a..0x4049f (mode/prefix bytes)`,
`+0x404a0 (debug flag)`, `+0x404a8 (QEMU timer)`; qemu_irq +0x440; SSI bus +0x448;
dma-backend +0x450; sram-backend +0x458.

### 1.5 SR compute 0x2afad0 [C]
```
SR = *(u32*)(state+0x474); // sticky ISR bits
fill= min(*(u32*)(state+0x40488), 0xffff); pos = min(fill, *(u32*)(state+0x4048c));
avail = fill - pos;
if ((*(u32*)(state+0x46c) & 0x60000) != 0x40000) // non-async mode
 if (*(u32*)(state+0x40484) < min(fifo_size,0xffff)) SR |= 2; // TXP: room in TX FIFO
if (avail) SR |= 1 | (min(avail,3) << 13) | (avail>3 ? 0x8000 : 0); // RXP + FRLVL + FTLVL/EOT
```
IRQ assertion everywhere is `irq = (SR & IER & 0xb) || ((IER & 4) && (SR&3)==3)` [C].

### 1.6 start-transfer 0x2b0c10 [C]
`len = *(u16*)(state+0x464)` (≤ 0xFFFF). Three branches:
1. `dma_backend(+0x450)==0 || (CFG2(+0x468) & 0xc000)==0`:
 - if `(CFG1+0x46c & 0x60000)==0x40000` → *async* bookkeeping: sets pending, total=len,
 schedules timer (0x2aff50) — no bytes moved here.
 - else **PIO**: pad TX FIFO with 0xff to `len`, then
 `for i<min(len,16): resp=ssi_broadcast(bus, TXFIFO[i]); RXFIFO[i]=resp;`
 `for i in [16,len): resp=ssi_broadcast(bus, TXFIFO[i]); RXFIFO[i]=resp;`
 then rx_count=len, finish 0x2b03f0.
2. DMA path (`CFG2 & 0xc000`): if bit15 set → `dma_read_from_guest(0x2af1e0, len, +0x20486)`
 then broadcast loop over +0x20486 → +0x30485, then `dma_write_to_guest(0x2af350, len, +0x30485)`.
 Otherwise fill +0x20486 with 0xff, broadcast into +0x30485, then dma_write_to_guest.

### 1.7 finish / flush / delayed paths [C]
- finish 0x2b03f0: logs, zeroes counts, clamps `rx_count = min(rx_count,0xffff)`, sets
 EOT(8), clears start bit, asserts IRQ.
- flush 0x2b02e0: kills the timer if any, zeroes counts/ISR, deasserts IRQ.
- 0x2aff50: computes a delay from `clock_hz(+0x478)`/CFG and arms the timer.
- **0x2b0850 (timer cb)**: picks (TX,RX) staging per the dma flag, **re-validates**
 `1 ≤ fifo_size ≤ 0xffef && tx_count ≤ fifo_size && rx_count ≤ 0xffff && rx_pos ≤ rx_count &&
 total ≤ 0xffff && resp_pos ≤ total`, else `"%s: invalid delayed transfer state"` + flush;
 then fills RX FIFO `[0, min(fifo_size,total)-resp_pos)` and broadcasts staging
 `[resp_pos,total)`.
- **0x2b04c0**: a state validator with the *same* invariants, error
 `"%s: rejecting invalid migration state"`, returns -EINVAL. [I: this is the
 `vmstate_pre/post_load` hook for stm32h7-spi.]

---

## 2. Data movement for one SPI transfer

Guest side (from the device tree / client `.ko`): the guest writes the command bytes into the
**SRAM pool** at 0x0c002000, programs a **spi-tpm-dma channel** with a descriptor ring, then
drives the SPI registers.

1. Guest fills the SRAM via normal memory writes / its DMA module.
2. Guest programs DMA ch1: write desc-base (64-bit, +0x448/+0x44c), count (+0x450,
 1..0x100), total (+0x454), then trigger (+0x45c bit0). The DMA handler
 `address_space_read(memory, desc_base, .., host_buf, count*0x18)` pulls the descriptor
 ring out of guest memory, validates `each desc.len != 0` and `Σdesc.len (+2) == total`,
 else resets the channel [C].
3. Guest writes SPI `CR2(+0x464) = len`, `CFG2(+0x468)` DMA bits, then `CR1(+0x460)`
 with SPE|start. That chains into start-transfer 0x2b0c10.
4. **mem→dev**: `0x2af1e0(dma_backend, len, state+0x20486)` walks ch1's descriptors and
 `address_space_read(desc.addr, min(desc.len, remaining))` into the SPI staging buffer,
 total ≤ `len` (≤0xFFFF) [C].
5. The bytes are pushed one at a time through the SSI bus:
 `ssi_broadcast(bus, byte)` = 0x2ae2e0 → for each slave, call its `ssi-peripheral`
 class method (`*(class+0xd8)(slave, byte)`) and OR the results; the returned byte is
 stored into the RX staging buffer [C].
6. **`spi-tpm` transfer 0x2b16e0** is that method: `ret = fw_vtable[+0x30](fw_handle, byte)`
 — i.e. every byte handed to the firmware's per-byte entry point (fw `0x3040`) [C].
7. Response bytes come back the same way and land in the RX staging buffer
 (+0x10487 or +0x30485), then **dev→mem** `0x2af350(dma_backend, len, +0x30485)` copies
 `len` bytes back to guest memory (`address_space_write` to ch2 descriptors)
 — or, in the async path, chunk-by-chunk through the timer/0x2aee50/0x2af000 chain [C].
8. Guest reads the RX FIFO via SPI `RXDR` (+0x30 read) [C].

**Roles of the pointers**
- `dma-backend` (state+0x450): a pointer to the `spi-tpm-dma` device state. It is the object
 whose descriptor ring/state the SPI controller drives (0x2af1e0 / 0x2af350 / 0x2af7d0 /
 timer bookkeeping). It is a *link<device>* — no host memory pointer leaks through it.
- `sram-backend` (state+0x458): declared, typed `spi-tpm-sram`, **never dereferenced** by
 the SPI code [C]. The SRAM is reached only *implicitly*, as ordinary RAM in the machine
 address space, because the guest programs DMA descriptors that point at 0x0c0020xx.

---

## 3. `spi-tpm-sram`

### Is it a plain RAM region? — **YES [C]**
realize 0x2af8d0:
```
size = *(u32*)(state+0x440);
if (size == 0) { error_setg(errp, "spi-tpm-sram requires size > 0"); return; }
memory_region_init_ram(state+0x330, owner=obj, "spi-tpm-sram", size, errp); // 0x2e4890
if (*errp) return;
sysbus_init_mmio(sys_bus_device(obj), state+0x330);
```
`memory_region_init_ram` has **no read/write ops** — it is pure backing store. The
`size` property (desc string `"MMIO SRAM pool for spi-stm32 RX DMA/MDMA chaining"`,
`instance_init 0x2af9e0` sets `state+0x440 = 0x2000`) is a *machine/DTS* property, not
guest-writable.

### How does the DMA/SPI code get a host pointer to it? — **It doesn't [C].**
There is **no `memory_region_get_ram_ptr` / `qemu_map_ram_ptr` / `address_space_map` of the
SRAM anywhere in the three drivers**, and the `sram-backend` property is dead (§1.1). The
only way data enters/leaves the SRAM is:

`address_space_rw(address_space_memory, guest_addr, MemTxAttrs{0x100000000}, host_buf, len, is_write)`
via **0x3ebd70** (a wrapper around `address_space_read`/`address_space_write`), called from:
- 0x2ae5b0 (DMA MMIO start) — reads the descriptor ring,
- 0x2af1e0 — desc → staging,
- 0x2af350 / 0x2af000 — staging → desc.

Because the target is the *machine address space*, an access to 0x0c002000 is dispatched to
the SRAM's RAM MemoryRegion and **bounds-checked by QEMU's memory core**. A descriptor whose
`addr`/`len` runs past the 0x2000 window is *not* an overflow of the SRAM backing store: the
access simply continues into whatever region is mapped next (or the unassigned region) — it
never becomes host-adjacent memory. There is therefore **no guest → `sram_backing + offset`
host-pointer arithmetic to over-run**.

### Length/offset checks applied to SRAM-derived values
Nothing is applied *to the SRAM* (it is never addressed by host pointer). What *is* checked
on the guest-supplied DMA descriptor data (all [C]):
- `count` (reg +0x450): accepted only if `count - 1 < 0x100` → 1..0x100; host ring buffer is
 `g_malloc0_n(count, 0x18)`; ring read length `count*0x18` ≤ 0x1800.
- per-descriptor `len` must be ≠ 0 and `Σ len (+2) == total(+0x454)`, else the channel is
 torn down (0x2ae380) — a descriptor set that doesn't add up never gets used.
- all desc→staging and staging→desc copies are clamped to the *SPI transfer length*
 (`len = u16 from +0x464`, ≤ 0xFFFF), i.e. `min(desc.len, remaining)`.
- the async writer (0x2aee50/0x2af000) clamps chunk size to `axi-write-burst-bytes`
 (+0x50c, default 0x400) and guards `consumed + chunk ≤ total`.

---

## 4. `spi-tpm` device

### realize 0x2b12f0 [C]
`firmware-path` prop at state+0xa8 → `g_module_open`; `g_module_symbol("spi_tpm_fw_get_api_v1")`;
`api = spi_tpm_fw_get_api_v1(1)` ; `state+0xb0 = module`, `state+0xb8 = api` (vtable),
`state+0xc0 = instance handle`. ABI validation: `api[0]==1`, `api[1] > 0x57` (size ≥ 0x58),
non-null at api+0x18,0x20,0x28,0x30,0x38,0x40,0x48. Then
`api[0x18](cfg{len=0x20}, &state+0xc0)` = create-instance.

Firmware API table (from `libspi_tpm_firmware.so`, `.data.rel.ro` @0x5d20) [C]:
| off | fn | meaning |
|---|---|---|
| +0x00 | – | version = 1 |
| +0x04 | – | size = 0x58 |
| +0x18 | 0x1d50 | create_instance |
| +0x20 | 0x1a40 | destroy_instance (wipes 0x24b0, free) |
| +0x28 | 0x2350 | load/validate state (from 0x24b0 blob) |
| +0x30 | **0x3040** | **per-byte transfer** (called by QEMU 0x2b16e0) |
| +0x38 | **0x1a00** | **get_length** → `mov $0x24b8,%eax; ret` — **constant 0x24b8** |
| +0x40 | **0x1a70** | **process/dump**: requires `len > 0x24b7`, sets `*outlen=0x24b8`, writes magic `"WFRC"`(0x043524657)+0x24b0 bytes |
| +0x48 | 0x23c0 | **restore**: requires `len==0x24b8`, magic `0x43524657`+ver 5, then `malloc(0x24b0)`+`memcpy` and validate/load |

### run-tx 0x2b18c0 (= `spi_tpm` dump) [C]
```
if (!fw_vtable || !handle) return -1;
memset(state+0xc8, 0, 0x4000); // frame buffer, exactly 0x4000 bytes
*(u32*)(state+0x40c8) = 0; // frame_len
L = fw_vtable[+0x38](handle); // == 0x24b8 (constant)
if (L-1 <= 0x3fff) { // accept only 1..0x4000
 r = fw_vtable[+0x40](handle, state+0xc8, L, &outlen);
 if (r == 0 && outlen == L) { *(u32*)(state+0x40c8) = L; return 0; }
 memset(state+0xc8, 0, 0x4000); // wipe on failure
}
return -1;
```
- The frame is `state+0xc8 .. state+0x40c8` (0x4000 bytes); `state+0x40c8` is the length
 word, immediately after — no overlap.
- `0x2b17f0` (load/restore, also in the same class vtable) requires
 `state+0x40c8 == fw_vtable[+0x38](handle)` then calls `fw_vtable[+0x48]` (restore) with
 the frame, then wipes the frame.

### Can the guest make the length exceed 0x4000? — **NO [C].**
`fw_vtable[+0x38]` is literally `mov $0x24b8,%eax; ret`, i.e. it returns a compile-time
constant — the guest cannot influence it. Even if it returned something else, QEMU rejects
everything outside `[1,0x4000]` and wipes the frame. `fw_vtable[+0x40]` writes exactly
`outlen = 0x24b8` bytes into the 0x4000 frame. So the 0x4000 frame buffer **cannot be
overflowed through run-tx**.

### What the guest *can* influence
The per-byte transfer (QEMU 0x2b16e0 → fw 0x3040) writes the incoming byte into the firmware
state at `state + *(u32*)(state+0x2420)` (fw), gated by `pos ≤ 0xf` for that branch (i.e. the
first 16 bytes are the *command header*); further bytes go through the ring at `state+0x1010`
(bounded by the validated fields 0x2428/0x242c/0x2430). So the guest controls a **0x24b0-byte
"state blob"** that the restore path (fw 0x23c0 → 0x2350) later parses. That parse *is*
validated (0x2424∈[0x10,0x2004], 0x2420≤0x2424, 0x2428∈[0x10,0x1010], 0x242c≥0x2428,
0x2430≤0x1008, 0x2424-0x242c≥0x2430, 0x2434≤0x2004) — see §5.

---

## 5. Bounds verdict — every access into a fixed-size buffer

| # | buffer | size | access | index/length source | bounded? |
|---|---|---|---|---|---|
| 1 | TX FIFO +0x488 | 0xFFFF | write @+0x488+tx_count (write reg 0x20) | tx_count, clamped to `min(fifo_size,0xffff)`; loop breaks *before* write when `fifo_size <= tx_count` | **SAFE [C]** |
| 2 | RX FIFO +0x10487 | 0xFFFF | read @+0x10487+rx_pos (read reg 0x30) | rx_pos, capped by `min(rx_count,0xfffe)` with `rx_count ≤ 0xffff` | **SAFE [C]** |
| 3 | TX/RX FIFO | 0xFFFF | PIO transfer 0x2b0c10 | `len = u16(+0x464)` ≤ 0xFFFF; pad-memset guarded by `tx_count < len` and `tx_count ≥ min(len,16)` | **SAFE [C]** |
| 4 | RX FIFO +0x10487 | 0xFFFF | emit-pio-chunk 0x2afd40 | start `prefix<<4` (`prefix` = +0x4049f, only ever written 0), chunk clamped to `0xffff - start` | **SAFE [C]** |
| 5 | RX FIFO +0x10487 | 0xFFFF | delay cb 0x2b0850 "emit-rx-only" | writes `[0, min(fifo_size,total)-resp_pos)`; `total ≤ 0xffff`, `fifo_size ≤ 0xffef` (validated 2 lines above) | **SAFE [C]** |
| 6 | staging +0x20486 / +0x30485 | 0xFFFF each | DMA mem↔dev 0x2af1e0 / 0x2af350 | copy total = `len` ≤ 0xFFFF | **SAFE [C]** |
| 7 | DMA ring buf (heap) | `count*0x18` | 0x2ae5b0 start | `count ∈ [1,0x100]` enforced (`count-1 < 0x100`); `g_malloc0_n(count,0x18)` | **SAFE [C]** |
| 8 | DMA staging chunk buf +0x4f8 / +0x520 | heap `g_memdup2(_, total)` | 0x2ae e50/0x2af000 | chunk clamped to `axi-write-burst-bytes` and guarded `consumed+chunk ≤ total` | **SAFE [C]** |
| 9 | **SRAM pool 0x0c002000** | size (0x2000) | guest DMA desc addrs | reached only through `address_space_rw(machine AS)` → QEMU memory core bounds it; **no host pointer is ever taken** | **SAFE [C]** (no host OOB possible this way) |
| 10 | spi-tpm frame +0xc8 | 0x4000 | run-tx 0x2b18c0 (fw dump) | `len = fw constant 0x24b8`; QEMU gates `1 ≤ len ≤ 0x4000`; requires `outlen == len` | **SAFE [C]** |
| 11 | fw command header `state[0..0xf]` | 16 B | fw transfer 0x3040 | `pos = *(u32*)(fw+0x2420)`, branch taken only when `pos ≤ 0xf` | **SAFE [C]** |
| 12 | fw response ring `state+0x1010` | 0x1008 | fw 0x1b20 builds `param_3 + 8` | `param_3` is a **u16**; buffer is 0x1008 → `param_3 ≤ 0xFFF8` needed | **NOT PROVEN — candidate [I]** |
| 13 | fw state blob fields 0x2420/0x2424/0x2428/0x242c/0x2430/0x2434 | – | fw restore 0x23c0 → 0x2350 | each field individually range-checked AND cross-checked (0x2420≤0x2424, 0x2428≤0x2424, 0x2428≤0x242c, 0x2424-0x242c≥0x2430) | **SAFE per the checks I read [C]; the *uses* downstream of 0x2434 were not exhaustively traced → residual [I]** |

### Ranked candidate violations (with exact guest triggers)

**1. — Firmware-side response builder (fw 0x1b20), the only unproven arithmetic.**
`FUN_00101b20(state, byte, u16)`: `*(u32*)(state+0x2430) = param_3 + 8;`
`*(u32*)(state+0x2424) = ...param_3+8...;` then a response frame is built into the
`0x1008`-byte ring `state+0x1010` with the length field `*(u16*)(state+0x1012) = param_3`.
If `param_3` (a 16-bit value that appears to come from the per-byte command header the guest
controls) can exceed `0xFFF8`, the response build overruns the 0x1008 ring. Reachability of a
large `param_3` was **not** established here.
*Live experiment:* drive the SSI with a crafted 16-byte header whose length field is large
(e.g. header `a5 <op> <len=0xffff>` at the first bytes written to fw state[0..0xf]), then
complete CS and read back; watch for an ASAN/heap-corruption in QEMU or a bogus response
length in the frame at `state+0x1010`.

**2. — Nothing actionable found in the three QEMU devices.** All twelve QEMU-side fixed-buffer
accesses (#1–#11) are provably bounded, and the code even carries *two* explicit state
validators ("rejecting invalid migration state" 0x2b04c0, "invalid delayed transfer state"
0x2b0850). If the intended guest→host escape is in the QEMU device, it is not in the
FIFO/staging/frame arithmetic; the remaining unexamined surfaces are:
- the `MemTxAttrs` value `0x100000000` handed to `address_space_rw` at every DMA copy
 (worth confirming it is `MEMTXATTRS_UNSPECIFIED` and not something that bypasses checks),
- the timer/async path race between 0x2b0850, 0x2aff50 and CR1 writes (re-entrancy),
- the `axi-write-burst-bytes` (+0x50c) clamping inside 0x2aee50/0x2af000 (I read guards, but
 not every branch).
*Live experiment:* replay with `-d unimp,guest_errors` and a guest driver that (a) writes
`CR1` mid-transfer while the 0x2b0850 timer is pending, and (b) sets `fifo-size` on the
command line to its extremes (1 and 0xffff) to exercise the clamps.

**3. — SRAM pool: no violation.** Confirmed the region is plain RAM, is never taken as a
host pointer, and the `sram-backend` property is dead code. A guest cannot turn an
out-of-range SRAM DMA into a host OOB.

### Things I could not finish (honest gaps)
- Exact field names/semantics of the DMA channel struct (stride 0x40, base 0x440; offsets
 +0x18 desc-ptr, +0x1c state, +0x20 counter, +0x28, +0x2c, +0x30 buf, +0x38 len) are **[I]**.
 The MMIO view of channel *c* is at `+0x448 + c*0x40` (8-byte desc addr split across
 +0x448/+0x44c, count +0x450, total +0x454, +0x458, trigger +0x45c).
- Whether `spi-tpm` 0x2b17f0/0x2b18c0 are reached via a custom QOM interface or via the
 SSI transfer/set_cs was not fully resolved (they sit in a data table at 0x9b6e40/0x9b6e48/
 0x9b6e58 that I did not find a direct code xref to). The *semantics* (dump vs.
 restore-then-wipe) are confirmed from the code.
- The firmware's command dispatch (fw FUN_001025e0 region) and the true source of `param_3`
 into 0x1b20 were not traced to the guest — this is the one open item (candidate #1).
