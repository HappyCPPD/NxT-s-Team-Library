# Webbed hands

Flag (accepted): `d4rk{m3rma1ds_ar3_r3al}`

My first read of the prefix was `h4ck{`, which was rejected. The body was right;
the prefix is `d4rk{` (144 064 162 153 173). The two misreads were the first
character (a long-held pose I took as `5 0` is `4 4`, with the open hand being
the leading `0` of `064`) and the third (`162` r, not `143` c). The decode
table below shows the corrected prefix.

## What the video is

Two mirrored hands with thumbs always touching hold a sequence of about 65 poses,
roughly 2 s each. The audio is a decoy ("heed not their song").

## Encoding

Octal ASCII, three poses per character. Each pose is one octal digit (3 bits).
The giveaway is the rhythm: the same pose (inner fingers bent into a "V", rest
spread) leads almost every group of three, which is the leading `1` of
lowercase letters (141-172). Groups led by the fully open pose are digits
(`06x`).

Pose to digit, as read from the video:

| digit | pose |
|-------|------|
| 0 | hands open, only thumbs touching |
| 1 | inner "V" only, other fingers spread |
| 2 | (only inferred, appears in `r` = 162) |
| 3 | V plus one more pair at the tip, big single gap |
| 4 | fingertips closed, one gap, no V |
| 5 | V plus closed tip (two gaps) |
| 6 | two straight chevrons, hands wide |
| 7 | single straight chevron, three fingers free |

Anchors that fixed the mapping: `V ? 3` three times then `{` (173), `_` (137)
twice, `}` (175) at the end, and `06x` digit groups.

## Decode

```
144 064 162 153 173 d4rk{
155 063 162 155 141 061 144 163 m3rma1ds
137 _
141 162 063 ar3
137 _
162 063 141 154 r3al
175 }
```

## Confidence

Read by eye from 360p frames (higher resolutions returned 403). The `5` vs `6`
and `2` vs `3` poses are hard to tell apart, so `r`, `s` and `l` were settled
by the word fitting ("mermaids are real" matches the siren/webbed-hands hint)
rather than by the pose alone. The prefix was the part I got wrong: I assumed
`h4ck{` from the CTF name instead of reading it strictly from the poses.
