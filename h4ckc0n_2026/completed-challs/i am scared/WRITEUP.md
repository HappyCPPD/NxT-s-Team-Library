# i am scared

Crypto (misc), h4ckc0n 2026, author pr4njal

Flag: `d4rk{SCpS_Ar3_sCary_0r_th3y_JuST_w4nna_l1ve?}`

## The challenge

The description is three lines of emoji and a note:

```
. . ⬇️
. . ⚪
. ↗️↖️

note - <cant_find_letters> are just an underscore or { or }
```

`scary.txt` is 46 lines, each either `number[number]` or the literal `<cant_find_letter>`:

```
839[6]
479[8]
317[1]
275[5]
<cant_find_letter>
937[8]
...
```

## Working out the encoding

The emoji are a picture. Three arrows pointing inward at a circle is the SCP Foundation logo, and the title "i am scared" fits.

That makes the first number an SCP designation. Every one is under 1000, so they all sit in Series I. `173` showing up in the list (the original SCP) was a nice confirmation.

The bracketed number is an index into something attached to that SCP. The obvious candidate is the title on the wiki's series list. Two entries have index 0, which says the indexing is 0-based:

- `370[0]` is "A Key", giving `A`
- `443[0]` is "Thought-streaming Crayons", giving `T`

The first four lines then give `d4rk`, which is the flag prefix, so the guess holds:

| Line | Title | Char |
| --- | --- | --- |
| `839[6]` | Candied Worms | `d` |
| `479[8]` | Hallway 4, D-Class Dorms, Site 14 | `4` |
| `317[1]` | Cretaceous Physicist | `r` |
| `275[5]` | Ironskin | `k` |

## Solve

Titles come from https://scp-wiki.wikidot.com/scp-series, where each entry is `<li><a href="/scp-NNN">SCP-NNN</a> - Title</li>`. Strip inner tags (173 has a `<strong>` in it), unescape HTML entities, and index.

```bash
curl -sL -A "Mozilla/5.0" https://scp-wiki.wikidot.com/scp-series -o s1.html
```

```python
import re, sys, html

page = open(sys.argv[1], encoding="utf8").read
titles = {}
for m in re.finditer(r"<li><a[^>]*>SCP-(\d+)</a> - (.*?)</li>", page):
 titles[int(m.group(1))] = html.unescape(re.sub(r"<[^>]+>", "", m.group(2)))

out = ""
for line in open(sys.argv[2]).read.split:
 m = re.match(r"(\d+)\[(\d+)\]", line)
 out += titles[int(m.group(1))][int(m.group(2))] if m else "_"
print(out)
```

```bash
python3 solve.py s1.html scary.txt
```

Output:

```
d4rk_SCpS_Ar3_sCary_0r_th3y_JuST_w4nna_l1ve?_
```

Per the note, each `<cant_find_letter>` is `_`, `{` or `}`. The first one follows the `d4rk` prefix so it is `{`, the last one closes the flag, and the rest are underscores.

## Notes

- The mixed case (`SCpS`, `sCary`, `JuST`) is real. The author could only use characters that exist in a title at some index, so case is whatever the titles happened to offer. Don't normalise it.
- Read the page as UTF-8 and unescape entities before indexing. Titles like `Schrödinger's Can Opener` and `Dragon-Snails™` have non-ASCII characters, and a byte-wise read shifts the offsets.
- The solve depends on the live wiki. Titles get edited, so a rename would break a character. It matched as of 2026-11-15.
