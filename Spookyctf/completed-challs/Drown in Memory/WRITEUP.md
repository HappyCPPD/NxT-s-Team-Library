# Drown in Memory

**Flag:** `spooky{!NjEc70R-P0wer-u5eR}`

## Solution
1. The server API (`/v1/session`, `/v1/step`) was reversed in earlier sessions (see `work/PROTOCOL.md`).
 On stock settings (walk 2 u/s) the final leg can't be covered: "FINAL GAP EXCEEDS STOCK SUIT RANGE.
 Inspect the paired propulsion calibration."
2. Reversing `Abyss-Win64-Shipping.exe` (step builder near 0x14463DB70) shows a memory-protected
 pair `{capacity (float), guard (u32)}` keyed by the session `cookie`:
 `guard == float_bits(capacity) ^ cookie ^ 0xA731CF29`, capacity in [0.5, 3.0].
 Factory value is capacity 1.0 -> guard = cookie ^ 0x98B1CF29. Editing capacity in memory without
 fixing the guard gives "calibration inconsistent", which is why every earlier probe sent the raw
 cookie and got `calibration_ok: false`.
3. Send `capacity=3.0` with the matching guard -> `calibration_ok: true`, swim speed x3 (~6 u/s).
4. The HUD code hard-codes the submarine at UE (36000, 0, -5); positions are server*100, so the
 submarine is at server **x=360**, not 176.
5. Collect the 6 tanks (x=25,54,83,112,141,170 alternating y=+-14), then swim to (360,0,0) ->
 phase `escaped`, state carries the flag. Solver: `work/solve_calibrated.py A diag 360`.
