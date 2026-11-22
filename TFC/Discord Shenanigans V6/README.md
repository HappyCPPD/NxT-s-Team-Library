# Discord Shenanigans V6

## Challenge information

- **Category:** Misc
- **Difficulty:** Baby
- **Points:** 340
- **Author:** hofill

## Description

> You already know. We don't want this challenge to be guessy. Wrap the hidden word in `TFCCTF{}`. It's in `#announcements`.

The relevant announcement was:

> Less than half a day until TFC CTF 2026. 
> Come prepared for a day of challenges, exploits, puzzles, and flags. 
> Assemble your teams, sharpen your tools, and make sure everything is ready before the clock starts. 
> Stay focused, think creatively, and expect the unexpected. 
> The competition will be intense, so every minute and every flag will matter. 
> Let the hacking, debugging, reversing, and suffering begin. 
> Everyone, good luck and see you on the scoreboard.

## Solution

The announcement is written so that the first letter of every sentence forms an acrostic:

```text
Less -> L
Come -> C
Assemble -> A
Stay -> S
The -> T
Let -> L
Everyone -> E
```

Reading those letters from top to bottom gives:

```text
LCASTLE
```

This is almost a word, but it contains an extra `L` at the beginning. The first sentence starts with **“Less than”**, which acts as the instruction to make the result “less” the leading `L`:

```text
LCASTLE - L = CASTLE
```

The hidden word is therefore `CASTLE`.

## Flag

```text
TFCCTF{CASTLE}
```
