---
title: "Glass Vault"
ctf: "platypwnies 2026"
date: 2026-11-14
category: misc
difficulty: medium
points: n/a
flag_format: "PP{...}"
author: "author"
---

# Glass Vault

## Summary

A Veloren v0.18.0 MMO instance (`Esedge`) hides the loot — and the flags — behind an NPC-gated
chain and a floating glass vault. The intended solve is the tip's literal reading: **modify your
client**. We built a headless, scriptable client from the shipped v0.18.0 source, then (a) read a
server-side localization argument the real UI hides to win rock-paper-scissors, (b) logged in under
the account name the Teller actually checks, and (c) teleported (client-authoritative physics) into
the vault to loot it. Three flags, no GUI.

The single biggest trap: **the character was dead**, which silently swallows every
use/collect action while leaving dialogue working. That is what made the previous attempts look
like a broken protocol.

## Solution

### Step 1: Build a scripted client, not a GUI

Get v0.18.0 (GitLab release or `git clone --depth 1 --branch v0.18.0`), add a small workspace member
that drives `veloren_client::Client` directly, and expose a `pub fn force_physics` next to
`send_chat` in `client/src/lib.rs` (the existing senders are private). Commands are read from a FIFO
each tick; two upstream build fixes are needed: change the x86_64 rustflags from `-fuse-ld=mold` to
`-fuse-ld=lld` and symlink `rust-lld` as `ld.lld`.

```bash
cd ~/tools/veloren-0.18 && export PATH=$HOME/bin:$PATH
CARGO_BUILD_JOBS=6 cargo build --profile no_overflow -p tools
VELOREN_ASSETS=.../veloren_bin/assets ./target/no_overflow/chat \
 --server <host>:<port> --user <acct> --pass x --type game --char <name> --vd 6 --in /tmp/nv_in
```

### Step 2: FLAG 1 — win RPS by reading an argument the UI hides

`talk <bram_uid>` (ControlEvent::Interact → NpcInteractEvent → AgentEvent::Talk) starts the game.
Each question arrives as `Content::Localized { key: "dialogue-game-rock_paper_scissors",
args: { "throw": Content::Plain("<his move>") } }` — the vanilla UI renders only the throw text and
hides the arg. Read `args["throw"]`, reply with the counter-move `Response` on the same
`DialogueId`/`tag`. Twenty wins later Bram reveals the flag.

```
PP{7h3_cl13n7_kn0w5_7h3_4n5w3r::DxX5xUFOmMwt}
```

### Step 3: FLAG 2 — the Teller checks the ACCOUNT alias, not the character name

Bram names the Treasurer (`Uncle_Scrooge_McDuck`). Renaming the character does nothing; the Teller
compares `comp::Player.alias`. Reconnect with `--user Uncle_Scrooge_McDuck` (auth_provider is None,
so the account auto-registers with that alias) and the Teller hands over the flag plus
`common.items.keys.glass_key`.

```
PP{4_k3y_70_rul3_7h3m_4ll::to9v7LNZ7cuO}
```

### Step 4: FLAG 3 — the vault (this is the real bug that cost two sessions)

**Root cause: the player was dead.** `Health` read `0/100 is_dead=true` and the log held
`CHAT Kill(FallDamage, Uid(us))`. A dead player is skipped by `character_behavior`, so
`ControlAction::InventoryAction(Collect)` never becomes an `Interact` state and the client emits
*nothing* — no `FailedSpriteUnlock`, no outcome. Dialogue (`ControlEvent`) has no health gate, which
is exactly why talk worked and collect never did. A dead player's `PlayerPhysics` is also ignored, so
every earlier teleport was a server-side no-op and the "position held perfectly" readback was a
local-only illusion.

Fix: add `respawn` (`Client::respawn` → `ControlEvent::Respawn`) plus an auto-respawn guard in the
tick loop. Then, with the player alive, the server validates physics again
(`server/src/sys/msg/in_game.rs`): ≤ ~20-block steps at zero velocity, and at least one z in
`[pos.z, pos.z+height]` must be a **fluid** block. `GlassBarrier`/`GlassKeyhole` are
`Block::air(sprite)` ⇒ `is_fluid == true`, so only **Rock** blocks movement.

```bash
# climb in open air, cross above the island, drop onto the ledge, then open the door
goto 5872 5136 700
goto 5875 5041 700
goto 5875 5041 653
collect 5875 5039 652 # consumes glass_key, destroys all 96 GlassBarrier
# stand next to each chest and collect; MAX_PICKUP_RANGE = 5.0 over an air-only A*
```

Server output on looting the vault (both a chat line and a dialogue `Statement`):

```
CHAT CommandInfo :: Plain("You found the Treasurer's Number One Dime. PP{...}")
DIALOGUE Uid(4117) Statement { msg: Plain("The Number One Dime gleams on its pedestal, the
 Treasurer's first coin ever earned. Scratched into its rim: PP{...}"), given_item: None }
```

## Flag

```
PP{7h3_cl13n7_kn0w5_7h3_4n5w3r::DxX5xUFOmMwt}
PP{4_k3y_70_rul3_7h3m_4ll::to9v7LNZ7cuO}
PP{7h3_7r345ur3r5_7r345ur3::kuxPFK-uyquP}
```

## Notes

- Chest loot (not flags): Mjolnir, Golden Cheese, Wings of Winter, Belzeshrub the Broom God,
 Laevateinn, Crown, Coins ×5000, Sagitta. The Dime is the only flag in the vault.
- Instance-specific: the `::` suffix of each flag is per-instance, so re-derive them on a fresh
 instance; the mechanics above are stable.
- Client command set used: `goto/tp` (stepped teleport), `pos/inv/ents/scanat` (recon),
 `talk/ack/resp/ans/auto` (dialogue), `collect` (use/unlock), `hp/respawn` (vitals).
