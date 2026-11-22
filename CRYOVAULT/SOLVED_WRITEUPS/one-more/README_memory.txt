one-more — memory budget for the full (n=511, k=512) run
=========================================================

Exact bit-based k-tree (the only correct formulation — the mod-N interval join
misfilters because the partial sums concentrate near 0):

  W      = 266 bits   (need W > max|S| = 511 * 2^256 = 2^265 so S=0 is forced)
  ell    = 27 bits/level, a = 9 levels
  L      = 2^27 = 1.34e8 elements per list        (k = 512 lists)
  fixed  = 9*27 = 243 bits; final list ~L; ~2^4 exact solutions per run

Live lists in the DFS: 2 leaves + one result per level = ~11 lists coexist.

  uncompacted (5 x u64 = 40 B) : 11 * 1.34e8 * 40B ~ 59 GB
  word-compacted               : ~35 GB
  (ideal lower bound ~2^26.6 * 35B * 11 ~ 25 GB)

Box: 14812 MB RAM, 11502 MB swap (4G swap.img + 7.2G zram), 303 GB free disk.

=> does not fit 16 GB RAM; needs swap-file, disk-backed (mmap) lists, or a
   bigger box. Compute itself is modest (~7e10 sha256, ~20-40 min); paging is
   the bottleneck.
