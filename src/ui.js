import { TITLE, TITLE_COLORS, ITEMS, ANIMAL_IDS } from './data.js';

const $ = (id) => document.getElementById(id);

export function puffyTitle(el, text) {
  el.innerHTML = '';
  [...text].forEach((ch, i) => {
    const s = document.createElement('span');
    s.textContent = ch;
    s.style.color = ch === '《' || ch === '》' ? '#8c6b4b' : TITLE_COLORS[i % TITLE_COLORS.length];
    s.style.animationDelay = `${-(i * 0.17)}s`;
    el.appendChild(s);
  });
}

export class UI {
  constructor() {
    puffyTitle($('title'), TITLE);
    puffyTitle($('titlechip'), '繁忙的动物世界');
    puffyTitle($('celebrate-title'), '探险完成！');
    this.found = new Set();
    this.stickers = {};
    const st = $('stickers');
    for (const id of ANIMAL_IDS) {
      const it = ITEMS.find(i => i.id === id);
      const d = document.createElement('div');
      d.className = 'sticker'; d.textContent = it.emoji; d.title = `${it.cn} ${it.en}`;
      st.appendChild(d); this.stickers[id] = d;
    }
    this.card = $('card');
    this.toastT = null;
    $('help-close').onclick = () => { $('help').hidden = true; };
    $('btn-help').onclick = () => { $('help').hidden = false; };
    $('celebrate-close').onclick = () => { $('celebrate').hidden = true; };
    this.isTouch = matchMedia('(pointer: coarse)').matches;
    if (this.isTouch) $('joy').hidden = false;
  }
  progress(p, text) { $('barfill').style.width = `${Math.round(p * 100)}%`; if (text) $('bartext').textContent = text; }
  ready(onStart) {
    const b = $('start');
    b.disabled = false; $('bartext').textContent = '黏土捏好啦！';
    b.onclick = () => { $('loader').style.transition = 'opacity .6s'; $('loader').style.opacity = '0'; setTimeout(() => { $('loader').hidden = true; }, 600); $('hud').hidden = false; onStart(); };
  }
  showCard(item, handlers) {
    $('card-cn').textContent = item.cn; $('card-py').textContent = item.py; $('card-en').textContent = item.en;
    this.card.hidden = false;
    this.card.style.animation = 'none'; void this.card.offsetWidth; this.card.style.animation = '';
    $('say-en').onclick = handlers.en; $('say-cn').onclick = handlers.cn; $('say-sound').onclick = handlers.sound;
    clearTimeout(this.cardT);
    this.cardT = setTimeout(() => { this.card.hidden = true; }, 9000);
  }
  hideCard() { this.card.hidden = true; }
  setSpeaking(which) { for (const id of ['say-en', 'say-cn', 'say-sound']) $(id).classList.toggle('speaking', id === which); }
  markFound(id) {
    if (this.found.has(id)) return false;
    this.found.add(id);
    const s = this.stickers[id]; if (s) { s.classList.add('found', 'pop'); setTimeout(() => s.classList.remove('pop'), 700); }
    $('bookcount').textContent = `${this.found.size}/${ANIMAL_IDS.length}`;
    return true;
  }
  allFound() { return this.found.size >= ANIMAL_IDS.length; }
  celebrate() { $('celebrate').hidden = false; }
  toast(text, ms = 2600) {
    const t = $('toast'); t.textContent = text; t.hidden = false;
    clearTimeout(this.toastT); this.toastT = setTimeout(() => { t.hidden = true; }, ms);
  }
  setTour(on) { $('btn-tour').classList.toggle('on', on); $('tourbanner').hidden = !on; }
  setOverview(on) { $('btn-view').classList.toggle('on', on); }
  setLabels(on) { $('btn-labels').classList.toggle('on', !on); $('btn-labels').style.opacity = on ? '' : '.75'; }
  setSound(on) { $('btn-sound').textContent = on ? '🔊' : '🔇'; $('btn-sound').classList.toggle('on', !on); }
  // virtual joystick: returns a Vector2-like {x, y} in [-1,1]
  bindJoystick(onMove) {
    const joy = $('joy'), knob = $('joyknob');
    let active = false, cx = 0, cy = 0, pid = null;
    const R = 40;
    const set = (dx, dy) => { const l = Math.hypot(dx, dy) || 1, k = Math.min(1, l / R); const nx = dx / l * k, ny = dy / l * k; knob.style.transform = `translate(${nx * R}px, ${ny * R}px)`; onMove(nx, ny); };
    joy.addEventListener('pointerdown', (e) => { active = true; pid = e.pointerId; const r = joy.getBoundingClientRect(); cx = r.left + r.width / 2; cy = r.top + r.height / 2; set(e.clientX - cx, e.clientY - cy); joy.setPointerCapture(pid); e.stopPropagation(); });
    joy.addEventListener('pointermove', (e) => { if (!active || e.pointerId !== pid) return; set(e.clientX - cx, e.clientY - cy); e.stopPropagation(); });
    const end = (e) => { if (!active) return; active = false; knob.style.transform = ''; onMove(0, 0); };
    joy.addEventListener('pointerup', end); joy.addEventListener('pointercancel', end);
  }
}
