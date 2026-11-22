Name: orphan
Description: Help, our flag has been orphaned! Can you find him?
Flag: CTF{please_sir_can_i_have_a_flag}
## 🧩 Challenge Info
**Name:** orphan 
**Category:** Forensics 
**Description:** Help, our flag has been orphaned! Can you find him? 
**Flag format:** CTF{...}

---

## 🔍 Initial Analysis

First, I checked the file type to understand what kind of data I was dealing with:

```bash
file orphan.bin
```

Output:
```
orphan.bin: XZ compressed data, checksum CRC64
```

So the file is compressed using **XZ compression**.

---

## 🔎 Verifying File Signature

To confirm this, I looked at the first few bytes:

```bash
xxd -l 16 orphan.bin
```

Output:
```
00000000: fd37 7a58 5a00 0004 e6d6 b446 04c0 8fe2 .7zXZ......F....
```

The magic bytes `fd 37 7a 58 5a` correspond to **XZ format**, confirming the result from `file`.

---

## 📦 Extracting the Archive

Next, I extracted the compressed file:

```bash
7z x orphan.bin
```

This gave me a new file named:

```
orphan
```

---

## 🧠 Identifying Filesystem

I checked the type of the extracted file:

```bash
file orphan
```

Output:
```
orphan: Linux rev 1.0 ext2 filesystem data, UUID=549aa1a4-8327-4d4b-af70-c3c0805e45e1 (large files)
```

### 📝 Explanation (Beginner Friendly)

This means:
- The file is a **Linux ext2 filesystem image**
- It behaves like a **mini disk**
- Files exist inside it, but we can’t access them with normal `ls`
- We need forensic tools to explore it

---

## 🔎 Searching for Clues

I used `strings` to quickly scan for readable text:

```bash
strings orphan | grep flag
```

Output:
```
flag.png
```

This tells me:
- There is likely a file named **flag.png**
- But it might not be accessible normally (possibly deleted or orphaned)

---

## 🧬 Investigating Filesystem (Sleuth Kit)

To explore the filesystem, I used `fls`:

```bash
fls -r -d orphan
```

Output:
```
r/- * 0: a
r/r * 13(realloc): flag.png
r/- * 0: b
-/r * 14: $OrphanFiles/OrphanFile-14
```

### 📝 Explanation

- `fls` lists files inside a filesystem image
- `-r` = recursive (search everything)
- `-d` = include deleted/orphaned files

#### Breaking down the important line:

```
r/r * 13(realloc): flag.png
```

- `13` → inode number
- `(realloc)` → file was deleted but reallocated (orphaned)
- `flag.png` → this is our target file

👉 This confirms that **flag.png exists but is not linked normally** (orphaned file)

---

## 🧲 Extracting the File

Now that I have the inode number (13), I used `icat` to extract it:

```bash
icat orphan 13 > flag.png
```

### 📝 Explanation

- `icat` extracts file content using inode number
- `orphan` = filesystem image
- `13` = inode
- `> flag.png` = save output as PNG file

---

## 🖼️ Viewing the Flag

Finally, I opened the image:

```bash
xdg-open flag.png
```

Inside the image, I found the flag:

```
CTF{please_sir_can_i_have_a_flag}
```

---

## ✅ Final Flag

```
CTF{please_sir_can_i_have_a_flag}
```

---

## 🧠 Key Takeaways

- Not all files are visible via normal tools
- Deleted/orphaned files can still exist in filesystem images
- Sleuth Kit tools (`fls`, `icat`) are essential for forensics
- Always check:
 - compression
 - file signatures
 - filesystem type
