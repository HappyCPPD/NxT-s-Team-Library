# Cleithrophobia

**Category:** forensics | **Flag:** `Spooky{Be0m_Me_Up_Sc0tty_2266}` (capital S)

## Approach
The pcap carried base64 in HTTP headers. Decoding produced the flag. The real casing is capital-S `Spooky{...}` — submit that first; lowercase only if rejected.

## Reproduction
```bash
tshark -r Cleithrophobia.pcap -Y http -T fields -e http.request.full_uri | grep -oE '[A-Za-z0-9+/=]{20,}' | while read b; do echo "$b" | base64 -d 2>/dev/null; done
```
Output: `Spooky{Be0m_Me_Up_Sc0tty_2266}`
