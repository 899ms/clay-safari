// All sound is generated: Web Speech for the names, Web Audio synthesis for the animal calls
// and UI pops.  No audio files, works offline.  Swap `animalSound` for real recordings later.
let ctx = null, master = null, enabled = true, ambientNodes = null;
const AC = window.AudioContext || window.webkitAudioContext;

export function initAudio() {
  if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return; }
  ctx = new AC();
  master = ctx.createGain(); master.gain.value = 0.8; master.connect(ctx.destination);
  const comp = ctx.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 6;
  master.disconnect(); master.connect(comp); comp.connect(ctx.destination);
  if (window.speechSynthesis) { speechSynthesis.getVoices(); speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices(); }
}
export function setEnabled(on) { enabled = on; if (master) master.gain.setTargetAtTime(on ? 0.8 : 0, ctx.currentTime, 0.05); if (!on && window.speechSynthesis) speechSynthesis.cancel(); }
export function isEnabled() { return enabled; }

// ---------------------------------------------------------------- primitives
function now() { return ctx.currentTime; }
function ensureNoise() {
  if (!noiseBuf) { noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate); const dd = noiseBuf.getChannelData(0); for (let i = 0; i < dd.length; i++) dd[i] = Math.random() * 2 - 1; }
  return noiseBuf;
}
function env(g, t0, a, d, s, r, peak = 1, sus = 0.5, dur = 0.3) {
  peak = Math.max(0.0002, peak);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(peak, t0 + a);
  g.gain.exponentialRampToValueAtTime(Math.max(0.0001, peak * sus), t0 + a + d);
  g.gain.setValueAtTime(Math.max(0.0001, peak * sus), t0 + a + d + dur);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + a + d + dur + r);
}
function tone({ type = 'sine', f0 = 440, f1 = null, t0 = 0, a = 0.02, d = 0.1, s = 0.5, dur = 0.2, r = 0.1, gain = 0.3, vib = 0, vibF = 6, filter = null, q = 1, pan = 0, dist = 0 }) {
  const t = now() + t0;
  const o = ctx.createOscillator(); o.type = type;
  o.frequency.setValueAtTime(f0, t);
  if (f1 != null) o.frequency.exponentialRampToValueAtTime(f1, t + a + d + dur);
  let node = o;
  if (vib > 0) { const lfo = ctx.createOscillator(); lfo.frequency.value = vibF; const lg = ctx.createGain(); lg.gain.value = vib; lfo.connect(lg); lg.connect(o.frequency); lfo.start(t); lfo.stop(t + a + d + dur + r + 0.1); }
  if (dist > 0) { const ws = ctx.createWaveShaper(); const n = 256, c = new Float32Array(n); for (let i = 0; i < n; i++) { const x = i * 2 / n - 1; c[i] = Math.tanh(x * dist); } ws.curve = c; node.connect(ws); node = ws; }
  if (filter) { const fl = ctx.createBiquadFilter(); fl.type = filter.type || 'lowpass'; fl.frequency.value = filter.f; fl.Q.value = q; node.connect(fl); node = fl; }
  const g = ctx.createGain(); env(g, t, a, d, s, r, gain, s, dur);
  node.connect(g);
  const p = ctx.createStereoPanner(); p.pan.value = pan; g.connect(p); p.connect(master);
  o.start(t); o.stop(t + a + d + dur + r + 0.05);
}
let noiseBuf = null;
function noise({ t0 = 0, a = 0.01, d = 0.1, s = 0.5, dur = 0.2, r = 0.1, gain = 0.2, filter = { type: 'lowpass', f: 1000 }, q = 1, pan = 0, f1 = null }) {
  ensureNoise();
  const t = now() + t0;
  const src = ctx.createBufferSource(); src.buffer = noiseBuf; src.loop = true;
  const fl = ctx.createBiquadFilter(); fl.type = filter.type; fl.frequency.setValueAtTime(filter.f, t); fl.Q.value = q;
  if (f1) fl.frequency.exponentialRampToValueAtTime(f1, t + a + d + dur);
  const g = ctx.createGain(); env(g, t, a, d, s, r, gain, s, dur);
  src.connect(fl); fl.connect(g);
  const p = ctx.createStereoPanner(); p.pan.value = pan; g.connect(p); p.connect(master);
  src.start(t); src.stop(t + a + d + dur + r + 0.05);
}

// ---------------------------------------------------------------- animal calls (returns duration in s)
const CALLS = {
  lion() {
    tone({ type: 'sawtooth', f0: 95, f1: 62, a: 0.15, d: 0.4, s: 0.7, dur: 0.9, r: 0.5, gain: 0.55, vib: 6, vibF: 5.5, filter: { f: 420 }, q: 2, dist: 4 });
    tone({ type: 'square', f0: 48, f1: 36, a: 0.2, d: 0.4, s: 0.6, dur: 0.8, r: 0.5, gain: 0.25, filter: { f: 200 } });
    noise({ a: 0.1, d: 0.5, s: 0.5, dur: 0.6, r: 0.6, gain: 0.18, filter: { type: 'bandpass', f: 500 }, q: 0.8 });
    return 2.2;
  },
  elephant() {
    tone({ type: 'sawtooth', f0: 260, f1: 720, a: 0.12, d: 0.35, s: 0.8, dur: 0.5, r: 0.35, gain: 0.35, vib: 18, vibF: 7, filter: { type: 'bandpass', f: 1100 }, q: 2.5, dist: 3 });
    tone({ type: 'sawtooth', f0: 130, f1: 360, a: 0.12, d: 0.35, s: 0.8, dur: 0.5, r: 0.35, gain: 0.2, filter: { f: 900 }, dist: 2 });
    return 1.5;
  },
  monkey() {
    for (let i = 0; i < 6; i++) tone({ type: 'triangle', f0: 520 + i * 90, f1: 900 + i * 90, t0: i * 0.17, a: 0.02, d: 0.05, s: 0.6, dur: 0.05, r: 0.05, gain: 0.35, filter: { type: 'bandpass', f: 1400 }, q: 1.2, pan: (i % 2) * 0.4 - 0.2 });
    return 1.3;
  },
  zebra() {
    for (let i = 0; i < 7; i++) tone({ type: i % 2 ? 'sawtooth' : 'square', f0: i % 2 ? 420 : 760, f1: i % 2 ? 380 : 700, t0: i * 0.11, a: 0.01, d: 0.04, s: 0.6, dur: 0.04, r: 0.04, gain: 0.22, filter: { type: 'bandpass', f: 900 }, q: 1.5, dist: 2 });
    return 1.1;
  },
  giraffe() {
    tone({ type: 'sine', f0: 92, f1: 84, a: 0.3, d: 0.3, s: 0.8, dur: 0.8, r: 0.5, gain: 0.5, vib: 3, vibF: 4 });
    tone({ type: 'triangle', f0: 184, f1: 170, a: 0.3, d: 0.3, s: 0.6, dur: 0.8, r: 0.5, gain: 0.12 });
    return 2.0;
  },
  hippo() {
    for (let i = 0; i < 3; i++) {
      noise({ t0: i * 0.32, a: 0.02, d: 0.1, s: 0.6, dur: 0.1, r: 0.1, gain: 0.45, filter: { type: 'lowpass', f: 260 }, q: 3 });
      tone({ type: 'sawtooth', f0: 70, f1: 55, t0: i * 0.32, a: 0.02, d: 0.1, s: 0.6, dur: 0.1, r: 0.1, gain: 0.3, filter: { f: 300 }, dist: 3 });
    }
    return 1.3;
  },
  crocodile() {
    noise({ a: 0.05, d: 0.3, s: 0.7, dur: 0.5, r: 0.3, gain: 0.25, filter: { type: 'bandpass', f: 2500 }, q: 0.7 });
    tone({ type: 'sawtooth', f0: 62, f1: 50, a: 0.1, d: 0.3, s: 0.7, dur: 0.5, r: 0.3, gain: 0.35, vib: 4, vibF: 9, filter: { f: 250 }, dist: 5 });
    return 1.4;
  },
  snake() {
    noise({ a: 0.08, d: 0.2, s: 0.7, dur: 0.6, r: 0.3, gain: 0.3, filter: { type: 'highpass', f: 3200 }, q: 0.5, f1: 5000 });
    noise({ t0: 0.02, a: 0.08, d: 0.2, s: 0.5, dur: 0.6, r: 0.3, gain: 0.12, filter: { type: 'bandpass', f: 6000 }, q: 2 });
    return 1.3;
  },
  bird() {
    const seq = [[2200, 3300], [2600, 3600], [3000, 2400], [2400, 3800], [2800, 3200]];
    seq.forEach(([a, b], i) => tone({ type: 'sine', f0: a, f1: b, t0: i * 0.14 + (i > 2 ? 0.1 : 0), a: 0.01, d: 0.04, s: 0.7, dur: 0.05, r: 0.05, gain: 0.25, pan: 0.3 }));
    return 1.0;
  },
  fish() {
    for (let i = 0; i < 6; i++) tone({ type: 'sine', f0: 500 + i * 120, f1: 1400 + i * 100, t0: i * 0.13 + Math.random() * 0.03, a: 0.005, d: 0.04, s: 0.3, dur: 0.02, r: 0.05, gain: 0.22, filter: { f: 2500 }, pan: (i - 3) * 0.1 });
    noise({ a: 0.05, d: 0.3, s: 0.5, dur: 0.4, r: 0.3, gain: 0.08, filter: { type: 'lowpass', f: 700 } });
    return 1.1;
  },
  truck() {
    tone({ type: 'square', f0: 392, a: 0.01, d: 0.05, s: 0.8, dur: 0.22, r: 0.05, gain: 0.2, filter: { f: 1800 } });
    tone({ type: 'square', f0: 494, a: 0.01, d: 0.05, s: 0.8, dur: 0.22, r: 0.05, gain: 0.2, filter: { f: 1800 } });
    tone({ type: 'square', f0: 392, t0: 0.34, a: 0.01, d: 0.05, s: 0.8, dur: 0.3, r: 0.05, gain: 0.2, filter: { f: 1800 } });
    tone({ type: 'square', f0: 494, t0: 0.34, a: 0.01, d: 0.05, s: 0.8, dur: 0.3, r: 0.05, gain: 0.2, filter: { f: 1800 } });
    tone({ type: 'sawtooth', f0: 55, f1: 80, a: 0.05, d: 0.3, s: 0.6, dur: 0.6, r: 0.3, gain: 0.2, filter: { f: 200 }, dist: 3 });
    return 1.3;
  },
  camera() { noise({ a: 0.003, d: 0.03, s: 0.2, dur: 0.02, r: 0.05, gain: 0.5, filter: { type: 'highpass', f: 2000 } }); tone({ type: 'square', f0: 1800, f1: 900, a: 0.003, d: 0.03, s: 0.2, dur: 0.02, r: 0.05, gain: 0.15 }); noise({ t0: 0.12, a: 0.003, d: 0.03, s: 0.2, dur: 0.02, r: 0.05, gain: 0.3, filter: { type: 'highpass', f: 2500 } }); return 0.5; },
  binoculars() { [880, 1320, 1760].forEach((f, i) => tone({ type: 'sine', f0: f, t0: i * 0.1, a: 0.01, d: 0.1, s: 0.4, dur: 0.1, r: 0.3, gain: 0.2 })); return 0.8; },
  stump() { tone({ type: 'sine', f0: 140, f1: 70, a: 0.005, d: 0.08, s: 0.2, dur: 0.05, r: 0.15, gain: 0.5 }); tone({ type: 'sine', f0: 140, f1: 70, t0: 0.2, a: 0.005, d: 0.08, s: 0.2, dur: 0.05, r: 0.15, gain: 0.4 }); return 0.6; },
  bone() { for (let i = 0; i < 3; i++) tone({ type: 'triangle', f0: 1200 - i * 200, f1: 600, t0: i * 0.12, a: 0.003, d: 0.05, s: 0.2, dur: 0.02, r: 0.08, gain: 0.25, filter: { f: 3000 } }); return 0.6; },
  banana() { tone({ type: 'sine', f0: 320, f1: 140, a: 0.01, d: 0.25, s: 0.5, dur: 0.1, r: 0.2, gain: 0.35, vib: 30, vibF: 12 }); return 0.7; },
  flower() { [523, 659, 784, 1047, 1319].forEach((f, i) => tone({ type: 'sine', f0: f, t0: i * 0.08, a: 0.01, d: 0.12, s: 0.4, dur: 0.05, r: 0.4, gain: 0.18, pan: (i - 2) * 0.2 })); return 1.0; },
  robot() { [660, 880, 1100].forEach((f, i) => tone({ type: 'square', f0: f, t0: i * 0.09, a: 0.01, d: 0.05, s: 0.5, dur: 0.05, r: 0.08, gain: 0.12, filter: { f: 2500 } })); return 0.5; },
};

export function animalSound(id) {
  if (!ctx || !enabled) return Promise.resolve();
  const fn = CALLS[id] || CALLS.flower;
  const dur = fn();
  return new Promise(r => setTimeout(r, dur * 1000));
}

// ---------------------------------------------------------------- UI sounds
export const sfx = {
  pop() { if (!ctx || !enabled) return; tone({ type: 'sine', f0: 600, f1: 900, a: 0.005, d: 0.06, s: 0.3, dur: 0.02, r: 0.08, gain: 0.25 }); },
  sparkle() { if (!ctx || !enabled) return; [1319, 1568, 2093, 2637].forEach((f, i) => tone({ type: 'sine', f0: f, t0: i * 0.06, a: 0.005, d: 0.1, s: 0.3, dur: 0.05, r: 0.35, gain: 0.16 })); },
  fanfare() { if (!ctx || !enabled) return; [[523, 0], [659, 0.15], [784, 0.3], [1047, 0.45], [784, 0.7], [1047, 0.85]].forEach(([f, t]) => { tone({ type: 'triangle', f0: f, t0: t, a: 0.01, d: 0.1, s: 0.6, dur: 0.12, r: 0.2, gain: 0.25 }); tone({ type: 'square', f0: f / 2, t0: t, a: 0.01, d: 0.1, s: 0.4, dur: 0.12, r: 0.2, gain: 0.08, filter: { f: 1500 } }); }); },
  step() { if (!ctx || !enabled) return; noise({ a: 0.003, d: 0.03, s: 0.2, dur: 0.01, r: 0.04, gain: 0.05, filter: { type: 'lowpass', f: 500 } }); },
  splash() { if (!ctx || !enabled) return; noise({ a: 0.01, d: 0.15, s: 0.4, dur: 0.1, r: 0.3, gain: 0.25, filter: { type: 'bandpass', f: 1800 }, q: 0.6, f1: 600 }); },
  whoosh() { if (!ctx || !enabled) return; noise({ a: 0.1, d: 0.2, s: 0.5, dur: 0.1, r: 0.3, gain: 0.12, filter: { type: 'bandpass', f: 800 }, q: 0.8, f1: 2400 }); },
};

// ---------------------------------------------------------------- ambient bed (wind + distant birds + water near river)
export function startAmbient() {
  if (!ctx || ambientNodes) return;
  const wind = ctx.createBufferSource(); wind.buffer = ensureNoise(); wind.loop = true;
  const wf = ctx.createBiquadFilter(); wf.type = 'lowpass'; wf.frequency.value = 380; wf.Q.value = 0.5;
  const wg = ctx.createGain(); wg.gain.value = 0.045;
  const lfo = ctx.createOscillator(); lfo.frequency.value = 0.13; const lg = ctx.createGain(); lg.gain.value = 0.025; lfo.connect(lg); lg.connect(wg.gain); lfo.start();
  wind.connect(wf); wf.connect(wg); wg.connect(master); wind.start();
  const water = ctx.createBufferSource(); water.buffer = noiseBuf; water.loop = true;
  const wtf = ctx.createBiquadFilter(); wtf.type = 'bandpass'; wtf.frequency.value = 1500; wtf.Q.value = 0.4;
  const wtg = ctx.createGain(); wtg.gain.value = 0;
  water.connect(wtf); wtf.connect(wtg); wtg.connect(master); water.start();
  let chirpTimer = null;
  const chirp = () => {
    if (enabled) { const base = 1800 + Math.random() * 1200, pan = Math.random() * 1.6 - 0.8; for (let i = 0; i < 2 + Math.floor(Math.random() * 3); i++) tone({ type: 'sine', f0: base, f1: base * (1 + (Math.random() - 0.4) * 0.6), t0: i * 0.12, a: 0.01, d: 0.05, s: 0.5, dur: 0.04, r: 0.06, gain: 0.05, pan }); }
    chirpTimer = setTimeout(chirp, 2500 + Math.random() * 6000);
  };
  chirpTimer = setTimeout(chirp, 1500);
  ambientNodes = { wg, wtg, chirpTimer };
}
export function setWaterProximity(t) { if (ambientNodes) ambientNodes.wtg.gain.setTargetAtTime(0.12 * t, ctx.currentTime, 0.3); }

// ---------------------------------------------------------------- speech
let voicesCache = null;
function pickVoice(lang) {
  if (!window.speechSynthesis) return null;
  const vs = speechSynthesis.getVoices(); if (!vs.length) return null;
  const prefer = lang.startsWith('en') ? ['Samantha', 'Google US English', 'Karen', 'Daniel', 'Moira', 'Microsoft Aria'] : ['Tingting', 'Ting-Ting', 'Google 普通话', 'Meijia', 'Microsoft Xiaoxiao', 'Lili'];
  for (const p of prefer) { const v = vs.find(v => v.name.includes(p) && v.lang.replace('_', '-').toLowerCase().startsWith(lang.slice(0, 2))); if (v) return v; }
  return vs.find(v => v.lang.replace('_', '-').toLowerCase().startsWith(lang.toLowerCase())) || vs.find(v => v.lang.toLowerCase().startsWith(lang.slice(0, 2))) || null;
}
export function speak(text, lang = 'en-US', { rate = 0.85, pitch = 1.15 } = {}) {
  if (!window.speechSynthesis || !enabled) return Promise.resolve();
  return new Promise(resolve => {
    try {
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = lang; u.rate = rate; u.pitch = pitch; u.volume = 1;
      const v = pickVoice(lang); if (v) u.voice = v;
      let finished = false;
      const fin = () => { if (!finished) { finished = true; resolve(); } };
      u.onend = fin; u.onerror = fin;
      setTimeout(fin, 700 + text.length * 260);
      speechSynthesis.speak(u);
    } catch (e) { resolve(); }
  });
}
export function stopSpeech() { if (window.speechSynthesis) speechSynthesis.cancel(); }
