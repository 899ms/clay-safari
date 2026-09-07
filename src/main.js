import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { ITEMS, ANIMAL_IDS, PLAYER_START, RIVER } from './data.js';
import { loadModel } from './clay.js';
import { buildWorld, terrainHeight } from './world.js';
import { Creature } from './animals.js';
import { Player } from './player.js';
import { Effects } from './effects.js';
import { UI } from './ui.js';
import { Tour } from './tour.js';
import { updateTweens, tween, Ease } from './tween.js';
import * as audio from './audio.js';

const isMobile = matchMedia('(pointer: coarse)').matches || innerWidth < 800;
const canvas = document.getElementById('c');
const ui = new UI();

// ------------------------------------------------------------ renderer / scene
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, isMobile ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xdff3ff);
const camera = new THREE.PerspectiveCamera(46, innerWidth / innerHeight, 0.1, 600);
Creature.camera = camera;

let composer = null;
if (!isMobile) {
  const rt = new THREE.WebGLRenderTarget(innerWidth, innerHeight, { samples: 4, type: THREE.HalfFloatType });
  composer = new EffectComposer(renderer, rt);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.26, 0.5, 0.95);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
}

function fitCamera() {
  camera.aspect = (innerWidth || 1280) / (innerHeight || 720);   // hidden/zero-size viewports must not yield NaN
  camera.fov = camera.aspect < 1 ? 64 : camera.aspect < 1.4 ? 54 : 46;   // portrait phones need a wider view
  camera.updateProjectionMatrix();
}
fitCamera();
addEventListener('resize', () => {
  fitCamera();
  renderer.setSize(innerWidth, innerHeight);
  composer && composer.setSize(innerWidth, innerHeight);
});

// ------------------------------------------------------------ build
ui.progress(0.05, '正在铺黏土草地…');
const world = buildWorld(scene, { isMobile });
ui.progress(0.2, '正在捏小动物…');

const creatures = {};
const clickables = [];
let player, robot, effects, tour;

const modelNames = [...ITEMS.map(i => i.id), 'explorer', 'robot'];
let loaded = 0;
const models = {};
await Promise.all(modelNames.map(async (n) => {
  models[n] = await loadModel(n);
  loaded++;
  ui.progress(0.2 + 0.7 * loaded / modelNames.length, `正在捏 ${loaded}/${modelNames.length} 个黏土朋友…`);
}));

effects = new Effects(scene, camera);
ITEMS.forEach((def, i) => {
  const c = new Creature(def, models[def.id], world, i);
  c.events = { ripple: (p, s) => effects.ripple(p, s, 0.35), splash: (p, s) => { effects.splash(p, s); audio.sfx.splash(); }, flash: () => effects.flash() };
  scene.add(c.group);
  creatures[def.id] = c;
  clickables.push(...c.meshes);
});

// robot guide
const robotDef = { id: 'robot', kind: 'guide', cn: '机器人向导', py: 'jī qì rén', en: 'Click me!', emoji: '🤖', pos: [PLAYER_START.x + 2.4, PLAYER_START.z - 1.5], rot: 0.3, scale: 1.0, y: 'ground', r: 0 };
robot = new Creature(robotDef, models.robot, world, 5);
robot.baseY = terrainHeight(robotDef.pos[0], robotDef.pos[1]) + 0.35;
scene.add(robot.group);
clickables.push(...robot.meshes);

player = new Player(models.explorer, world, camera, canvas);
scene.add(player.group);

tour = new Tour({ player, creatures, discover, ui, robot });
ui.progress(1, '黏土捏好啦！');

// ------------------------------------------------------------ discover flow
let speakToken = 0;
async function discover(c, { fromTour = false } = {}) {
  const item = c.def;
  audio.sfx.pop();
  c.react();
  effects.sparkle(c.group.position, 0xffe066, 24, Math.max(1, item.scale));
  if (item.kind === 'guide') { tour.toggle(); return; }
  ui.showCard(item, {
    en: () => sayChain(c, ['en']), cn: () => sayChain(c, ['cn']), sound: () => sayChain(c, ['sound']),
  });
  if (item.kind === 'animal' && ui.markFound(item.id)) {
    effects.hearts(c.group.position);
    audio.sfx.sparkle();
    ui.toast(`✨ 发现新朋友：${item.cn} · ${item.en}`, 2600);
    if (ui.allFound()) {
      setTimeout(() => { effects.confetti(player.group.position, 240); audio.sfx.fanfare(); ui.celebrate(); audio.speak('Congratulations! You found all the animals!', 'en-US'); }, 1200);
    }
  }
  await sayChain(c, ['en', 'sound', 'cn']);
}
async function sayChain(c, steps) {
  const token = ++speakToken;
  const item = c.def;
  for (const s of steps) {
    if (token !== speakToken) break;
    if (s === 'en') { ui.setSpeaking('say-en'); await audio.speak(item.en, 'en-US'); }
    else if (s === 'cn') { ui.setSpeaking('say-cn'); await audio.speak(item.cn, 'zh-CN', { rate: 0.8, pitch: 1.1 }); }
    else if (s === 'sound') { ui.setSpeaking('say-sound'); if (!c.reacting) c.react(); await audio.animalSound(item.id); }
  }
  if (token === speakToken) ui.setSpeaking(null);
}

// ------------------------------------------------------------ input
const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const pointers = new Map();
let downPos = null, dragged = false, pinchDist = 0, lastHover = null, hoverThrottle = 0;
const marker = new THREE.Mesh(new THREE.RingGeometry(0.35, 0.55, 32), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0, depthWrite: false }));
marker.rotation.x = -Math.PI / 2; marker.renderOrder = 4; scene.add(marker);

function setNDC(e) { ndc.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); }
function pickCreature() { ray.setFromCamera(ndc, camera); const hits = ray.intersectObjects(clickables, false); return hits.length ? hits[0].object.userData.creature : null; }
function pickGround() { ray.setFromCamera(ndc, camera); const hits = ray.intersectObjects([world.terrain, world.water], false); return hits.length ? hits[0].point : null; }

canvas.addEventListener('pointerdown', (e) => {
  canvas.setPointerCapture(e.pointerId);
  pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
  if (pointers.size === 1) { downPos = { x: e.clientX, y: e.clientY }; dragged = false; }
  if (pointers.size === 2) { const [a, b] = [...pointers.values()]; pinchDist = Math.hypot(a.x - b.x, a.y - b.y); }
});
canvas.addEventListener('pointermove', (e) => {
  const p = pointers.get(e.pointerId);
  if (p) {
    const dx = e.clientX - p.x, dy = e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    if (pointers.size === 1) {
      if (downPos && Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y) > 6) dragged = true;
      if (dragged) player.orbit(dx, dy);
    } else if (pointers.size === 2) {
      const [a, b] = [...pointers.values()]; const d = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinchDist > 0) player.zoom(pinchDist / d); pinchDist = d; dragged = true;
    }
    return;
  }
  // hover (mouse only)
  if (isMobile) return;
  const now = performance.now(); if (now - hoverThrottle < 40) return; hoverThrottle = now;
  setNDC(e);
  const c = pickCreature();
  if (c !== lastHover) { lastHover && lastHover.setHover(false); lastHover = c; c && c.setHover(true); canvas.style.cursor = c ? 'pointer' : 'grab'; }
});
function endPointer(e) {
  pointers.delete(e.pointerId);
  if (pointers.size === 0 && downPos && !dragged) onTap(e);
  if (pointers.size === 0) downPos = null;
}
canvas.addEventListener('pointerup', endPointer);
canvas.addEventListener('pointercancel', endPointer);
canvas.addEventListener('wheel', (e) => { e.preventDefault(); player.zoom(Math.exp(e.deltaY * 0.0012)); }, { passive: false });
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

function onTap(e) {
  setNDC(e);
  const c = pickCreature();
  if (c) { if (tour.active && c.def.kind !== 'guide') tour.stop(); discover(c); return; }
  const pt = pickGround();
  if (!pt) return;
  if (tour.active) { tour.stop(); ui.toast('导览已停止', 1500); }
  const target = world.nav.nearest(pt.x, pt.z, 6);
  if (!target) return;
  if (player.goTo(target.x, target.z)) {
    marker.position.set(target.x, terrainHeight(target.x, target.z) + 0.08, target.z);
    marker.material.opacity = 0.9; marker.scale.setScalar(1.6);
    tween(marker.material, 'opacity', 0, 1.2, { id: 'mk' }); tween(marker.scale, 'x', 1, 0.5, { id: 'mkx' }); tween(marker.scale, 'y', 1, 0.5, { id: 'mky' });
    audio.sfx.pop();
  } else ui.toast('那里走不到哦～', 1500);
}
player.onInput = () => { if (tour.active) tour.stop(); };

ui.bindJoystick((x, y) => { player.joy.set(x, y); if ((x || y) && tour.active) tour.stop(); });

// ------------------------------------------------------------ buttons & keys
let overview = false;
function setOverview(on) { overview = on; player.setOverview(on); ui.setOverview(on); if (on) ui.toast('🗺️ 俯瞰整个黏土世界 · 再按一次返回', 2200); }
document.getElementById('btn-tour').onclick = () => tour.toggle();
document.getElementById('btn-view').onclick = () => setOverview(!overview);
let soundOn = true;
document.getElementById('btn-sound').onclick = () => { soundOn = !soundOn; audio.setEnabled(soundOn); ui.setSound(soundOn); };
function setLabels(on) {
  Creature.labelsVisible = on; ui.setLabels(on);
  try { localStorage.setItem('clay-safari-labels', on ? '1' : '0'); } catch (e) {}
  ui.toast(on ? '🏷️ 标签已显示' : '🏷️ 标签已隐藏 · 悬停动物仍可查看', 1800);
}
let labelsOn = true;
try { labelsOn = localStorage.getItem('clay-safari-labels') !== '0'; } catch (e) {}
Creature.labelsVisible = labelsOn; ui.setLabels(labelsOn);
document.getElementById('btn-labels').onclick = () => setLabels(!Creature.labelsVisible);
addEventListener('keydown', (e) => {
  if (e.code === 'KeyM') setOverview(!overview);
  if (e.code === 'KeyH') document.getElementById('help').hidden = !document.getElementById('help').hidden;
  if (e.code === 'Escape') { tour.stop(); ui.hideCard(); document.getElementById('help').hidden = true; }
  if (e.code === 'KeyT') tour.toggle();
  if (e.code === 'KeyL') setLabels(!Creature.labelsVisible);
});

// ------------------------------------------------------------ robot companion
const robotTarget = new THREE.Vector3();
function updateRobot(dt, t) {
  const pp = player.pos;
  if (tour.active && player.path) {
    const idx = Math.min(player.pathIdx + 1, player.path.length - 1);
    const wp = player.path[idx];
    robotTarget.set(wp.x, 0, wp.z);
  } else if (tour.active && tour.current) {
    const c = tour.current.group.position;
    robotTarget.set(pp.x + (c.x - pp.x) * 0.35 + 1.5, 0, pp.z + (c.z - pp.z) * 0.35);
  } else {
    const side = player.heading + Math.PI * 0.72;
    robotTarget.set(pp.x + Math.sin(side) * 2.4, 0, pp.z + Math.cos(side) * 2.4);
  }
  const g = robot.group.position;
  const dx = robotTarget.x - g.x, dz = robotTarget.z - g.z, d = Math.hypot(dx, dz);
  const shouldMove = tour.active ? d > 0.3 : d > 3.2;
  if (shouldMove || robot.moving) {
    robot.moving = d > 0.4;
    const sp = Math.min(d, (tour.active ? 8 : 6) * dt);
    g.x += dx / d * sp; g.z += dz / d * sp;
    robot.def.rot = Math.atan2(dx, dz);
  } else robot.def.rot += (Math.atan2(pp.x - g.x, pp.z - g.z) - robot.def.rot) * 0.05;
  robot.baseY = Math.max(terrainHeight(g.x, g.z), RIVER.level + 0.2) + 0.35;
}

// ------------------------------------------------------------ main loop
const clock = new THREE.Clock();
let started = false;
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, clock.getDelta()), t = clock.elapsedTime;
  updateTweens(dt);
  world.update(dt, t);
  if (started) {
    player.update(dt, t);
    for (const id in creatures) creatures[id].update(dt, t);
    updateRobot(dt, t);
    robot.update(dt, t);
    effects.update(dt, t);
    const dRiver = Math.abs(player.pos.x - RIVER.x(player.pos.z));
    audio.setWaterProximity(Math.max(0, 1 - Math.max(0, dRiver - 4) / 10));
  } else {
    // idle poster spin while loading / on the start screen
    camera.position.set(Math.sin(t * 0.05) * 58, 40, Math.cos(t * 0.05) * 58);
    camera.lookAt(0, 0, 0);
    for (const id in creatures) creatures[id].update(dt, t);
    effects.update(dt, t);
  }
  if (composer) composer.render(); else renderer.render(scene, camera);
}
frame();

// debug handle (harmless in production)
window.__game = { player, creatures, robot, tour, world, effects, ui, setOverview, discover, camera, scene, renderer,
  step: (dt = 0.05, n = 1) => { for (let i = 0; i < n; i++) { const t = clock.elapsedTime + dt * (i + 1); updateTweens(dt); world.update(dt, t); player.update(dt, t); for (const id in creatures) creatures[id].update(dt, t); updateRobot(dt, t); robot.update(dt, t); effects.update(dt, t); } } };

ui.ready(() => {
  audio.initAudio();
  audio.startAmbient();
  started = true;
  player.snapCamera();
  setTimeout(() => audio.speak('Welcome to the busy animal world!', 'en-US'), 400);
  setTimeout(() => ui.toast('👆 点击动物听声音 · 点击 🤖 开始导览', 3500), 1500);
});
