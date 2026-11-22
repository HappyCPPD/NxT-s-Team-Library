; =============================================================================
; hemglass.asm — "Hemglass" glassbilsjingel
;
; Spelar en kort melodi med ett MOS 6581 SID-chip kopplat till Z80:s I/O-buss.
; Röst 1 används, pulsvåg med 50% duty cycle, inget filter.
;
; Bygg med SjASMPlus:
;   sjasmplus --raw=hemglass.bin hemglass.asm
;
; Minneskarta:
;   $0000  RST $00 / kallstart — hårdvaruinit, sedan hopp till main
;   $0038  RST $38 / maskerbar avbrottshanterare — startar melodiuppspelning
;   $0066  NMI-hanterare — hoppar in vid sista notens gate-off
;   $0080  Melodi: 16 noter på SID Röst 1
;   $0280  Tystnad: nollar alla Röst 1-register
;   $0290  Main: uppstartsfördröjning, stack/avbrottsinit, HALT
; =============================================================================

; -----------------------------------------------------------------------------
; SID 6581 registeroffset (mappade direkt till Z80:s I/O-portnummer)
; -----------------------------------------------------------------------------
SID_V1_FREQ_LO  EQU  $00    ; Röst 1 frekvens, låg byte
SID_V1_FREQ_HI  EQU  $01    ; Röst 1 frekvens, hög byte
SID_V1_PW_LO    EQU  $02    ; Röst 1 pulsbredd, låg byte
SID_V1_PW_HI    EQU  $03    ; Röst 1 pulsbredd, hög byte
SID_V1_CTRL     EQU  $04    ; Röst 1 kontrollregister
SID_V1_AD       EQU  $05    ; Röst 1 Attack / Decay
SID_V1_SR       EQU  $06    ; Röst 1 Sustain / Release  (används ej)
SID_VOL         EQU  $18    ; Filterläge / huvudvolym

; Kontrollregistervärden — bit 6 = PULSE, bit 0 = GATE
; Bitmönster: 7=NOISE, 6=PULSE, 5=SAW, 4=TRI, 3=TEST, 2=RING, 1=SYNC, 0=GATE
GATE_ON         EQU  $41    ; %01000001 — pulsvåg, gate PÅ
GATE_OFF        EQU  $40    ; %01000000 — pulsvåg, gate AV (release)

; -----------------------------------------------------------------------------
; Envelope:  Attack/Decay = $29
;   Attack  nibble $2 -> ~6 ms
;   Decay   nibble $9 -> ~240 ms
; Volym:    $0F = max, inget filter
; -----------------------------------------------------------------------------
ATTACK_DECAY    EQU  $29
MASTER_VOL      EQU  $0F

; -----------------------------------------------------------------------------
; Notfrekvensregister (16-bit)
;   SID-frekvensreg = (not_hz x 2^24) / fclk,  fclk = 1 000 000 Hz
;
;   Registren är hämtade från en NTSC C64-frekvenstabell (fclk = 1022727 Hz).
;   Noterna D4-C5 matchar tabellen exakt (0 cent avvikelse vid NTSC).
;   Vid enhetens 1 MHz-klocka spelar alla noter ~39 cent för lågt.
;   D5 ($2578) avviker från tabellens D5 ($25A3): 584,7 Hz vid NTSC (-8 cent)
;   och 571,7 Hz vid 1 MHz (-47 cent). Vi anser det utrett att D5 var avsedd,
;   men att någon troligen räknat med 2^(1/13) istället för 2^(1/12) från C#5
;   (554,365 Hz x 2^(1/13) = 584,726 Hz, vilket ger registervärdet $2578).
; -----------------------------------------------------------------------------
NOTE_D4         EQU  $12D1   ; D4   = 293,7 Hz (NTSC exakt, 1MHz: 287,1 Hz)
NOTE_G4         EQU  $191E   ; G4   = 392,0 Hz (NTSC exakt, 1MHz: 383,3 Hz)
NOTE_A4         EQU  $1C31   ; A4   = 439,9 Hz (NTSC exakt, 1MHz: 430,2 Hz)
NOTE_B4         EQU  $1FA5   ; B4   = 493,8 Hz (NTSC exakt, 1MHz: 482,9 Hz)
NOTE_C5         EQU  $2187   ; C5   = 523,2 Hz (NTSC exakt, 1MHz: 511,6 Hz)
NOTE_D5         EQU  $2578   ; D5   avsedd (NTSC: 584,7 Hz, -8 cent; 1MHz: 571,7 Hz, -47 cent)

; -----------------------------------------------------------------------------
; Fördröjningskonstanter för notlängd (H-registrets startvärde)
;
; Fördröjningsstrukturen för varje not:
;
;   noteXX_ldl:  LD  L, $FF      ; återställ inre räknare    (7 cykler)
;   noteXX_lp:   DEC L           ; räkna ned                 (4 cykler)
;                JR  NZ, lp      ; loopa tills noll          (12/7 cykler)
;                DEC H           ; yttre räknare             (4 cykler)
;                JR  NZ, ldl     ; tillbaka till LD L (inte DEC L!)  (12/7 cykler)
;
; Den yttre JR NZ hoppar tillbaka till "LD L, $FF" så att L alltid laddas
; om fullt till 255 för varje yttre iteration.
; -----------------------------------------------------------------------------
DELAY_SHORT     EQU  $2F     ; kort (grundlängd)
DELAY_LONG      EQU  $65     ; ca 2 x DELAY_SHORT
DELAY_VLONG     EQU  $96     ; ca 3 x DELAY_SHORT (sista noten)

; =============================================================================
; RST / avbrottsvektorområde  ($0000 - $007F)
; =============================================================================

        ORG  $0000

; --- RST $00 / kallstartsingångspunkt ----------------------------------------
rst00:
        NOP

        DEFS $0014 - $, $00         ; fyll med NOPs till $0014

; --- Hårdvaruinitiering ------------------------------------------------------
hw_init:
        LD   A, ATTACK_DECAY
        OUT  (SID_V1_AD), A         ; Röst 1: Attack=2 (~6ms), Decay=9 (~240ms)
        LD   A, MASTER_VOL
        OUT  (SID_VOL), A           ; huvudvolym = 15, filter förbikopplat
        JP   main                   ; hoppa till uppstartsfördröjning

        DEFS $0038 - $, $00         ; fyll RST $08/$10/$18/$20/$28/$30-platser

; --- RST $38 / IM 1 avbrottshanterare ($0038) --------------------------------
; Z80 IM 1 vektorar alltid hit vid /INT.
; Sätter pulsbredd (hög byte = $08, låg byte = $00 -> 50% duty cycle)
; och hoppar sedan till melodin.
irq_handler:
        LD   A, $08
        OUT  (SID_V1_PW_HI), A     ; pulsbredd hög = $08, låg = $00 -> 50% duty cycle
        JP   melody

        DEFS $0066 - $, $00         ; fyll till NMI-vektor

; --- NMI-hanterare ($0066) ---------------------------------------------------
; Hoppar till releasefasen för sista noten för att avbryta den i förtid.
nmi_handler:
        JP   note16_rel

        DEFS $0080 - $, $00         ; fyll till melodistart

; =============================================================================
; Melodi ($0080 - $027F)
;
; Sekvens: D4 B4 D5 B4 G4 | D4 B4 D5 B4 G4 | D4 C5 C5 A4 A4 G4
;
; Varje notblock:
;   Sätt frekvens (hi+lo) -> sätt GATE_ON (pulsvåg, gate på) ->
;   fördröjningsloop (notlängd) -> sätt GATE_OFF (release) ->
;   kort fördröjning (klang ut)
; =============================================================================
melody:

; --- Not 1: D4, kort --------------------------------------------------------
note01:
        LD   A, HIGH NOTE_D4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_D4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note01_ldl:
        LD   L, $FF
note01_lp:
        DEC  L
        JR   NZ, note01_lp
        DEC  H
        JR   NZ, note01_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   L, $FF
note01_rel:
        DEC  L
        JR   NZ, note01_rel
        NOP

; --- Not 2: B4, kort --------------------------------------------------------
note02:
        LD   A, HIGH NOTE_B4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_B4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note02_ldl:
        LD   L, $FF
note02_lp:
        DEC  L
        JR   NZ, note02_lp
        DEC  H
        JR   NZ, note02_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 3: D5, kort --------------------------------------------------------
note03:
        LD   A, HIGH NOTE_D5
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_D5
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note03_ldl:
        LD   L, $FF
note03_lp:
        DEC  L
        JR   NZ, note03_lp
        DEC  H
        JR   NZ, note03_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 4: B4, kort --------------------------------------------------------
note04:
        LD   A, HIGH NOTE_B4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_B4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note04_ldl:
        LD   L, $FF
note04_lp:
        DEC  L
        JR   NZ, note04_lp
        DEC  H
        JR   NZ, note04_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 5: G4, lång (första frasens slut) ----------------------------------
note05:
        LD   A, HIGH NOTE_G4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_G4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_LONG
note05_ldl:
        LD   L, $FF
note05_lp:
        DEC  L
        JR   NZ, note05_lp
        DEC  H
        JR   NZ, note05_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 6: D4, kort --------------------------------------------------------
note06:
        LD   A, HIGH NOTE_D4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_D4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note06_ldl:
        LD   L, $FF
note06_lp:
        DEC  L
        JR   NZ, note06_lp
        DEC  H
        JR   NZ, note06_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 7: B4, kort --------------------------------------------------------
note07:
        LD   A, HIGH NOTE_B4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_B4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note07_ldl:
        LD   L, $FF
note07_lp:
        DEC  L
        JR   NZ, note07_lp
        DEC  H
        JR   NZ, note07_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 8: D5, kort --------------------------------------------------------
note08:
        LD   A, HIGH NOTE_D5
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_D5
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note08_ldl:
        LD   L, $FF
note08_lp:
        DEC  L
        JR   NZ, note08_lp
        DEC  H
        JR   NZ, note08_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 9: B4, kort --------------------------------------------------------
note09:
        LD   A, HIGH NOTE_B4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_B4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note09_ldl:
        LD   L, $FF
note09_lp:
        DEC  L
        JR   NZ, note09_lp
        DEC  H
        JR   NZ, note09_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 10: G4, lång (andra frasens slut) ----------------------------------
note10:
        LD   A, HIGH NOTE_G4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_G4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_LONG
note10_ldl:
        LD   L, $FF
note10_lp:
        DEC  L
        JR   NZ, note10_lp
        DEC  H
        JR   NZ, note10_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 11: D4, kort -------------------------------------------------------
note11:
        LD   A, HIGH NOTE_D4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_D4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note11_ldl:
        LD   L, $FF
note11_lp:
        DEC  L
        JR   NZ, note11_lp
        DEC  H
        JR   NZ, note11_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 12: C5, lång --------------------------------------------------------
note12:
        LD   A, HIGH NOTE_C5
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_C5
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_LONG
note12_ldl:
        LD   L, $FF
note12_lp:
        DEC  L
        JR   NZ, note12_lp
        DEC  H
        JR   NZ, note12_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 13: C5, kort (upprepad tonhöjd, kortare varaktighet) ----------------
note13:
        LD   A, HIGH NOTE_C5
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_C5
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note13_ldl:
        LD   L, $FF
note13_lp:
        DEC  L
        JR   NZ, note13_lp
        DEC  H
        JR   NZ, note13_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 14: A4, lång -------------------------------------------------------
note14:
        LD   A, HIGH NOTE_A4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_A4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_LONG
note14_ldl:
        LD   L, $FF
note14_lp:
        DEC  L
        JR   NZ, note14_lp
        DEC  H
        JR   NZ, note14_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 15: A4, kort (upprepad tonhöjd, kortare varaktighet) ---------------
note15:
        LD   A, HIGH NOTE_A4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_A4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_SHORT
note15_ldl:
        LD   L, $FF
note15_lp:
        DEC  L
        JR   NZ, note15_lp
        DEC  H
        JR   NZ, note15_ldl
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; --- Not 16: G4, mycket lång (sista hållna noten) ---------------------------
; NMI-hanteraren (på $0066) hoppar till note16_rel för att avbryta i förtid.
note16:
        LD   A, HIGH NOTE_G4
        OUT  (SID_V1_FREQ_HI), A
        LD   A, LOW NOTE_G4
        OUT  (SID_V1_FREQ_LO), A
        LD   A, GATE_ON
        OUT  (SID_V1_CTRL), A
        LD   H, DELAY_VLONG
note16_ldl:
        LD   L, $FF
note16_lp:
        DEC  L
        JR   NZ, note16_lp
        DEC  H
        JR   NZ, note16_ldl
note16_rel:
        LD   A, GATE_OFF
        OUT  (SID_V1_CTRL), A       ; release — startar decay-fasen
        LD   A, $FF
        DEC  L
        JR   NZ, $ - 1
        NOP

; =============================================================================
; Tystnad ($0280) — nollar alla Röst 1-register för att stoppa ljud
; =============================================================================
silence:
        LD   A, $00
        OUT  (SID_V1_FREQ_LO), A
        OUT  (SID_V1_FREQ_HI), A
        OUT  (SID_V1_PW_LO),   A
        OUT  (SID_V1_PW_HI),   A
        NOP
        NOP
        NOP
        NOP
        NOP
        NOP

; =============================================================================
; Huvudingångspunkt ($0290)
; Nås från hw_init (JP main) vid reset, och även efter varje uppspelning
; eftersom melodin faller igenom silence in hit.
; Kör en fördröjning på ca 2,8 s (avbrott är avstängda under tiden),
; ställer in stackpekare och avbrottsläge, aktiverar avbrott med EI och
; kör sedan HALT. Därefter drivs melodin helt av /INT-avbrott.
; =============================================================================
        DEFS $0290 - $, $00

main:
        ; Fördröjning: ca 2,83 miljoner Z80-cykler = ca 2,8 s vid 1 MHz.
        ; Körs efter varje melodi, inte bara vid strömpåslag. Syftet är okänt.
        ; Avbrott är avstängda hela tiden (IFF1 = 0 sedan avbrottet accepterades).
        ; Struktur: 15 x (46 x (L=$FF inre loop)).
        LD   E, $0F                 ; 15 yttre iterationer
main_outer:
        LD   H, $2E
main_ldl:
        LD   L, $FF
main_lp:
        DEC  L
        JR   NZ, main_lp
        DEC  H
        JR   NZ, main_ldl
        DEC  E
        JR   NZ, main_outer
        NOP

        LD   SP, $FFFF              ; sätt stackpekaren till toppen av RAM
        IM   1                      ; avbrottsläge 1: /INT vektorar till $0038
        EI                          ; aktivera avbrott
        HALT                        ; vänta på första /INT

        ; Fyll resterande del av 2 KB ROM-avbilden med $FF (oskriven EPROM)
        DEFS $0800 - $, $FF
