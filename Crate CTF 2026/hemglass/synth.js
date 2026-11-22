/*
 * synth.js – notparser och enkel syntes (en röst, pulsvåg).
 * Fungerar både i webbläsaren (window.Synth) och i Node (module.exports).
 */
(function (root) {
  'use strict';

  const NOTE_INDEX = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const VALID_LENGTHS = [1, 2, 4, 8, 16, 32];
  // <längd>[.]<ton>[#|S]<oktav>  eller  <längd>[.]P[oktav]   ("." = punkterad, 1,5 x längden)
  const TOKEN_RE = /^(\d{1,2})(\.?)(?:([A-G])([#S])?([0-8])|P([0-8])?)$/i;
  const MAX_TOKENS = 512;
  const MAX_SECONDS = 180;

  class MelodyError extends Error {
    constructor(message, index, token) {
      super(message);
      this.name = 'MelodyError';
      this.index = index;
      this.token = token;
    }
  }

  function parseMelody(text) {
    const raw = String(text).trim().split(/[\s,;]+/).filter(Boolean);
    if (raw.length === 0) throw new MelodyError('Tom sekvens', -1, '');
    if (raw.length > MAX_TOKENS) throw new MelodyError('För många noter (max ' + MAX_TOKENS + ')', MAX_TOKENS, '');
    return raw.map((token, index) => {
      const m = TOKEN_RE.exec(token);
      if (!m) throw new MelodyError('Ogiltig not: ' + token.slice(0, 16), index, token);
      const length = parseInt(m[1], 10);
      if (!VALID_LENGTHS.includes(length)) {
        throw new MelodyError('Ogiltig notlängd ' + length + ' (tillåtet: ' + VALID_LENGTHS.join(', ') + ')', index, token);
      }
      const dotted = m[2] === '.';
      const beats = (4 / length) * (dotted ? 1.5 : 1);
      const prefix = length + (dotted ? '.' : '');
      if (!m[3]) return { token, length, dotted, beats, rest: true, canonical: prefix + 'P' };
      const letter = m[3].toUpperCase();
      const sharp = !!m[4];
      const octave = parseInt(m[5], 10);
      const midi = 12 * (octave + 1) + NOTE_INDEX[letter] + (sharp ? 1 : 0);
      return {
        token, length, dotted, beats, rest: false, letter, sharp, octave, midi,
        freq: 440 * Math.pow(2, (midi - 69) / 12),
        canonical: prefix + letter + (sharp ? '#' : '') + octave,
      };
    });
  }

  function canonicalize(notes) {
    return notes.map((n) => n.canonical).join(' ');
  }

  // Speltid i sekunder (utan efterklang).
  function duration(notes, bpm) {
    return notes.reduce((sum, n) => sum + n.beats, 0) * 60 / bpm;
  }

  const DEFAULTS = {
    sampleRate: 44100,
    bpm: 120,
    duty: 0.5,         // pulsbredd
    attack: 0.016,     // s, linjärt anslag
    decay: 0.155,      // s, tidskonstant för avklingning medan tonen hålls
    release: 0.0015,   // s, tidskonstant efter släpp
    maxFreq: 3900,     // Hz, högre toner klipps
    gap: 0.02,         // s mellan släpp och nästa ton
    tail: 0.4,         // s extra i slutet
    volume: 0.35,
    lowpass: 12000,
  };

  function render(notes, options) {
    const o = Object.assign({}, DEFAULTS, options || {});
    const sr = o.sampleRate;
    const OS = 8;
    const beat = 60 / o.bpm;
    if (duration(notes, o.bpm) > MAX_SECONDS) {
      throw new MelodyError('Melodin är längre än ' + MAX_SECONDS / 60 + ' minuter', -1, '');
    }

    // Tidslinje och gate-händelser (i samples).
    const timeline = [];
    const events = [];
    let t = 0;
    for (const n of notes) {
      const dur = n.beats * beat;
      timeline.push({ start: t, end: t + dur });
      const s0 = Math.round(t * sr);
      if (n.rest) {
        events.push({ at: s0, gate: false });
      } else {
        const holdSec = Math.max(dur - o.gap, dur * 0.5);
        events.push({ at: s0, gate: true, freq: Math.min(n.freq, o.maxFreq) });
        events.push({ at: Math.round((t + holdSec) * sr), gate: false });
      }
      t += dur;
    }
    const total = Math.ceil((t + o.tail) * sr);
    const out = new Float32Array(total);

    const attackStep = 1 / (o.attack * sr);
    const decayMul = Math.exp(-1 / (o.decay * sr));
    const releaseMul = Math.exp(-1 / (o.release * sr));
    const lpA = 1 - Math.exp(-2 * Math.PI * o.lowpass / sr);
    const hpR = Math.exp(-2 * Math.PI * 16 / sr);

    let phase = 0, inc = 0, env = 0, attacking = false, held = false;
    let lp1 = 0, lp2 = 0, hpIn = 0, hpOut = 0;
    let ev = 0;

    for (let i = 0; i < total; i++) {
      while (ev < events.length && events[ev].at <= i) {
        const e = events[ev++];
        if (e.gate) { inc = e.freq / (sr * OS); attacking = true; held = true; }
        else { attacking = false; held = false; }
      }

      // Envelope, kvantiserad till 8 bitar
      if (attacking) {
        env += attackStep;
        if (env >= 1) { env = 1; attacking = false; }
      } else {
        env *= held ? decayMul : releaseMul;
      }
      const level = Math.floor(env * 255) / 255;

      // Pulsvåg med översampling
      let sum = 0;
      for (let k = 0; k < OS; k++) {
        phase += inc;
        if (phase >= 1) phase -= 1;
        sum += phase >= o.duty ? 1 : -1;
      }

      // Utgång: två lågpass + DC-spärr
      const x = (sum / OS) * level;
      lp1 += lpA * (x - lp1);
      lp2 += lpA * (lp1 - lp2);
      hpOut = lp2 - hpIn + hpR * hpOut;
      hpIn = lp2;
      out[i] = hpOut * o.volume;
    }

    return { samples: out, timeline, duration: total / sr };
  }

  const api = { parseMelody, canonicalize, duration, render, MelodyError, DEFAULTS, VALID_LENGTHS, MAX_SECONDS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Synth = api;
})(typeof window !== 'undefined' ? window : globalThis);
