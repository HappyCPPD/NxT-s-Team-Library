# Peering Eyes — forensics / memory forensics (hard) — SOLVED

Flag: spooky{th3y_ar3_w2tch1ng}

## Method
1. LiME dump of a Kali box (sha256 cc89dd1b...b664e, 1.073 GB). Symbols = vmlinux-7.1.5+kali-amd64 ISF.
2. Spyware = /home/kali/EYEsee.py (PID 28906, python3 EYEsee.py under zsh).
 String table @0x227e32d4 / 0x227e32f8 contains the Python literal "spooky{th3y_ar3_"
 (i.e. the first half of the flag), plus cv2 / imshow "eye see you" / pyautogui.screenshot /
 screenshots/latest_screenshot_%Y%m%d_%H%M%S.png constants.
3. The webcam frames (4 intact 640x480 JPEGs carved from RAM) show a person holding a paper note:
 the note reads "w2tch1ng}" — the left half of the note is hidden behind the hand.
4. Note suffix + script prefix => spooky{th3y_ar3_w2tch1ng}

Artifacts: /var/tmp/spooky2/peering/{webcam_56224832.jpg, frame4_notezoom.png, tail_zoom.png}
