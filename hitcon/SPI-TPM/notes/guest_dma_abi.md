# Guest DMA/SPI register & descriptor ABI — QEMU `spi-tpm-dma`

HITCON CTF "SPI-TPM" (guest → QEMU escape). Offline reversing of the two guest
kernel modules. **This note is derived from disassembly only.**

## Provenance / method

* `spi_tpm_dma.ko` — ELF64 aarch64 relocatable, not stripped, build SHA1 `9718968d5a11ea4fcc5892606216c614fa2bbd1f`
* `spi_tpm_client.ko` — ELF64 aarch64 relocatable, not stripped, build SHA1 `5abc8d2a7d855ec31619f53abac197f861d34183`
* vermagic `7.2.9+ SMP preempt mod_unload aarch64`, GCC 16.1.0 (fictional kernel version).
* Tools: `r2 -q -e scr.color=false -c "aa; pdf @ <addr>"` and ghidra (`re-mcp` `ghidra_decompile`).
 **Pitfall:** `-e bin.relocs.apply=true` patches `bl` sites with `00000000` and makes r2 stop
 decoding mid-function. All results here were produced **without** reloc application (r2 still
 resolves `bl sym.X` names).
* The driver's own `sym.spi_tpm_dma_*` symbols are intact, which is why every field offset below
 can be tied to a specific instruction.

Guest platform devices (from the guest DT) — for orientation only:

| node | compatible | MMIO | size |
|---|---|---|---|
| spi-tpm-dma | `qemu,spi-tpm-dma` | `0x0c000000` | `0x200` |
| stm32h7-spi | `st,stm32h7-spi` | `0x0c000400` | `0x400` |
| sram | `mmio-sram` | `0x0c002000` | `0x2000` |

Channel numbering (DT `dma-names = rx, tx, rxm2m` → indices 0, 1, 2) is significant:
`prep_slave_sg` hard-codes *different* descriptor layouts per channel index, and the DT
`dmas` phandles are resolved through `of_dma_xlate_by_chan_id`
(`probe` @ `0x080004a8` → `of_dma_xlate_by_chan_id`, `0x080004ac` → `of_dma_controller_register`).

---

## 1. MMIO register map of `spi-tpm-dma`

### 1.1 Setup

`spi_tpm_dma_probe` @ `0x080002e4`:

```
0x08000300 mov x0, x21 ; &pdev->dev
0x08000308 bl devm_kmalloc ; (dev, size=0x428, gfp=0xdc0) -> driver state
0x08000320 bl platform_get_resource ; (pdev, IORESOURCE_MEM=0x200, 0)
0x0800032c bl devm_ioremap_resource
0x08000330 str x0, [x19, 0x180] ; dev->iomem = mapped spi-tpm-dma BAR
0x08000334 cmn x0, 1, lsl 12 ; IS_ERR check
0x0800035c bl platform_get_irq ; (pdev, 0) ...
0x08000360 str w0, [x19, 0x188] ; dev->irq
0x08000394 bl devm_request_threaded_irq ; handler=NULL(thr only), thread_fn=spi_tpm_dma_irq,
 ; flags=0x200000, dev_id=dev
```

So: one memory resource (index 0) is the register block, one irq, threaded-only handler.
`dma_async_device_register` (`0x08000490`) publishes it; the `DMA_SLAVE` capability bit is set
(`0x080003c0`–`0x080003c8`: atomic `orr x0, x0, 0x400` on `dev+0x48`).

### 1.2 The register accessor (= the whole ABI in one function)

`spi_tpm_dma_write(chan, reg, val)` @ `0x08000070` — **the only MMIO writer in the module**:

```
0x08000070 ldr x3, [x0, 0x68] ; x3 = chan->dma_dev (driver state)
0x08000074 ldr w0, [x0, 0xd4] ; w0 = chan->index (0,1,2)
0x08000078 lsl w0, w0, 6 ; idx * 0x40 <-- STRIDE = 0x40 per channel
0x0800007c add x1, x0, w1, uxtw ; off = idx*0x40 + reg
0x08000080 ldr x0, [x3, 0x180] ; iomem base
0x08000084 add x0, x0, x1
0x08000088 dmb oshst
0x0800008c str w2, [x0] ; writel(val, base + idx*0x40 + reg)
```

`readl(addr)` @ `0x08000058`: `ldr w0, [x0]` / `dmb oshld` — plain 32-bit MMIO load.

* **Register stride per channel: 0x40 bytes.**
* **Total channels: 3** (`probe` loop @ `0x0800043c`–`0x08000488`: `w1` = 0,1,2 stored to
 `chan+0xd4` via `str w1, [x0, 0xa4]`, loop exits on `cmp w1, 3`).
* All accesses are 32-bit, non-posted with explicit `dmb`.

### 1.3 Registers, per channel (byte offset inside the channel's 0x40 block)

| off | R/W | guest-written value | proven by |
|-----|-----|---------------------|-----------|
| `0x00` | W | **low 32 bits of the 64-bit DMA (=guest-physical) address of the SG array** | `start_next_locked` @`0x08000240`–`0x08000248`: `ldr w2,[x1,0x18]` with `x1 = desc+0x58` (⇒ `desc+0x70`) then `write(chan,0,..)` |
| `0x04` | W | **high 32 bits of the same address** (upper half of the u64 at `desc+0x70`) | `0x0800024c`–`0x08000258`: `ldr w2,[x5,0x74]` → `write(chan,4,..)` |
| `0x08` | W | **entry count** = `sg_len` (`desc+0x88`) | `0x0800025c`–`0x08000268` |
| `0x0c` | W | **total transfer length in bytes** = Σ entry lengths (`desc+0x80`) | `0x0800026c`–`0x08000278` |
| `0x10` | W | **bus-width code** ∈ {1,2,4} derived from `dma_slave_config` addr width (`desc+0x84`) | `0x0800027c`–`0x08000288`; value built at `0x08000814`–`0x08000824` |
| `0x14` | W | **command: `1` = start/kick, `2` = abort/stop** | `0x0800028c`–`0x08000298` writes literal `1`; `abort_channel` @`0x08000ad4`–`0x08000adc` writes literal `2` |
| `0x18` | **R** | channel status — read value is **discarded** by the driver | `abort_channel` @`0x08000ae0`–`0x08000af8`: address `iomem + idx*0x40 + 0x18`, `bl readl`, result unused |

Global (not channel-strided) registers:

| off | R/W | meaning | proven by |
|-----|-----|---------|-----------|
| `0x100` | R | **IRQ status bitmask**, bit *i* = channel *i* finished | `irq` @`0x0800053c`–`0x0800054c`: `ldr x0,[x22,0x180]; add x0,x0,0x100; bl readl`; then `lsl w24, w26, w21` and `tst w24, w19` for `i`=0..2 |
| `0x104` | W | **IRQ ack/clear** — writes back the OR of the bits it serviced | `irq` @`0x080005d8`–`0x080005e4`: `add x0,x0,0x104; dmb oshst; str w23,[x0]` |
| `0x108` | R | exists on the device side (some status word); **the guest driver never touches it** | inferred from the device binary only — see cross-check below |

**Footprint:** 3 × 0x40 = `0xC0` for channels, globals at `0x100`/`0x104`(`/0x108`), DT says `0x200`.
The write helper has exactly 7 call sites (6 in `start_next_locked`, 1 in `abort_channel`), so the
list above is the **complete** set of writes the guest performs.

### 1.4 Cross-check against the QEMU side (already-reversed device code)

The device keeps channel state at a `0x40` stride too, base `dev+0x448 + ch*0x40`:
`+0x448`=reg`0x00`, `+0x44c`=reg`0x04`, `+0x450`=reg`0x08`, `+0x454`=reg`0x0c`, `+0x458`=reg`0x10`,
`+0x45c`=reg`0x14`. Reg `0x14` is the *command/state* cell: `1`=armed, `2`=running, `4`/`8`=done/reset.
On write of `1` the device cross-checks **reg `0x0c` against the length the SPI side expects**
(`fcn_002ae520`: `if (*(u32*)(dev+ch*0x40+0x454) != len) fail`) and requires the SG-array pointer
cell (`+0x460`) to be non-NULL. Global device cell `+0x508` = IRQ status bitmask (read at reg
`0x100`), `+0x520` backs reg `0x108`. **Confirmed** — this is a real consistency check on the
attacker-supplied "total length" field.

---

## 2. Descriptor and scatter-gather entry format

`spi_tpm_dma_prep_slave_sg(chan, sgl, sg_len, direction, dma_flags)` @ `0x080006e0`:

```
0x0800071c mov x2, 0x90 ; size
0x08000720 mov w1, 0x2900 ; gfp
0x08000724 bl __kmalloc_cache_noprof
0x08000734 str x1,[x0,0x58] / 0x08000738 str x1,[x0,0x60] ; INIT_LIST_HEAD at desc+0x58
0x08000744 bl dma_async_tx_descriptor_init
0x08000748 str w23,[x19,4] ; desc+0x04 = flags (prep arg #5)
0x0800074c ldr w23,[x22,0xd4] ; channel index decides which layout follows
0x08000758 str x0,[x19,0x18] ; desc+0x18 = tx_submit
```

### 2.1 Descriptor (`0x90` = 144 bytes, `kmalloc`)

| off | size | field | written by |
|-----|------|-------|-----------|
| `0x00` | u32 | **cookie**, set by `tx_submit`; must be `>= 1` (IRQ does `BUG_ON` if `<1`, `0x08000598`–`0x080005a0`) and is zeroed after completion | `0x080000e0` `str w19,[x2]` |
| `0x04` | u32 | tx flags (prep arg 5 / `DMA_CTRL_*`) | `0x08000748` |
| `0x10` | ptr | `struct dma_chan *` (set by `dma_async_tx_descriptor_init`); the IRQ writes the completed cookie to **`chan+0x14`** through it | `irq` `0x080005a4`–`0x080005a8` |
| `0x18` | ptr | `tx_submit` (→ `spi_tpm_dma_tx_submit`) | `0x08000758` |
| `0x28` | ptr | completion callback | read by `irq` @`0x080005f4` |
| `0x38` | ptr | callback argument | read by `irq` @`0x080005fc` |
| `0x58` | list_head | queue node (next/prev) | `tx_submit`, `start_next_locked` (`desc = node - 0x58`, `0x08000224`) |
| `0x68` | ptr | **SG array kernel VA** | `0x080007a8` / `0x08000850` / `0x08000980` |
| `0x70` | u64 | **SG array DMA address** (`dma_map_page_attrs`, dir `DMA_TO_DEVICE`) | `0x08000a98` |
| `0x74` | u32 | upper half of the `0x70` u64 — this is what lands in reg `0x04` | implicitly `0x0800024c` |
| `0x78` | u32 | SG array size in bytes = `sg_len * 0x18` | `0x08000938` |
| `0x80` | u32 | **total transfer bytes** (Σ entry lengths) → reg `0x0c` | `0x0800080c`, `0x080008b0`, `0x080009c4` |
| `0x84` | u32 | **bus-width code** → reg `0x10` | `0x08000824`, `0x080008c8`, `0x08000814` |
| `0x88` | u32 | **entry count** (`sg_len`) → reg `0x08` | `0x08000810`, `0x080008b4`, `0x080009c8` |

`desc+0x70` is produced by `dma_map_page_attrs(dev->dev, virt_to_page(array), array & 0xfff,
array_size, 1 /*DMA_TO_DEVICE*/, 0)` (`0x08000a68`–`0x08000a98`). The SG array **must not be a
vmalloc allocation** — `is_vmalloc_addr` is called (`0x08000944`); if it is vmalloc, prep stores
`-1` in `desc+0x70` and fails (`0x0800094c`–`0x08000950`).

### 2.2 SG array entry — **0x18 (24) bytes**

```
kmalloc_array(sg_len, 0x18, gfp=0x2900) ; 0x08000798 / 0x08000840 / 0x0800096c
```

| off | size | meaning |
|-----|------|---------|
| `0x00` | u64 | **address A** — source/side-A address |
| `0x08` | u64 | **address B** — side-B address |
| `0x10` | u32 | **length** of this entry (bytes) |
| `0x14` | u32 | not written by the guest driver (padding / unused) |

Entry size and field roles independently confirmed on the device side:
`fcn_002aee50` copies an entry as `g_memdup2(array + i*0x18, 0x18)` and reads `entry+0x10` as the
length; `fcn_002af350` (engine A) reads **`entry+0x08`** as the address it transfers to;
`fcn_002af1e0` (engine B) reads **`entry+0x00`** as the address it transfers from.

Which address field each channel fills (channel index = `chan+0xd4`):

| chan | name | required `direction` arg | A (`+0x00`) | B (`+0x08`) | citation |
|------|------|--------------------------|-------------|-------------|----------|
| 0 | `rx` | `2` (`DMA_DEV_TO_MEM`) | *not written* | `sg->dma_address` (`sg+0x10`) | `0x08000860`–`0x080008a8` |
| 1 | `tx` | `1` (`DMA_MEM_TO_DEV`) | `sg->dma_address` | *not written* | `0x080007bc`–`0x08000804` |
| 2 | `rxm2m` | `2` (`DMA_DEV_TO_MEM`) | `cached_entry.B` (see §3b) | `sg->dma_address` | `0x080009d0`–`0x08000a50` |

Per-entry length is always taken from `sg->dma_length` (`sg+0x18`), and `sg_next` (`0x080001d4`)
advances the list.

**How many entries fit:** all three paths reject `sg_len > 0x100` (`0x0800078c`,
`0x08000834`, `0x08000960`: `cmp w21, 0x100; b.hi <fail>`). So **max 256 entries**, i.e. at most
`256 * 0x18 = 0x1800` bytes of SG array.

---

## 3. Register write sequences

### (a) TX transfer (guest RAM → device), channel 1

1. `prep_slave_sg(chan1, sgl, n, DMA_MEM_TO_DEV, flags)` — requires `direction == 1` and `n <= 0x100`;
 builds the array with `entry.A = sg->dma_address`, `entry.len = sg->dma_length`;
 sets `desc+0x80 = Σlen`, `desc+0x88 = n`, `desc+0x84 = f(chan->0x94 = dst_addr_width)`
 (`0x08000808`: reads the **dst** width for TX).
2. `tx_submit(desc)` @ `0x08000094` — takes `chan->0xd0` spinlock, `chan->0x10` (cookie)++,
 stores the cookie at `desc+0x00`, appends `desc+0x58` to the list at `chan+0xc0`.
3. `issue_pending(chan)` @ `0x080002a8` — spinlock, `start_next_locked(chan)`.
4. `start_next_locked` @ `0x080001fc` — pops the first descriptor, sets `chan+0x70 = desc`, then:

```
write(chan, 0x00, (u32)(desc+0x70)); ; SG array phys addr (low)
write(chan, 0x04, (u32)(desc+0x74)); ; (high)
write(chan, 0x08, (u32)(desc+0x88)); ; entry count
write(chan, 0x0c, (u32)(desc+0x80)); ; total length
write(chan, 0x10, (u32)(desc+0x84)); ; bus width code
write(chan, 0x14, 1); ; kick
```

 (instructions `0x08000240`–`0x08000298`, in that order)
5. Device performs the transfer (device reads entries at the array address in reg `0x00`).
6. IRQ: `status = readl(iomem + 0x100)`; for each set bit *i*, take `chan_i` lock, `desc = chan+0x70`,
 `chan+0x70 = NULL`, `*(chan+0x14) = desc->cookie`, `desc->cookie = 0`, `start_next_locked(chan_i)`
 to chain the next queued descriptor, unlock; finally `writel(OR(bits), iomem + 0x104)`, then call
 `desc_free(dev, desc)` and `desc->callback(desc->callback_param)` for each completed descriptor
 (`0x08000584`–`0x0800060c`).

### (b) RX with MDMA chaining, channels 0 → 2

**RX (channel 0)** — same sequence as TX but with the RX register payload:
`entry.B = sg->dma_address`, `entry.A` untouched, `direction` must be `2`, and `desc+0x84` is
derived from `chan->0x90` (the **src** addr width, `0x08000808` vs `0x080009c0`).

After building the RX array, the driver **caches it in the device-private state** (this is the
piece that makes chaining work):

```
0x080008cc cbz x4, <fail> ; x4 = RX array
0x080008e0 mov w2, 0x2800 ; gfp
0x080008e4 bl kmemdup_noprof(array, sg_len*0x18, 0x2800)
0x080008f0 bl _raw_spin_lock_irqsave(dev+0x18c) ; global cache lock
0x080008fc bl kfree(dev+0x190) ; free previous cache
0x08000904 stp x21, xzr, [dev, 0x190] ; dev+0x190 = copy, dev+0x198 = 0
0x08000910 str w0, [dev, 0x198] ; dev+0x198 = sg_len
0x08000918 str w0, [dev, 0x19c] ; dev+0x19c = Σlen
0x08000920 bl _raw_spin_unlock_irqrestore
```

**RX-M2M (channel 2)** — the second stage (device-internal SRAM → guest RAM):

```
0x08000968 f903152a mov w25, w21 ; n = sg_len
0x08000980 str x0, [x19,0x68] ; new array
0x08000988 bl _raw_spin_lock_irqsave(dev+0x18c)
0x08000990 ldr x3, [x27, 0x190] ; cached array
0x08000998 cbz x3, <fail -EINVAL> ; must exist
0x0800099c ldr w0, [x27, 0x198]
0x080009a0 cmp w21, w0 ; b.eq ... ; sg_len must equal cached sg_len
0x080009d0 add x3, x3, 8 ; start at cached entry +0x08
 per entry: cmp [x3,8] (cached len) vs [sg,0x18] ; lengths must match
0x08000a04 ldr x2, [x3], 0x18 ; x2 = cached_entry.B
0x08000a0c str x2, [arr2 + i*0x18 + 0x00] ; A = cached entry.B
0x08000a14 ldr x1, [sg, 0x10]
0x08000a1c str x1, [arr2 + i*0x18 + 0x08] ; B = new sg->dma_address
0x08000a2c str w1, [arr2 + i*0x18 + 0x10] ; len
0x08000a54 ldr w0, [x27, 0x19c] ; cmp w26, w0 ; Σlen must equal cached Σlen
```

So the channel-2 entries are `{ A = the RX channel's destination address (the staging/SRAM buffer),
B = this channel's own scatterlist address (the final guest RAM buffer), len }`.
Then the normal `0x00/0x04/0x08/0x0c/0x10/0x14=1` kick sequence runs, and `desc+0x84` comes from
`chan->0x90` (src width).

*Confirmed vs inferred:* the copy directions (A = cached `+0x08`, B = live `sg+0x10`) are
**confirmed** by instruction. The naming "SRAM staging / guest RAM" is **inferred** from the task's
device topology (device → SRAM → guest RAM) plus the device-side engine roles; the driver itself
only stores addresses.

### (c) Control / reset / IRQ-ack

| action | register traffic | citation |
|--------|------------------|----------|
| kick | `write(chan,0x14,1)` | `0x0800028c`–`0x08000298` |
| abort/stop | `write(chan,0x14,2)` then `readl(iomem + idx*0x40 + 0x18)` (value discarded) | `abort_channel` `0x08000ad4`–`0x08000af8` |
| IRQ status read | `readl(iomem + 0x100)` | `irq` `0x0800053c` |
| IRQ ack/clear | `writel(mask_of_serviced_bits, iomem + 0x104)` | `irq` `0x080005d8` |
| synchronize | `synchronize_irq(dev->irq)` — no MMIO | `0x08000174` |
| probe / remove | **no MMIO at all** (only ioremap / frees) | `probe`, `remove` |

`abort_channel` also drains both descriptor queues into a caller-supplied list: it moves
`chan+0x70` and every node of `chan+0xc0` onto that list and sets `chan+0x70 = 0`
(`0x08000afc`–`0x08000b48`). `free_chan_resources` and `terminate_all` wrap it with
`chan+0xd0` locking and then `desc_free` every drained descriptor.

**Which register carries what (the two asked about explicitly):**

* **SG array guest-physical address → reg `0x00` (low 32) + reg `0x04` (high 32).**
* **Transfer length → reg `0x0c`** ("total", Σ of entry lengths). The number of entries is
 reg `0x08`; the per-entry lengths live only in the SG array in guest RAM.

---

## 4. Attacker-controlled input surface (everything the guest can put in front of the device)

Nothing here is filtered by the device beyond the checks noted; this is the escape surface.

**Per-channel registers (write side):**

| value | control | notes |
|-------|---------|-------|
| SG array DMA address | reg `0x00`/`0x04` (u64) | guest-physical address the device will dereference and read `sg_len * 0x18` bytes from |
| entry count `sg_len` | reg `0x08` (u32) | any value; driver limits to `0x100`, device limit unknown |
| total length | reg `0x0c` (u32) | Σ lengths; **device cross-checks** it against the SPI-side length |
| bus width code | reg `0x10` (u32) | 1 / 2 / 4 derived from `dma_slave_config.src|dst_addr_width` |
| command | reg `0x14` (u32) | 1 = kick, 2 = abort |
| IRQ ack mask | reg `0x104` (u32) | driver writes back only bits it saw set |

**SG entries (device reads them from guest RAM at the address above):**

| value | control |
|-------|---------|
| `A` (`+0x00`, u64) | 64-bit address — fully guest-controlled (from `sg->dma_address`, i.e. from DMA mapping of a client-provided buffer) |
| `B` (`+0x08`, u64) | 64-bit address — fully guest-controlled |
| `len` (`+0x10`, u32) | per-entry byte count — guest-controlled; only the *sum* is cross-checked against reg `0x0c` |
| `+0x14` | never written by the driver — the device sees whatever the kmalloc'd page contains (potential stale/garbage field; **inferred**, the array is `kmalloc_array(..., 0x2900)` and `+0x14` is never stored) |

**Descriptor indirect controls:** `desc+0x00` cookie (must be ≥ 1 or the guest kernel `BUG`s in
its own IRQ path), `desc+0x04` tx flags, `desc+0x28`/`0x38` callback+arg (free-form kernel pointers
read back after the descriptor is freed).

**Length/consistency rules a driver attacker must satisfy (guest-side):**

* `sg_len <= 0x100` per descriptor.
* channel 1 requires `direction == DMA_MEM_TO_DEV`; channels 0 and 2 require `DMA_DEV_TO_MEM`.
* channel 2 additionally requires a *previously cached* channel-0 array with identical `sg_len`,
 identical per-entry lengths and identical total; otherwise `prep` returns `-EINVAL (-0x16)`.
* the SG array must not be vmalloc-backed.

---

## 5. `spi_tpm_client.ko` — userspace ioctl → SPI transfer

The client is an SPI driver (`of_match` `qemu,spi-tpm`, `spi:spi-tpm`) that also registers a misc
device; `probe` @ `0x080000d4` builds name `spi-tpm%d` (`snprintf`, `0x0800011c`), sets
`mode = 0x1b6` (0666) and `minor = 0xff` (dynamic), and calls `misc_register`.

### 5.1 ioctl entry `spi_tpm_ioctl` @ `0x080005b4`

```
0x080005c4 ldr x0, [x0, 0x18] ; file->private_data
0x080005c8 sub x0, x0, 0x20 ; container_of -> client state
0x080005b8 mov w4, 0x4301 / movk w4, 0xc018, lsl 16 ; 0xc0184301 -> genkey
0x080005e4 mov w4, 0xbcfe / movk w4, 0x3fc7, lsl 16 ; accepts cmd+0x3fc7bcfe <= 1
 ; => 0xc0384301 decrypt, 0xc0384302 encrypt
```

| cmd | handler | struct size |
|-----|---------|-------------|
| `0xc0184301` | `spi_tpm_gen_key_ioctl` | `0x18` |
| `0xc0384302` | `spi_tpm_crypt_user_ioctl` (encrypt) | `0x38` |
| `0xc0384301` | `spi_tpm_crypt_user_ioctl` (decrypt) | `0x38` |

### 5.2 Userspace request structs (from the ioctl decompilations)

`genkey` — `0x18` bytes copied in, `0x18` copied back; `memchr_inv(buf+8, 0, 0x10)` must be zero
(`0x080002e4`); response payload (≤4 bytes) is written into the caller's buffer.

`crypt` — `0x38` bytes copied in **and out** (`0x080003a0`/`0x080003f4`; `memchr_inv(buf+0x28,0,0x10)`
must be zero, `0x080003c0`):

| off | field | checks (`spi_tpm_crypt_user_ioctl`) |
|-----|-------|--------------------------------------|
| `0x00` | `u32 key` | encrypt: must be != 0 (`0x08000454`) |
| `0x04` | `u32 cost` | encrypt: must be != 0 (`0x0800045c`) |
| `0x08` | `u32 inlen` | `1 <= inlen <= 0x1000`; encrypt additionally `inlen <= 0xfd8` (`0x08000464`); decrypt `inlen >= 0x28` (`0x08000498`) |
| `0x0c` | `u32 reslen` (out) | byte count actually produced |
| `0x10` | `u32 outlen` | `<= 0x1000` (`0x0800042c`) |
| `0x14` | `u32 status` (out) | ioctl return code |
| `0x18` | `u64 inptr` | must be non-NULL (`0x08000434`) |
| `0x20` | `u64 outptr` | must be non-NULL (`0x0800043c`) |
| `0x28` | `u64 z0` | must be 0 |
| `0x30` | `u64 z1` | must be 0 |

Input is copied to kernel memory with `memdup_user(inptr, inlen)` (`0x08000480`).

### 5.3 Buffers — allocation, size, maximum transfer

`spi_tpm_buffer_transfer(client, bufdesc)` @ `0x08000848`:

```
0x08000858 mov x0, 0x2004
0x08000864 mov w1, 0xdc0 ; GFP_KERNEL
0x08000868 bl __kmalloc_large_noprof ; TX buffer
0x08000874 mov x0, 0x2004
0x08000878 bl __kmalloc_large_noprof ; RX buffer
0x080008a0 bl spi_tpm_run_transaction(base, bufdesc, tx, rx, 0x2004)
0x080008b0/0x080008b8 kfree(rx); kfree(tx)
```

* **Two `kmalloc` (large) buffers of `0x2004` = 8196 bytes each**, allocated and freed **per ioctl**
 (`__kmalloc_large_noprof` — the "kmalloc" buffer flavour, also advertised by the
 `_dev_info` string *"cryptographic accelerator ready (%s buffers)"* with `%s = "kmalloc"`,
 rodata `0x08000cf2`).
* **Maximum transfer: `0x2004` bytes, full duplex, fixed** — the length is not derived from the
 user request; `outlen`/`inlen` only bound the payload inside it.

`spi_tpm_run_transaction` @ `0x08000608` (ghidra-verified):

1. zero the stack `spi_transfer` (`memset(...,0,0x74)`), set `tx_buf`/`rx_buf` to the two buffers,
 `len = 0x2004`, `bits_per_word = 8` (`0x0800065c`), `speed_hz = 0x2faf080 = 50000000` (50 MHz,
 `0x08000660`–`0x0800066c`).
2. `memset(tx, 0xff, 0x2004)`; `memset(rx, 0, 0x2004)` (`0x0800070c`, `0x0800071c`).
3. build the request packet in the TX buffer:

```
+0x00 u8 0xa5 magic
+0x01 u8 op 1 = genkey, 2 = encrypt, 3 = decrypt
+0x02 u16 inlen payload length (from bufdesc+0x18)
+0x04 u32 key (bufdesc+0x04)
+0x08 u32 cost (bufdesc+0x08)
+0x0c u32 0x2004 total SPI length
+0x10 ... payload memcpy from bufdesc+0x10, bufdesc+0x18 bytes
```
 (`0x08000720`–`0x08000758`)
4. `mutex_lock(client+8)`; `spi_sync(...)`; `mutex_unlock` (`0x08000760`–`0x08000778`) — i.e. the
 whole path is `spi_sync` (the DMA engine is reached through the SPI controller, not directly).
5. parse the response at RX offset `inlen + 0x10`:

```
+0x00 u8 must be 0xa5 else -EILSEQ (`0x08000780`, `0x08000788`)
+0x01 u8 status: 0x00/0xe0 = OK, 0xe1/0xe2/0xe5 = -EPROTO,
 0xe3 = -EOVERFLOW, 0xe4 = -ENOMSG, 0xe6 = -ENOENT, else -EIO
+0x02 u16 response length
+0x08 ... response data -> memcpy(bufdesc+0x20, ..., len)
```
 (`0x0800078c`–`0x08000814`); the response length is stored back into `bufdesc+0x2a`, and in the
 crypt path written to the caller's `reslen` (`0x08000524`–`0x08000528`) and copied out to
 `outptr` (`0x08000564`).
6. For decrypt, the expected response length is read out of the *input payload* at `+0x10`
 (`0x080004b4`: `ldr w19,[x0,0x10]`) and must be `<= 0xfd8` and `<= outlen`.

### 5.4 Client-side internal offsets (for cross-referencing)

`file->private_data - 0x20` = client state; `+0x00` dev, `+0x08` mutex, `+0x20` `struct miscdevice`,
`+0x48` device ptr, `+0x68` mode, `+0x70` name buffer (`0x20` bytes).

### 5.5 DMA-engine side helper offsets (spi_tpm_dma.ko), for reference

`struct dma_chan` is `0xd8` bytes; three of them at `dev+0x1a0 + i*0xd8`
(`probe` loop `0x0800043c`–`0x08000488`, `dev` total `0x428`).

| chan off | meaning | citation |
|----------|---------|---------|
| `0x10` / `0x14` | cookie / completed-cookie (both init to 1) | `0x08000454`, `tx_status`, `irq` |
| `0x68` | parent `dma_device` | `0x08000070` |
| `0x70` | descriptor currently running (`NULL` when idle) | `0x080001fc` |
| `0x78` | `struct dma_slave_config` copy, `0x48` bytes | `config` `0x08000144` |
| `0x90` / `0x94` | **`dma_slave_config.src_addr_width` / `.dst_addr_width`** (used for reg `0x10`) | `0x08000808`, `0x080009c0` |
| `0xc0` | pending-descriptor list head | `0x0800020c` |
| `0xd0` | spinlock | `0x080000b8` |
| `0xd4` | channel index 0/1/2 | `0x08000074` |

`dma_device` state: `+0x180` iomem base, `+0x188` irq, `+0x18c` global spinlock, `+0x190` cached RX
SG array, `+0x198` cached sg_len, `+0x19c` cached total.

---

## Confirmed vs inferred — summary

**Confirmed by instruction** (offsets, values, access order): register stride `0x40`, 3 channels,
all register offsets and the value written to each; the `0x00/0x04/0x08/0x0c/0x10/0x14=1` kick
sequence; register `0x14 = 2` abort plus `0x18` read; `0x100` read / `0x104` ack; descriptor size
`0x90` and every field offset listed; SG entry size `0x18` with `A@0x00`, `B@0x08`, `len@0x10`;
`sg_len <= 0x100`; per-channel address-field assignment; the RX array caching at `dev+0x190`;
the channel-2 validation against the cache; the `0x2004`-byte kmalloc buffers and the SPI packet
layout; all userspace struct sizes, field offsets and bounds.

**Inferred (flagged):** the *names* of register semantics (e.g. that `0x14` is "start/abort" and
`0x18` is "status" — the guest discards `0x18`, so its content could not be read from the guest
side); that address `A` is the SRAM/staging side and `B` the guest-RAM side; the existence of reg
`0x108` (device side only, no guest reference); that SG entry `+0x14` is unused padding (the guest
never writes it; its device-visible content is unconstrained); the meaning of `desc+0x04` (tx
flags) and `desc+0x20` (written by `dma_async_tx_descriptor_init`, not used by this driver);
allocation flag constants (`0x2900`, `0x2800`, `0xdc0`) are quoted literally, not decoded to
`GFP_*` names.
