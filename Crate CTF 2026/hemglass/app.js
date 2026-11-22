/* app.js – gränssnittet för speldosan. */
(function () {
  'use strict';
  const VERIFY_URL = document.querySelector('meta[name="verify-url"]').content;
  const $ = (id) => document.getElementById(id);
  const melodyEl = $('melody'), runBtn = $('run'), stopBtn = $('stop');
  const tokensEl = $('tokens'), outEl = $('out'), scope = $('scope');
  const css = getComputedStyle(document.documentElement);
  const TEXT = css.getPropertyValue('--text').trim();

  let ctx = null, source = null, analyser = null, rafId = 0, session = 0;
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  function audio() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.connect(ctx.destination);
    }
    return ctx;
  }

  // Skriv rader som på en hemdator: en i taget, med blinkande markör sist.
  async function print(lines, my, delay) {
    outEl.textContent = '';
    const cur = document.createElement('span');
    cur.className = 'cursor';
    outEl.appendChild(cur);
    for (const [text, cls] of lines) {
      if (delay) { await wait(delay); if (my !== undefined && my !== session) return; }
      const div = document.createElement('div');
      div.className = 'line' + (cls ? ' ' + cls : '');
      div.textContent = text;
      outEl.insertBefore(div, cur);
    }
  }

  function showTokens(list, badIndex) {
    tokensEl.textContent = '';
    list.forEach((t, i) => {
      const s = document.createElement('span');
      s.className = 'tok' + (t.rest ? ' rest' : '') + (i === badIndex ? ' bad' : '');
      s.textContent = t.canonical || t.token;
      tokensEl.appendChild(s);
    });
  }

  // Oscilloskop i 320x40 pixlar, uppskalat utan utjämning.
  function drawScope() {
    const g = scope.getContext('2d');
    const w = scope.width, h = scope.height;
    g.clearRect(0, 0, w, h);
    g.fillStyle = TEXT;
    if (!analyser) { g.fillRect(0, h >> 1, w, 1); return; }
    const data = new Float32Array(analyser.fftSize);
    analyser.getFloatTimeDomainData(data);
    let prev = null;
    for (let x = 0; x < w; x++) {
      const v = data[Math.floor(x / w * data.length)];
      const y = Math.max(0, Math.min(h - 1, Math.round(h / 2 - v * h * 1.1)));
      const y0 = prev === null ? y : prev;
      g.fillRect(x, Math.min(y0, y), 1, Math.abs(y - y0) + 1);
      prev = y;
    }
  }

  function stop() {
    session++;
    if (source) { try { source.stop(); } catch (e) {} source = null; }
    cancelAnimationFrame(rafId);
    tokensEl.querySelectorAll('.active').forEach((el) => el.classList.remove('active'));
    drawScope();
    runBtn.disabled = false;
    stopBtn.disabled = true;
  }

  async function verify(text) {
    try {
      const res = await fetch(VERIFY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ melody: text }),
      });
      let body = null;
      try { body = await res.json(); } catch (e) {}
      if (!body) return { ok: false, error: '?DEVICE NOT PRESENT  ERROR', message: 'HTTP ' + res.status };
      return body;
    } catch (e) {
      return { ok: false, error: '?DEVICE NOT PRESENT  ERROR', message: '' };
    }
  }

  async function run() {
    stop();
    const my = session;
    const text = melodyEl.value;
    let notes;
    try {
      notes = Synth.parseMelody(text);
    } catch (e) {
      if (e instanceof Synth.MelodyError) {
        const raw = text.trim().split(/[\s,;]+/).filter(Boolean).map((token) => ({ token }));
        showTokens(raw, e.index);
        print([['?SYNTAX  ERROR', 'err'], [e.message, 'err'], ['READY.', '']]);
        return;
      }
      throw e;
    }
    showTokens(notes, -1);

    const bpm = Math.min(400, Math.max(30, Number($('bpm').value) || 120));
    if (Synth.duration(notes, bpm) > Synth.MAX_SECONDS) {   // kontrollera innan något renderas
      print([['?OVERFLOW  ERROR', 'err'], ['Melodin är längre än 3 minuter.', 'err'], ['READY.', '']]);
      return;
    }
    const ac = audio();
    if (ac.state === 'suspended') await ac.resume();

    const { samples, timeline } = Synth.render(notes, { sampleRate: ac.sampleRate, bpm });

    runBtn.disabled = true;
    stopBtn.disabled = false;
    const verdict = verify(text);
    await print([['LOAD"HEMGLASS",8,1', 'white'], ['', ''], ['SEARCHING FOR HEMGLASS', ''], ['LOADING', ''], ['READY.', ''], ['RUN', 'white']], my, 140);
    if (my !== session) return;

    const buf = ac.createBuffer(1, samples.length, ac.sampleRate);
    buf.copyToChannel(samples, 0);
    source = ac.createBufferSource();
    source.buffer = buf;
    source.connect(analyser);
    const t0 = ac.currentTime + 0.05;
    source.start(t0);

    const chips = tokensEl.children;
    let last = -1;
    (function tick() {
      const t = ac.currentTime - t0;
      let idx = -1;
      for (let i = 0; i < timeline.length; i++) {
        if (t >= timeline[i].start && t < timeline[i].end) { idx = i; break; }
      }
      if (idx !== last) {
        if (last >= 0 && chips[last]) chips[last].classList.remove('active');
        if (idx >= 0 && chips[idx]) chips[idx].classList.add('active');
        last = idx;
      }
      drawScope();
      rafId = requestAnimationFrame(tick);
    })();

    await new Promise((resolve) => { source.onended = resolve; });
    if (my !== session) return;     // avbruten
    stop();
    const done = session;

    const r = await verdict;
    if (done !== session) return;   // ny körning har startat
    if (r.ok) {
      print([['Rätt melodi!', 'ok'], ['Glassbilen är på väg.', 'ok'], ['', ''], [String(r.flag || ''), 'flag'], ['', ''], ['READY.', '']]);
    } else {
      const lines = [[r.error || '?WRONG MELODY  ERROR', 'err']];
      if (r.message) lines.push([r.message, 'err']);
      lines.push(['READY.', '']);
      print(lines);
    }
  }

  runBtn.addEventListener('click', run);
  stopBtn.addEventListener('click', () => { stop(); print([['BREAK', ''], ['READY.', '']]); });
  melodyEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); if (!runBtn.disabled) run(); }
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !stopBtn.disabled) stopBtn.click();   // RUN/STOP
  });
  drawScope();
})();
