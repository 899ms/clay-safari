// World layout. Coordinates are Three.js world units: x right, z toward the
// default camera (the "bottom" of the reference poster), y up.

export const MAP = { w: 84, h: 60 };          // x ∈ [-42, 42], z ∈ [-30, 30]
export const WALK = { x: 36, z: 25 };         // walkable extent

// river centre line x = A·sin(B·z + C)  (kept as numbers so the water shader can share it)
export const RIVER = {
  A: 3, B: 0.11, C: 0.6,
  halfWidth: 3.4,
  level: -0.45,
  x: (z) => 3 * Math.sin(0.11 * z + 0.6),
};

export const BRIDGE = { z: -2, halfLen: 5.4, halfW: 1.7, rise: 0.62, base: 0.12 };
BRIDGE.x = RIVER.x(BRIDGE.z);

export const PLAYER_START = { x: -24, z: 20, rot: Math.PI };

export const TITLE = '《繁忙的动物世界 双语认知大发现》';
export const TITLE_COLORS = ['#ff6b6b', '#ff9f43', '#feca57', '#8ee68a', '#48dbfb', '#5f8bff', '#c58bff', '#ff6b9d'];

// kind: 'animal' counts toward the sticker book; 'prop' is just a word to learn.
// y: 'ground' | 'water' | number ; viewFrom: where the tour stands to look at it.
export const ITEMS = [
  { id: 'snake',     kind: 'animal', cn: '蛇',     py: 'shé',            en: 'Snake',      emoji: '🐍', pos: [-31, 12],  rot: 0.9,  scale: 1.6, y: 'ground', r: 1.4, viewFrom: [-28, 15] },
  { id: 'lion',      kind: 'animal', cn: '狮子',   py: 'shī zi',         en: 'Lion',       emoji: '🦁', pos: [-27, -2],  rot: 0.7,  scale: 1.6, y: 'rock',   r: 0,   viewFrom: [-22.5, 2] },
  { id: 'flower',    kind: 'prop',   cn: '花朵',   py: 'huā duǒ',        en: 'Flower',     emoji: '🌸', pos: [-22, 15],  rot: 0.3,  scale: 1.5, y: 'ground', r: 0.9, viewFrom: [-20, 17.5] },
  { id: 'giraffe',   kind: 'animal', cn: '长颈鹿', py: 'cháng jǐng lù',  en: 'Giraffe',    emoji: '🦒', pos: [-13, -12], rot: 0.5,  scale: 1.3, y: 'ground', r: 1.6, viewFrom: [-10.5, -8.5] },
  { id: 'bird',      kind: 'animal', cn: '小鸟',   py: 'xiǎo niǎo',      en: 'Bird',       emoji: '🐦', pos: [-17.6, -6], rot: 0.6, scale: 1.4, y: 3.05,     r: 0,   viewFrom: [-15.5, -3.5], perchTree: [-19.5, -6] },
  { id: 'bone',      kind: 'prop',   cn: '骨头',   py: 'gǔ tou',         en: 'Bone',       emoji: '🦴', pos: [-11, 6],   rot: 0.4,  scale: 1.5, y: 'ground', r: 0.8, viewFrom: [-9, 8] },
  { id: 'zebra',     kind: 'animal', cn: '斑马',   py: 'bān mǎ',         en: 'Zebra',      emoji: '🦓', pos: [-6, -4],   rot: 1.0,  scale: 1.5, y: 'ground', r: 1.5, viewFrom: [-3.2, -1] },
  { id: 'hippo',     kind: 'animal', cn: '河马',   py: 'hé mǎ',          en: 'Hippo',      emoji: '🦛', pos: [3.0, 9],   rot: -0.6, scale: 1.7, y: 'water',  r: 0,   viewFrom: [8.2, 8] },
  { id: 'fish',      kind: 'animal', cn: '鱼',     py: 'yú',             en: 'Fish',       emoji: '🐟', pos: [1.9, 17],  rot: 0,    scale: 1.6, y: 'water',  r: 0,   viewFrom: [7.2, 16], swim: [12, 22] },
  { id: 'crocodile', kind: 'animal', cn: '鳄鱼',   py: 'è yú',           en: 'Crocodile',  emoji: '🐊', pos: [11, 13],   rot: -1.9, scale: 1.4, y: 'ground', r: 1.8, viewFrom: [11, 17.2] },
  { id: 'stump',     kind: 'prop',   cn: '树桩',   py: 'shù zhuāng',     en: 'Tree Stump', emoji: '🪵', pos: [19, 12],   rot: 0.2,  scale: 1.5, y: 'ground', r: 1.2, viewFrom: [17, 14.5] },
  { id: 'elephant',  kind: 'animal', cn: '大象',   py: 'dà xiàng',       en: 'Elephant',   emoji: '🐘', pos: [15, -11],  rot: -0.7, scale: 1.6, y: 'ground', r: 2.2, viewFrom: [12, -7.5] },
  { id: 'monkey',    kind: 'animal', cn: '猴子',   py: 'hóu zi',         en: 'Monkey',     emoji: '🐵', pos: [24.4, -16], rot: -0.9, scale: 1.2, y: 2.55,   r: 0,   viewFrom: [22, -12.5], perchTree: [27, -16] },
  { id: 'banana',    kind: 'prop',   cn: '香蕉',   py: 'xiāng jiāo',     en: 'Banana',     emoji: '🍌', pos: [21, -6],   rot: 0.8,  scale: 1.6, y: 'ground', r: 0.8, viewFrom: [19, -3.5] },
  { id: 'truck',     kind: 'prop',   cn: '探险车', py: 'tàn xiǎn chē',   en: 'Safari Truck', emoji: '🚙', pos: [29, 3],  rot: -2.4, scale: 1.8, y: 'ground', r: 2.8, viewFrom: [24.5, 4.5] },
  { id: 'camera',    kind: 'prop',   cn: '照相机', py: 'zhào xiàng jī',  en: 'Camera',     emoji: '📷', pos: [14, 20],   rot: -0.4, scale: 1.3, y: 'ground', r: 0.8, viewFrom: [12, 17.5] },
  { id: 'binoculars', kind: 'prop',  cn: '望远镜', py: 'wàng yuǎn jìng', en: 'Binoculars', emoji: '🔭', pos: [24, 20],   rot: 0.5,  scale: 1.3, y: 'ground', r: 0.8, viewFrom: [22, 17.5] },
];

export const ANIMAL_IDS = ITEMS.filter(i => i.kind === 'animal').map(i => i.id);

// Auto-tour order (the exploration route). Crosses the bridge between zebra and hippo.
export const ROUTE = ['snake', 'lion', 'flower', 'giraffe', 'bird', 'bone', 'zebra', 'hippo', 'fish', 'crocodile', 'stump', 'elephant', 'monkey', 'banana', 'truck', 'camera', 'binoculars'];

// Path painted onto the terrain (light sand), roughly following the route.
export const PATH_POINTS = [
  [-24, 21], [-28, 15], [-26, 6], [-23, 1], [-21, -3], [-16, -8], [-11, -8], [-10, -2], [-9, 5], [-6, 2], [-3, -2],
  [BRIDGE.x, BRIDGE.z], [7, -2], [8, 4], [7.5, 9], [8, 15], [12, 18], [17, 15], [18, 8], [14, 1], [12, -6],
  [17, -10], [22, -13], [24.5, -9], [20, -4], [24, 1], [27, 7], [24, 13], [20, 17], [23, 18],
];

// Trees that carry a perch (bird / monkey) are placed exactly; everything else is scattered.
export const SPECIAL_TREES = [
  { pos: [-19.5, -6], type: 'perch', branchDir: 1, branchH: 3.0, branchLen: 2.4, scale: 1.25 },
  { pos: [27, -16],   type: 'perch', branchDir: -1, branchH: 2.5, branchLen: 3.2, scale: 1.7 },
];
