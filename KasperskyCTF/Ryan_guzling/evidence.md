# Ryan_guzling forensic evidence log

All analysis is local and read-only with respect to the supplied ZIP and disk-image artifacts. Times below use Asia/Singapore unless a tool reports otherwise.

## Initial inventory

- Working directory: `<path>
- Supplied archive: `guz_5d74556b5147018c.zip` (11,684,370,291 bytes)
- Free space at start: 419 GiB on the workspace filesystem; sufficient for the ~34.1 GB extraction and reconstruction workspace.
- Relevant tools initially present: 7-Zip, unzip/zipinfo, util-linux disk tools, Sleuth Kit (`mmls`, `fls`, `icat`, `tsk_recover`), `qemu-img`, and byte/string utilities.

## Archive preservation and metadata

- SHA-256: `556f7e5a9d5c04ad10167c13a3d45ac7f770c81d4ddcfe67cc3d86f6ccb2e2a8`
- ZIP structure: single-part Zip64 archive, 3 entries, no archive/file comments, entries not ZIP-encrypted.
- `hdd.dd`: 19,327,352,832 bytes; deflated to 635,266,258 bytes; CRC-32 `aa3bc786`; DOS last-modified `2025-05-08 16:49:36`.
- `ssd.dd`: 16,106,127,360 bytes; deflated to 11,048,339,952 bytes; CRC-32 `85f09b0a`; DOS last-modified `2025-05-08 16:45:02`.
- `trash.dd`: 536,870,912 bytes; deflated to 763,523 bytes; CRC-32 `7c54ebe2`; DOS last-modified `2025-05-08 16:40:10`.
- The DOS times are recorded only as ZIP entry metadata, not treated as image acquisition/creation times.
- Full `7z t -bb1` decompression test completed successfully for all three entries (`Everything is Ok`), validating their stored CRCs before extraction.

## Extracted-image integrity

- Extraction completed with 7-Zip reporting `Everything is Ok`.
- `hdd.dd` SHA-256: `8eea40e3663d6df4fbacedae26256602a7fba0bc89e393e25fb47d46d3eb227e`
- `ssd.dd` SHA-256: `f2a2d3b2763347ac41ed162547d535e4718376632d6825adce3febc980121b63`
- `trash.dd` SHA-256: `48f28dfa775ad710d761d4996f556f2c27f7846313f9181f56aa12db050245de`

## On-disk layout and member correlation

The supplied handoff proposed Microsoft Storage Spaces. The actual GPT type GUIDs and data signatures falsify that hypothesis:

- `hdd.dd`: GPT disk UUID `1F4F98C1-C677-4FD0-AA2A-E43F49CD57AB`; partition 2 starts at LBA 409640, size 36,069,520 sectors, type `53746F72-6167-11AA-AA11-00306543ECAC` (Apple CoreStorage), partition UUID `B8FA354B-ED37-4764-983F-49186BA47B10`.
- `ssd.dd`: GPT disk UUID `35243F31-3D70-4567-A8EB-DE5140D86016`; partition 2 starts at LBA 409640, size 30,785,456 sectors, same Apple CoreStorage type, partition UUID `F89F5171-FD4E-42D1-AE27-6424B8AF2C84`.
- Both CoreStorage partitions have a valid `CS` metadata header at absolute byte offset 209,735,680.
- The common LVG UUID embedded in both headers is `3186F1C4-ED4D-4D74-B9EE-36EBF630E52A`, LVG name `fusion`.
- SSD physical-volume UUID: `CAAC2A72-E9FE-4EC6-8923-698738D40F6B`.
- HDD physical-volume UUID: `89837067-A081-47C7-9D47-DE5DB0EF13B7`.
- The metadata in both members lists those PV UUIDs in SSD-then-HDD order. `fvdeinfo -o 209735680 ssd.dd hdd.dd` reconstructs the two-member set successfully; the reverse order fails its member-identifier check.
- Reconstructed logical volume UUID: `134725CA-BA45-4EBA-B981-BB4360EA7FDF`, name `FusionDrive`, size 34,124,726,272 bytes. It is FileVault-locked using AES-XTS 128-bit.
- `trash.dd` is not a third CoreStorage member. Its only partition starts at LBA 40, size 1,048,496 sectors, GPT type `48465300-0000-11AA-AA11-00306543ECAC` (Apple HFS/HFS+), and contains an HFS+ journaled volume header at partition-relative offset 1024 bytes (`H+`, `HFSJ`).
