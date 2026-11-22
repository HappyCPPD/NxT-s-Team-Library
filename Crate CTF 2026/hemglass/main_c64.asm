SID_V1_FREQ_LO  =  $d400    ; Röst 1 frekvens, låg byte
SID_V1_FREQ_HI  =  $d401    ; Röst 1 frekvens, hög byte
SID_V1_PW_LO    =  $d402    ; Röst 1 pulsbredd, låg byte
SID_V1_PW_HI    =  $d403    ; Röst 1 pulsbredd, hög byte
SID_V1_CTRL     =  $d404    ; Röst 1 kontrollregister
SID_V1_AD       =  $d405    ; Röst 1 Attack / Decay
SID_V1_SR       =  $d406    ; Röst 1 Sustain / Release  (används ej)
SID_VOL         =  $d418    ; Filterläge / huvudvolym

; Kontrollregistervärden — bit 6 = PULSE, bit 0 = GATE
; Bitmönster: 7=NOISE, 6=PULSE, 5=SAW, 4=TRI, 3=TEST, 2=RING, 1=SYNC, 0=GATE
GATE_ON         =  $41    ; %01000001 — pulsvåg, gate PÅ
GATE_OFF        =  $40    ; %01000000 — pulsvåg, gate AV (release)

; -----------------------------------------------------------------------------
; Envelope:  Attack/Decay = $29
;   Attack  nibble $2 -> ~6 ms
;   Decay   nibble $9 -> ~240 ms
; Volym:    $0F = max, inget filter
; -----------------------------------------------------------------------------
ATTACK_DECAY    =  $29
MASTER_VOL      =  $0F

; Värden för frekvensregistren för respektive ton.
; Dessa världen är avsedda att låta välstämt på en PAL C64/128 
; Detta skiljer sig lite från speldosan i Hemglassbilen som inte var rätt stämd
NOTE_D4         =  $1389   ; D4   = 293,7 Hz
NOTE_G4         =  $1a13   ; G4   = 392,0 Hz
NOTE_A4         =  $1d45   ; A4   = 440,0 Hz
NOTE_B4         =  $20da   ; B4   = 493,9 Hz
NOTE_C5         =  $22ce   ; C5   = 523,2 Hz
NOTE_D5         =  $2711   ; D5   = 587,3 Hz

; fördröjningskonstanter för fördröjningsslinga vid notspelning
DELAY_SHORT     =  $36     ; fjärdedelsnot
DELAY_LONG      =  $77     ; halvnot
DELAY_VLONG     =  $ad     ; punkterad halvnot (sista noten)


*=$0801
        BYTE    $27, $08, $40, $00, $9E, $32, $30, $38, $38, $3a, $8f, $20, $53, $56, $45, $4E, $53, $4B, $41, $20, $43, $4F, $4D, $4D, $4F, $44, $4F, $52, $45, $4B, $4C, $55, $42, $42, $45, $4E, $00, $00, $00

hw_init
        lda #ATTACK_DECAY       ; $29
        sta SID_V1_AD           ; Röst 1: Attack=2 (~6ms), Decay=9 (~240ms)
        lda #MASTER_VOL         ; $0f
        sta SID_VOL             ; huvudvolym = 15, filter förbikopplat
        lda #$08
        sta SID_V1_PW_HI        ; pulsbredd hög = $08, låg = $00 -> 50% duty cycle
       
melody
        sei
        ldx #>NOTE_D4
        ldy #<NOTE_D4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_B4
        ldy #<NOTE_B4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_D5
        ldy #<NOTE_D5
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_B4
        ldy #<NOTE_B4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_G4
        ldy #<NOTE_G4
        lda #DELAY_LONG
        jsr play_note

        ldx #>NOTE_D4
        ldy #<NOTE_D4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_B4
        ldy #<NOTE_B4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_D5
        ldy #<NOTE_D5
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_B4
        ldy #<NOTE_B4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_G4
        ldy #<NOTE_G4
        lda #DELAY_LONG
        jsr play_note

        ldx #>NOTE_D4
        ldy #<NOTE_D4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_C5
        ldy #<NOTE_C5
        lda #DELAY_LONG
        jsr play_note

        ldx #>NOTE_C5
        ldy #<NOTE_C5
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_A4
        ldy #<NOTE_A4
        lda #DELAY_LONG
        jsr play_note

        ldx #>NOTE_A4
        ldy #<NOTE_A4
        lda #DELAY_SHORT
        jsr play_note

        ldx #>NOTE_G4
        ldy #<NOTE_G4
        lda #DELAY_VLONG
        jsr play_note

silence
        lda #0
        sta SID_V1_FREQ_LO
        sta SID_V1_FREQ_HI
        sta SID_V1_PW_LO
        sta SID_V1_PW_HI
exit
        rts


; Denna rutin spelar en not
; notfrekvens hög byte i X
; notfrekvens låg byte i Y
; notlängd i A
play_note
        stx SID_V1_FREQ_HI
        sty SID_V1_FREQ_LO
        tax ; notlängd > X
        lda #GATE_ON
        sta SID_V1_CTRL
note_ldl
        ldy #$ff
note_lp
        nop
        nop
        nop
        nop
        dey
        bne note_lp
        dex
        bne note_ldl
        
        lda #GATE_OFF
        sta SID_V1_CTRL
        ldy #$ff
note_rel
        dey
        bne note_rel
        rts
