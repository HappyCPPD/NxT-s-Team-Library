# Git Sleuth

**Category:** Misc 
**Flag:** `SkillBit{R3m3mb3r_t0_4lw4ys_3sc4p3_G1t_C0mm4nds}`

## Challenge

We're given a TCP service and its source code. The service drops us into a restricted shell that only runs `git` commands, with a long blocklist of characters and words. Somewhere in `/tmp` are 501 randomly-named `.txt` files: 500 contain a fake flag (`SkillBit{This_Is_A_Fake_Flag}`), and one contains the real flag copied from `/flag.txt`.

## Restrictions

The filter in `challenge.py` splits each input line by spaces and checks every token for blocked substrings:

- **Characters:** `| " ' ; $ \ # *  & ^ @ ! < > % : , ? { }` `` ` ``
- **Words:** `diff`, `grep`, `flag`, `patch`, `./`, `push`, `alias`, `remote`, `Fake`, `Flag`, `For`, `Testing`, `work`, `update-ref`, `lfs-remote`, `/dev/null`

This blocks most obvious approaches — no `grep`, no `diff`, no `*` globbing, no `:` (so `git show HEAD:file` is out), and the word `flag` kills any direct path to `/flag.txt`.

## Solution

### Step 1 — Build a git repo from the files

```
init /tmp
-C /tmp add -A
-C /tmp commit -m x
-C /tmp ls-tree -r HEAD
```

None of these tokens hit the blocklist. This initializes a repo in `/tmp`, stages all 501 files, commits them, and dumps the tree — one line per file with its blob SHA.

### Step 2 — Spot the odd hash

Locally, compute the git blob hash of the known fake flag content:

```bash
echo 'SkillBit{This_Is_A_Fake_Flag}' | git hash-object --stdin
# 937fc2f3a9653a549fe41c35f4e3102c02a3cad9
```

In the `ls-tree` output, 500 files share that hash. One file has a different hash (`35ab8c9e...`) — that's the real flag.

### Step 3 — Read the blob directly

`git show HEAD:filename` is blocked because `:` is a disallowed character. But `git cat-file -p <hash>` reads a blob by its SHA with no blocked characters:

```
-C /tmp cat-file -p 35ab8c9e8787383f759aae2db4ee654c73080548
```

This prints the flag.

## Key Takeaways

- `git cat-file -p <hash>` bypasses the `:` restriction — it reads any object by SHA without needing the `ref:path` syntax.
- `git ls-tree` exposes blob hashes, making it trivial to find the one file with unique content among hundreds of duplicates.
- The filter checks input tokens only, not output, so git's stdout is uncensored.
