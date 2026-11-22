# Beginner guide: Socket-Malfunction and Owner Of The Footprints

This is written for someone who has never done a CTF before. Every command is
written out in full. Type it, press Enter, look at what comes back. If your output
does not match mine, stop and re-read the step.

Two words you will see everywhere:

- **Flag**: the secret string you are hunting for. It looks like
 `SkillBit{something}`. Finding it means you solved the challenge.
- **Terminal**: the black window where you type commands. On Linux it is usually
 called Terminal, Konsole or GNOME Terminal.

You will need Python 3 and a tool called `tshark`. To check:

```bash
python3 --version
tshark -v
```

If `tshark` says "command not found", install Wireshark (tshark comes with it):
`sudo apt install tshark`

---

# Part 1: Socket-Malfunction

**The story:** someone recorded network traffic between a door controller and the
app that operates it. The controller's replies are readable. The app's own
messages look like garbage. One of those messages holds a password. Get it.

## Step 1: Unzip the challenge

```bash
cd ~/Downloads/ctfs/MetaCTFs/MetaCTFs2026Nov/Socket-Malfunction
unzip -o socket-malfunction.zip -d extracted
ls -R extracted
```

You now have one file: `control-socket.pcap`.

A **pcap** is a recording of network packets, like a video file but for traffic
between two computers. You open it with tshark or Wireshark and read what was sent.

## Step 2: Copy it somewhere easy and look at it

```bash
cp extracted/socket-malfunction/control-socket.pcap /tmp/sm.pcap
tshark -r /tmp/sm.pcap
```

You should see 13 lines, talking between port `51788` and port `47821`. A "port"
is just a numbered door on a computer.

(Tip: on some machines tshark refuses files inside your home folder with
"You don't have permission to read the file". That is why we copied to `/tmp`. If
you hit it, copy the file to `/tmp` and use that path.)

## Step 3: Ask tshark to decode the messages

Right now tshark only shows "TCP packet, 40 bytes". It does not know those bytes
are chat messages. Tell it the traffic on port 47821 is WebSocket:

```bash
tshark -r /tmp/sm.pcap -d tcp.port==47821,websocket -Y websocket -T fields -e websocket.payload
```

Now you get lines like:

```
7b226576223a2268656c6c6f222c226677223a22322e342e31222c...
7b22636d64223a22737562736372696265222c22746f70696322...
```

Those are the messages, but written in **hex**. Hex is a way of writing bytes
using only 0-9 and a-f, so a computer can print any byte safely. `7b` is the
character `{`, `22` is `"`, and so on. It is not encrypted, just written down
differently.

## Step 4: Turn the hex back into text

Add one more tool on the end, `xxd -r -p`, which reverses hex back into real
characters:

```bash
tshark -r /tmp/sm.pcap -d tcp.port==47821,websocket -Y websocket -T fields -e websocket.payload | xxd -r -p
```

Readable output:

```
{"ev":"hello","fw":"2.4.1","dev":"bay-door-ctl"}{"cmd":"subscribe","topic":"door"}{"ev":"state","door":"closed","lock":"engaged"}{"cmd":"auth","key":"SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}"}{"ev":"auth","result":"ok","scope":"operator"}{"cmd":"release"}{"ev":"state","door":"open","lock":"released"}{"ev":"bye"}
```

There it is, in the `"auth"` message, after `"key"`:

```
SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}
```

## Step 5: Why this worked

WebSocket is a chat protocol. The rules say the **client** (the app) must
scramble every message it sends, and the **server** (the door) must not. That
scrambling is called **masking**. The app flips every byte using a 4-byte key,
and it puts that key right there in the packet header so the other side can undo
it. Because the key travels with the message, anyone holding the recording can
unscramble it. It was never meant to hide anything from someone reading the
traffic.

Why did the server's replies look readable? Because the server is not allowed to
mask. Only the app masks. That difference is your clue.

**Flag: `SkillBit{m4sk1ng_1s_n0t_3ncrypt10n}`**

---

# Part 2: Owner Of The Footprints

**The story:** an attacker broke into a company and moved from one computer to
another. We have copies of the logs from the two jump servers. We need the
**account name** that made the jump. There are hundreds of accounts on each
machine, and the attacker deleted most of the logs.

A "jump server" is a computer people log into first, then hop to other machines
from. "Lateral movement" means the attacker going sideways from machine to machine.

## Step 1: Unzip the challenge

```bash
cd ~/Downloads/ctfs/MetaCTFs/MetaCTFs2026Nov/Owner\ Of\ The\ Footprints
unzip -o owner-of-the-footprints.full.zip -d extracted
cd extracted/owner-of-the-footprints
unzip -o 2025-03-11T082527_JUMP-SCV-01.zip -d 2025-03-11T082527_JUMP-SCV-01
unzip -o 2025-03-11T090100_JUMP-SCV-02.zip -d 2025-03-11T090100_JUMP-SCV-02
ls
```

(The `-d <folder>` part matters. Each zip has its files loose at the top with no
folder around them, so without it the two servers would dump their files on top
of each other.)

You now have two folders, one per machine:

```
2025-03-11T082527_JUMP-SCV-01 <- first jump server
2025-03-11T090100_JUMP-SCV-02 <- second jump server
```

Inside each are Windows files. The ones we care about are the logs, which live
under:

```
C/Windows/System32/winevt/logs/
```

Those `.evtx` files are Windows event logs. Windows writes thousands of them.
We only want one kind.

## Step 2: Install the tool that reads .evtx files

```bash
pip install python-evtx
```

## Step 3: Look at the RDP login log on the second server

When someone logs into a Windows machine **over the network**, Windows records
it in a log called `Microsoft-Windows-TerminalServices-LocalSessionManager`.
The useful part is a field called `Address`: a login from another computer shows
an IP address there, a login made while sitting at the machine says `LOCAL`.

Save this as `read_logins.py`:

```python
import re
import Evtx.Evtx as evtx

F = ("2025-03-11T090100_JUMP-SCV-02/C/Windows/System32/winevt/logs/"
 "Microsoft-Windows-TerminalServices-LocalSessionManager%4Operational.evtx")

with evtx.Evtx(F) as log:
 for record in log.records:
 x = record.xml
 if "<Address>" not in x: # skip events that have no address field
 continue
 time = re.search(r'SystemTime="([^"]+)"', x).group(1)
 user = re.search(r'<User>([^<]*)</User>', x).group(1)
 addr = re.search(r'<Address>([^<]*)</Address>', x).group(1)
 print(f"{time[:19]} {user} from={addr}")
```

Run it:

```bash
python3 read_logins.py
```

## Step 4: Find the one line that came from the network

You get a long list. Almost every line ends with `from=LOCAL`, meaning the
person was sitting at that computer. Scroll through and look for the lines that
end with a real number instead:

```
2025-03-11 04:36:24 JUMP-SCV-02\Th3y_w0n7_sUrV1v3_35 from=LOCAL
2025-03-11 07:34:50 JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 from=192.168.91.159
2025-03-11 07:34:51 JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 from=192.168.91.159
2025-03-11 07:38:04 JUMP-SCV-02\Th3y_w0n7_sUrV1v3_34 from=192.168.91.159
2025-03-11 07:42:03 JUMP-SCV-02\Th3y_w0n7_sUrV1v3_08 from=LOCAL
```

That is the whole trick. Hundreds of `LOCAL` logins are noise. Only one account
appears with an IP address next to it. That account logged into this machine
over the network, which is exactly what "lateral movement" looks like.

The account name is the part after the backslash:

```
Th3y_w0n7_sUrV1v3_34
```

**Flag: `SkillBit{Th3y_w0n7_sUrV1v3_34}`**

## Step 5: Why this worked

The attacker cleared the normal Security log to cover their tracks, which is why
the obvious place has nothing useful in it. But clearing logs with the usual
command only clears the old, classic logs. The newer "operational" logs are left
alone. The RDP session log is one of those, so it survived.

Those small numbers in the list are Windows event numbers, and they mean
different things:

- `21` = a session logged on
- `22` = a session was reconnected
- `24` = a session disconnected

You do not need to memorise them. For this challenge, the only thing that
matters is which lines have an IP address instead of `LOCAL`.

The same idea works generally: when someone says "logs were deleted", go looking
in the logs the cleanup command forgot.

---

# Quick summary

Socket-Malfunction: open the pcap, tell tshark the traffic is WebSocket, unstuff
the hex. The client's masking key is stored in the packet, so the password falls
straight out.

Owner Of The Footprints: read the RDP login log on the second server, and the
single login that came from an IP address instead of `LOCAL` is your answer.
