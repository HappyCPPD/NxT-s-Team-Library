# RESULT — DLSS (AI/ML, 200 pts) slug=dlss

STATUS: SOLVED (two candidate flags — one is the genuine artifact, one a forgery decoy)

FLAG (try first): d4rk{yare.yare.daze}
FLAG (alt): d4rk{hinjaku!hinjaku!}

## MECHANISM
1. Unzip museum_simulation.dist.zip. The game ships 8 encrypted canvases frame_0N.png.enc
 + model.pt (a 4x "DLSS" decoder). Passphrase recovered from museum_obby.bin: `unga-bunga-ved-in`.
 Decrypting gives 8x 128x128 RGB canvases (dlss_frame_01..08.png) — prior work.
2. model.pt is a U-Net (checkpoint dict: size=128, base_channels=16; keys enc1..enc4, bottleneck,
 up4..up1/dec4..dec1, head -> 1 channel). CRITICAL: conv layers have bias=False (BN follows);
 rebuilding with bias=True gives noise. Exact module in dlss_solve.py loads with
 missing=[]/unexpected=[].
3. Run each canvas through the net -> 1-channel logit map; threshold at mean -> binary image;
 upscale 4x. Frames 05 and 06 render clean QR CODES; frames 01-04,07,08 are forgery noise
 ("not every piece is worth what it's hanging for").
4. "never show anyone the negative" -> the QRs decode only when INVERTED (negative). cv2
 QRCodeDetector on the inverted binaries:
 frame_05 (white frame) -> d4rk{yare.yare.daze}
 frame_06 (gold frame) -> d4rk{hinjaku!hinjaku!}

Both are valid d4rk{...} QR payloads; the museum theme implies one genuine + one forgery.
Submit yare.yare.daze first (white/"genuine" frame; Jotaro catchphrase), hinjaku as fallback.

## ARTIFACTS
- dlss_solve.py (exact U-Net + inference), dlss_bin_05.png/06.png (the two QRs),
 dlss_bin_montage.png (all 8), dlss_out_*/dlss_neg_* renders.
