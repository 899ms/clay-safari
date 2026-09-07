# -*- coding: utf-8 -*-
"""
Clay Safari — procedural clay animals for the web.
Run:  Blender -b -P blender/build_animals.py -- public/models
Every model is built from spheres / capsules / bezier tubes, shaded smooth,
grouped under one root Empty and exported as its own GLB with named parts
(head, tail, trunk, jaw, wingL ...) so Three.js can animate them.

Convention: Blender Z-up, animal faces -Y (Blender "front").  glTF export is
Y-up, so the animal faces +Z in Three.js.  Origin sits on the ground (z=0).
"""
import bpy, bmesh, math, os, random, sys
from mathutils import Vector, Euler

argv = sys.argv
OUT = argv[argv.index('--') + 1] if '--' in argv else 'public/models'
os.makedirs(OUT, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# ----------------------------------------------------------------- helpers
def hex2lin(h):
    h = h.lstrip('#')
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    s2l = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (s2l(r), s2l(g), s2l(b), 1.0)

MATS = {}
def mat(color, rough=0.85, emit=0.0):
    key = (color, rough, emit)
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new('clay_%s' % color.lstrip('#'))
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = hex2lin(color)
    b.inputs['Roughness'].default_value = rough
    if emit > 0:
        b.inputs['Emission Color'].default_value = hex2lin(color)
        b.inputs['Emission Strength'].default_value = emit
    MATS[key] = m
    return m

def deselect():
    for ob in bpy.context.selected_objects:
        ob.select_set(False)

def rad(t):
    return tuple(math.radians(a) for a in t)

def _finish(o, name, m, parent, smooth=True):
    o.name = name
    if m is not None:
        o.data.materials.append(m)
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if parent is not None:
        o.parent = parent
    return o

def subsurf(o, lv):
    if lv > 0:
        mod = o.modifiers.new('sub', 'SUBSURF')
        mod.levels = lv
        mod.render_levels = lv

def empty(name, parent=None, loc=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    if parent is not None:
        o.parent = parent
    if loc is not None:
        o.location = loc
    return o

def pivot(e, point):
    """Move an Empty's origin to `point` while keeping every child where it is
    (children were authored in absolute coords).  glTF bakes matrix_parent_inverse
    into child transforms, so Three.js gets parent at `point`, children relative."""
    from mathutils import Matrix
    e.location = Vector(point)
    inv = Matrix.Translation(-Vector(point))
    for c in e.children:
        c.matrix_parent_inverse = inv

def sphere(name, loc, scale, m, parent, rot=(0, 0, 0), seg=24, rings=12):
    r = rot if isinstance(rot, Euler) else rad(rot)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=1, location=loc, rotation=r)
    o = bpy.context.active_object
    o.scale = scale if isinstance(scale, (tuple, list)) else (scale, scale, scale)
    return _finish(o, name, m, parent)

def limb(name, p0, p1, r, m, parent, r1=None, sub=2):
    """capsule-ish limb from p0 to p1 (radius r at p0, r1 at p1)"""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if r1 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=L, location=(p0 + p1) / 2)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r, radius2=r1, depth=L, location=(p0 + p1) / 2)
    o = bpy.context.active_object
    o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    subsurf(o, sub)
    return _finish(o, name, m, parent)

def cyl(name, loc, r, h, m, parent, rot=(0, 0, 0), sub=1, verts=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=loc, rotation=rad(rot))
    o = bpy.context.active_object
    subsurf(o, sub)
    return _finish(o, name, m, parent)

def cone(name, loc, r1, r2, h, m, parent, rot=(0, 0, 0), sub=1):
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=r1, radius2=r2, depth=h, location=loc, rotation=rad(rot))
    o = bpy.context.active_object
    subsurf(o, sub)
    return _finish(o, name, m, parent)

def ring(name, loc, R, r, m, parent, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=32, minor_segments=10,
                                     location=loc, rotation=rad(rot))
    o = bpy.context.active_object
    o.scale = scale
    return _finish(o, name, m, parent)

def mark_sharp(o, angle_deg=40):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    th = math.radians(angle_deg)
    for e in bm.edges:
        if len(e.link_faces) == 2 and e.calc_face_angle(0) > th:
            e.smooth = False
    bm.to_mesh(o.data)
    bm.free()

def rbox(name, loc, half, m, parent, bevel=0.06, rot=(0, 0, 0), sharp=True):
    """rounded box; half = half extents"""
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc, rotation=rad(rot))
    o = bpy.context.active_object
    o.scale = half
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = o.modifiers.new('bev', 'BEVEL')
    mod.width = min(bevel, min(half) * 0.9)
    mod.segments = 4
    bpy.ops.object.modifier_apply(modifier='bev')
    if sharp:
        mark_sharp(o, 40)
    return _finish(o, name, m, parent)

def tube(name, pts, r, m, parent, radii=None, res=12, caps=True, bevel_res=6, cyclic=False):
    cu = bpy.data.curves.new(name + '_cu', 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
        bp.radius = radii[i] if radii else 1.0
    sp.use_cyclic_u = cyclic
    cu.bevel_depth = r
    cu.bevel_resolution = bevel_res
    cu.resolution_u = res
    cu.use_fill_caps = caps
    o = bpy.data.objects.new(name, cu)
    bpy.context.collection.objects.link(o)
    deselect()
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o = bpy.context.active_object
    return _finish(o, name, m, parent)

def spots(parent, center, scale, n, r, m, seed=1, zmin=-0.3, flat=0.35, ymax=1.0):
    """flattened spots sitting on an ellipsoid surface, oriented along the normal"""
    rng = random.Random(seed)
    c, s = Vector(center), Vector(scale)
    made = 0
    guard = 0
    while made < n and guard < 400:
        guard += 1
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(zmin, 1)))
        if not (0.3 < d.length <= 1.0):
            continue
        d.normalize()
        if d.y > ymax:
            continue
        pos = c + Vector((d.x * s.x, d.y * s.y, d.z * s.z))
        nrm = Vector((d.x / s.x, d.y / s.y, d.z / s.z)).normalized()
        rot = nrm.to_track_quat('Z', 'Y').to_euler()
        sphere('spot%d' % made, pos, (r, r, r * flat), m, parent, rot=rot, seg=16, rings=8)
        made += 1

# shared cute-face bits ------------------------------------------------------
BLACK = mat('#2B2622', 0.6)
WHITE = mat('#FFFFFF', 0.5)
PINK = mat('#F7A8A8', 0.9)
CREAM = mat('#FFF3D6', 0.9)

def eyes(parent, x, y, z, r=0.06, white=False, wr=None):
    for s in (-1, 1):
        if white:
            sphere('eyewhite%d' % s, (s * x, y + r * 0.3, z), wr or r * 1.5, WHITE, parent, seg=16, rings=8)
        sphere('eye%d' % s, (s * x, y, z), r, BLACK, parent, seg=16, rings=8)
        sphere('glint%d' % s, (s * x - s * r * 0.3, y - r * 0.7, z + r * 0.4), r * 0.35, WHITE, parent, seg=10, rings=6)

def cheeks(parent, x, y, z, r=0.07):
    for s in (-1, 1):
        sphere('cheek%d' % s, (s * x, y, z), (r, r * 0.5, r * 0.7), PINK, parent, seg=16, rings=8)

def smile(parent, x, y, z, w=0.08, drop=0.04, r=0.012, m=None):
    tube('smile', [(-w, y, z), (0, y - 0.01, z - drop), (w, y, z)], r, m or BLACK, parent, res=8, bevel_res=4)

# ----------------------------------------------------------------- animals
def build_lion():
    root = empty('lion')
    body = mat('#F2B44C'); mane = mat('#D4802E'); snout = mat('#FBE0AE'); dark = mat('#5B3A29')
    sphere('body', (0, 0.18, 0.55), (0.46, 0.62, 0.42), body, root)
    sphere('belly', (0, -0.05, 0.42), (0.34, 0.42, 0.28), snout, root)
    # legs
    for i, (x, y) in enumerate([(-0.26, -0.22), (0.26, -0.22), (-0.3, 0.5), (0.3, 0.5)]):
        limb('leg%d' % i, (x, y, 0.5), (x, y, 0.1), 0.13, body, root)
        sphere('paw%d' % i, (x, y - 0.03, 0.12), (0.15, 0.17, 0.11), body, root)
    head = empty('head'); head.parent = root
    sphere('mane', (0, -0.3, 0.98), (0.66, 0.36, 0.66), mane, head)
    for i in range(12):
        a = i / 12 * math.tau
        sphere('manebump%d' % i, (math.cos(a) * 0.6, -0.36, 0.98 + math.sin(a) * 0.6), 0.18, mane, head, seg=16, rings=8)
    sphere('face', (0, -0.5, 0.98), 0.42, body, head)
    for s in (-1, 1):
        sphere('ear%d' % s, (s * 0.32, -0.42, 1.32), 0.12, body, head, seg=16, rings=8)
        sphere('earin%d' % s, (s * 0.32, -0.5, 1.32), 0.07, PINK, head, seg=12, rings=6)
    sphere('muzzle', (0, -0.86, 0.88), (0.24, 0.14, 0.17), snout, head)
    sphere('nose', (0, -0.98, 0.95), (0.07, 0.05, 0.05), dark, head, seg=12, rings=6)
    eyes(head, 0.17, -0.86, 1.06, 0.06)
    cheeks(head, 0.3, -0.8, 0.92, 0.08)
    smile(head, 0, -0.99, 0.84, 0.06, 0.03)
    tail = empty('tail', root)
    tube('tailmesh', [(0.1, 0.72, 0.62), (0.3, 1.02, 0.5), (0.5, 1.16, 0.78)], 0.045, body, tail, radii=[1, 0.9, 0.8])
    sphere('tailtuft', (0.52, 1.18, 0.84), 0.1, mane, tail, seg=16, rings=8)
    pivot(tail, (0.1, 0.72, 0.62)); pivot(head, (0, -0.3, 0.85))
    return root

def build_giraffe():
    root = empty('giraffe')
    body = mat('#F5C45E'); spot = mat('#C97A3A'); cream = mat('#FFEFC2'); dark = mat('#7A4B24')
    sphere('body', (0, 0.1, 1.05), (0.38, 0.56, 0.4), body, root)
    spots(root, (0, 0.1, 1.05), (0.38, 0.56, 0.4), 18, 0.11, spot, seed=3, zmin=-0.2)
    for i, (x, y) in enumerate([(-0.2, -0.25), (0.2, -0.25), (-0.22, 0.42), (0.22, 0.42)]):
        limb('leg%d' % i, (x, y, 0.95), (x, y, 0.12), 0.1, body, root, r1=0.085)
        sphere('hoof%d' % i, (x, y, 0.1), (0.1, 0.11, 0.09), dark, root, seg=16, rings=8)
    head = empty('head'); head.parent = root
    tube('neck', [(0, -0.3, 1.2), (0, -0.5, 1.75), (0, -0.62, 2.3)], 0.17, body, head, radii=[1.1, 0.95, 0.8])
    for i in range(6):
        t = i / 5
        sphere('mane%d' % i, (0, -0.3 - 0.32 * t + 0.16, 1.3 + 1.0 * t), 0.06, spot, head, seg=12, rings=6)
    for i in range(4):
        sphere('neckspot%d' % i, (0.14 if i % 2 else -0.14, -0.38 - i * 0.07, 1.45 + i * 0.22), (0.07, 0.07, 0.03), spot, head,
               rot=(0, 90 if i % 2 else -90, 0), seg=12, rings=6)
    sphere('skull', (0, -0.75, 2.46), (0.27, 0.36, 0.26), body, head)
    sphere('muzzle', (0, -1.04, 2.38), (0.2, 0.17, 0.15), cream, head)
    for s in (-1, 1):
        sphere('nostril%d' % s, (s * 0.07, -1.2, 2.42), 0.025, dark, head, seg=10, rings=6)
        tube('ossicone%d' % s, [(s * 0.1, -0.68, 2.66), (s * 0.12, -0.66, 2.9)], 0.035, body, head)
        sphere('ossitip%d' % s, (s * 0.12, -0.66, 2.92), 0.06, dark, head, seg=12, rings=6)
        sphere('ear%d' % s, (s * 0.3, -0.62, 2.6), (0.13, 0.05, 0.08), body, head, rot=(0, s * 20, 0), seg=16, rings=8)
    eyes(head, 0.2, -0.93, 2.52, 0.05)
    cheeks(head, 0.24, -0.98, 2.42, 0.06)
    smile(head, 0, -1.2, 2.31, 0.05, 0.025)
    tail = empty('tail', root)
    tube('tailmesh', [(0, 0.66, 1.15), (0.05, 0.85, 0.9), (0.15, 0.9, 0.65)], 0.035, body, tail, radii=[1, 0.8, 0.6])
    sphere('tailtuft', (0.17, 0.9, 0.6), (0.06, 0.06, 0.1), dark, tail, seg=12, rings=6)
    pivot(tail, (0, 0.66, 1.15)); pivot(head, (0, -0.3, 1.2))
    return root

def build_zebra():
    root = empty('zebra')
    body = mat('#F6F1E6'); stripe = mat('#3B3735'); dark = mat('#2B2622')
    B = (0.36, 0.56, 0.36)
    sphere('body', (0, 0.1, 0.72), B, body, root)
    # stripes: torus bands following the body cross-section
    for i, y in enumerate([-0.36, -0.2, -0.04, 0.12, 0.28, 0.44]):
        f = math.sqrt(max(0.0, 1 - (y / B[1]) ** 2))
        ring('stripe%d' % i, (0, 0.1 + y, 0.72), 1.0, 0.035, stripe, root, rot=(90, 0, 0), scale=(B[0] * f + 0.01, B[2] * f + 0.01, 1))
    for i, (x, y) in enumerate([(-0.2, -0.28), (0.2, -0.28), (-0.22, 0.42), (0.22, 0.42)]):
        limb('leg%d' % i, (x, y, 0.62), (x, y, 0.1), 0.09, body, root, r1=0.08)
        for j, z in enumerate((0.42, 0.26)):
            ring('legstripe%d_%d' % (i, j), (x, y, z), 0.095, 0.022, stripe, root)
        sphere('hoof%d' % i, (x, y, 0.09), (0.095, 0.1, 0.08), dark, root, seg=16, rings=8)
    head = empty('head'); head.parent = root
    tube('neck', [(0, -0.36, 0.86), (0, -0.55, 1.18)], 0.16, body, head, radii=[1.05, 0.9])
    for i in range(3):
        t = 0.2 + i * 0.3
        ring('neckstripe%d' % i, (0, -0.36 - 0.19 * t, 0.86 + 0.32 * t), 0.17, 0.028, stripe, head, rot=(-32, 0, 0))
    for i in range(6):
        t = i / 5
        sphere('mane%d' % i, (0, -0.28 - 0.3 * t, 1.0 + 0.3 * t), (0.05, 0.07, 0.09), stripe, head, seg=12, rings=6)
    sphere('skull', (0, -0.76, 1.24), (0.23, 0.33, 0.23), body, head)
    ring('headstripe', (0, -0.72, 1.24), 1.0, 0.03, stripe, head, rot=(90, 0, 0), scale=(0.235, 0.235, 1))
    sphere('muzzle', (0, -1.02, 1.14), (0.17, 0.16, 0.14), dark, head)
    for s in (-1, 1):
        sphere('ear%d' % s, (s * 0.15, -0.62, 1.46), (0.07, 0.05, 0.12), body, head, rot=(0, s * 15, 0), seg=16, rings=8)
        sphere('earin%d' % s, (s * 0.15, -0.66, 1.46), (0.04, 0.03, 0.08), PINK, head, seg=12, rings=6)
        sphere('nostril%d' % s, (s * 0.06, -1.17, 1.17), 0.025, body, head, seg=10, rings=6)
    eyes(head, 0.17, -0.92, 1.3, 0.05)
    cheeks(head, 0.2, -0.96, 1.2, 0.06)
    tail = empty('tail', root)
    tube('tailmesh', [(0, 0.64, 0.8), (0.03, 0.8, 0.6), (0.08, 0.86, 0.4)], 0.035, body, tail, radii=[1, 0.8, 0.6])
    sphere('tailtuft', (0.09, 0.87, 0.36), (0.06, 0.06, 0.1), stripe, tail, seg=12, rings=6)
    pivot(tail, (0, 0.64, 0.8)); pivot(head, (0, -0.36, 0.86))
    return root

def build_elephant():
    root = empty('elephant')
    body = mat('#9BA5B4'); light = mat('#B7BFCB'); tusk = mat('#FFF7E0'); nail = mat('#E9E4D8')
    sphere('body', (0, 0.12, 0.9), (0.64, 0.82, 0.62), body, root)
    for i, (x, y) in enumerate([(-0.34, -0.3), (0.34, -0.3), (-0.36, 0.5), (0.36, 0.5)]):
        limb('leg%d' % i, (x, y, 0.75), (x, y, 0.1), 0.2, body, root)
        for j in range(3):
            a = (j - 1) * 0.55
            sphere('nail%d_%d' % (i, j), (x + math.sin(a) * 0.16, y - math.cos(a) * 0.16, 0.08), (0.05, 0.04, 0.045), nail, root, seg=10, rings=6)
    head = empty('head'); head.parent = root
    sphere('skull', (0, -0.72, 1.32), (0.52, 0.48, 0.5), body, head)
    for s in (-1, 1):
        ear = empty('ear%s' % ('L' if s < 0 else 'R'), head)
        sphere('earmesh%d' % s, (s * 0.66, -0.55, 1.36), (0.3, 0.09, 0.38), body, ear, rot=(0, s * -12, 0))
        sphere('earin%d' % s, (s * 0.66, -0.62, 1.36), (0.21, 0.06, 0.28), PINK, ear, rot=(0, s * -12, 0))
        pivot(ear, (s * 0.42, -0.55, 1.36))
        tube('tusk%d' % s, [(s * 0.24, -1.1, 1.02), (s * 0.3, -1.34, 0.9), (s * 0.3, -1.46, 1.0)], 0.05, tusk, head, radii=[1, 0.85, 0.6])
    trunk = empty('trunk', head)
    tube('trunkmesh', [(0, -1.12, 1.16), (0, -1.38, 0.8), (0, -1.48, 0.42), (0, -1.36, 0.22)], 0.14, body, trunk, radii=[1.05, 0.85, 0.7, 0.62])
    pivot(trunk, (0, -1.1, 1.16))
    eyes(head, 0.23, -1.16, 1.4, 0.06)
    cheeks(head, 0.36, -1.08, 1.24, 0.09)
    tail = empty('tail', root)
    tube('tailmesh', [(0, 0.9, 0.95), (0.05, 1.05, 0.7), (0.1, 1.08, 0.5)], 0.04, body, tail, radii=[1, 0.8, 0.6])
    sphere('tailtuft', (0.11, 1.09, 0.45), (0.05, 0.05, 0.09), light, tail, seg=12, rings=6)
    pivot(tail, (0, 0.9, 0.95)); pivot(head, (0, -0.55, 1.15))
    return root

def build_monkey():
    root = empty('monkey')
    fur = mat('#A5643C'); face = mat('#F5D9B4'); banana = mat('#FFD84D'); btip = mat('#7A5A2A')
    sphere('body', (0, 0, 0.56), (0.28, 0.25, 0.32), fur, root)
    sphere('belly', (0, -0.18, 0.52), (0.18, 0.1, 0.22), face, root)
    head = empty('head'); head.parent = root
    sphere('skull', (0, -0.04, 1.02), 0.33, fur, head)
    for s in (-1, 1):
        sphere('facepatch%d' % s, (s * 0.1, -0.29, 1.06), (0.16, 0.1, 0.15), face, head)
        sphere('ear%d' % s, (s * 0.35, -0.02, 1.04), 0.12, fur, head, seg=16, rings=8)
        sphere('earin%d' % s, (s * 0.37, -0.08, 1.04), 0.07, face, head, seg=12, rings=6)
    sphere('muzzle', (0, -0.31, 0.94), (0.2, 0.1, 0.15), face, head)
    sphere('nose', (0, -0.42, 0.97), (0.035, 0.03, 0.025), BLACK, head, seg=10, rings=6)
    eyes(head, 0.1, -0.38, 1.08, 0.05)
    cheeks(head, 0.2, -0.36, 0.98, 0.06)
    smile(head, 0, -0.42, 0.9, 0.06, 0.03)
    tube('armL', [(-0.26, 0, 0.74), (-0.42, -0.1, 0.55), (-0.36, -0.32, 0.42)], 0.07, fur, root)
    sphere('handL', (-0.35, -0.36, 0.4), 0.08, face, root, seg=12, rings=6)
    armR = empty('armR', root)
    tube('armRmesh', [(0.26, 0, 0.74), (0.46, -0.05, 0.96), (0.42, -0.18, 1.22)], 0.07, fur, armR)
    sphere('handR', (0.42, -0.2, 1.26), 0.08, face, armR, seg=12, rings=6)
    tube('banana', [(0.3, -0.24, 1.46), (0.45, -0.28, 1.36), (0.56, -0.24, 1.42)], 0.05, banana, armR, radii=[0.6, 1, 0.6])
    sphere('btip', (0.29, -0.24, 1.47), 0.03, btip, armR, seg=10, rings=6)
    pivot(armR, (0.26, 0, 0.74))
    for s in (-1, 1):
        tube('leg%d' % s, [(s * 0.16, 0, 0.36), (s * 0.24, -0.14, 0.16), (s * 0.22, -0.3, 0.09)], 0.07, fur, root)
        sphere('foot%d' % s, (s * 0.22, -0.32, 0.08), (0.08, 0.1, 0.06), face, root, seg=12, rings=6)
    tail = empty('tail', root)
    tube('tailmesh', [(0, 0.24, 0.5), (0, 0.52, 0.28), (0.14, 0.72, 0.6), (0.02, 0.6, 0.95)], 0.045, fur, tail, radii=[1, 0.9, 0.8, 0.6])
    pivot(tail, (0, 0.24, 0.5)); pivot(head, (0, -0.04, 0.8))
    return root

def build_hippo():
    root = empty('hippo')
    body = mat('#B39EE0'); light = mat('#CDBDEE'); tooth = mat('#FFFFFF', 0.4)
    sphere('body', (0, 0.15, 0.6), (0.56, 0.72, 0.46), body, root)
    for i, (x, y) in enumerate([(-0.32, -0.28), (0.32, -0.28), (-0.34, 0.55), (0.34, 0.55)]):
        limb('leg%d' % i, (x, y, 0.45), (x, y, 0.1), 0.16, body, root)
        sphere('foot%d' % i, (x, y - 0.02, 0.1), (0.18, 0.2, 0.1), light, root)
    head = empty('head'); head.parent = root
    sphere('skull', (0, -0.62, 0.74), (0.46, 0.42, 0.4), body, head)
    sphere('muzzle', (0, -1.0, 0.58), (0.44, 0.34, 0.32), light, head)
    for s in (-1, 1):
        sphere('nostril%d' % s, (s * 0.14, -1.32, 0.72), 0.045, mat('#7B69A8'), head, seg=12, rings=6)
        sphere('ear%d' % s, (s * 0.34, -0.5, 1.08), 0.09, body, head, seg=16, rings=8)
        sphere('earin%d' % s, (s * 0.35, -0.55, 1.08), 0.05, PINK, head, seg=12, rings=6)
        rbox('tooth%d' % s, (s * 0.17, -1.3, 0.4), (0.045, 0.035, 0.06), tooth, head, bevel=0.02, sharp=False)
    eyes(head, 0.25, -0.86, 1.04, 0.055, white=True, wr=0.085)
    cheeks(head, 0.4, -0.85, 0.8, 0.09)
    smile(head, 0, -1.34, 0.52, 0.16, 0.05, 0.015, mat('#7B69A8'))
    tail = empty('tail', root)
    tube('tailmesh', [(0, 0.85, 0.7), (0.04, 0.96, 0.55)], 0.03, body, tail)
    sphere('tailtuft', (0.05, 0.98, 0.5), (0.04, 0.04, 0.07), light, tail, seg=10, rings=6)
    pivot(tail, (0, 0.85, 0.7)); pivot(head, (0, -0.4, 0.72))
    return root

def build_crocodile():
    root = empty('crocodile')
    skin = mat('#6FBF5A'); belly = mat('#CBE59D'); ridge = mat('#4F9E3F'); tooth = mat('#FFFFFF', 0.4)
    sphere('body', (0, 0.25, 0.34), (0.42, 0.92, 0.3), skin, root)
    sphere('belly', (0, 0.25, 0.22), (0.38, 0.86, 0.2), belly, root)
    for i in range(7):
        y = -0.4 + i * 0.28
        for s in (-1, 1):
            sphere('ridge%d_%d' % (i, s), (s * 0.13, y, 0.6 - abs(y - 0.25) * 0.12), 0.065, ridge, root, seg=12, rings=6)
    head = empty('head'); head.parent = root
    sphere('skull', (0, -0.9, 0.36), (0.34, 0.42, 0.24), skin, head)
    sphere('snout', (0, -1.38, 0.3), (0.27, 0.46, 0.14), skin, head)
    jaw = empty('jaw'); jaw.parent = head; jaw.location = (0, -0.95, 0.22)
    sphere('lowerjaw', (0, -0.36, -0.02), (0.25, 0.44, 0.09), belly, jaw)
    for i in range(5):
        y = -1.15 - i * 0.14
        for s in (-1, 1):
            sphere('tooth%d_%d' % (i, s), (s * 0.22, y, 0.2), (0.03, 0.03, 0.05), tooth, head, seg=8, rings=5)
    for s in (-1, 1):
        sphere('eyebump%d' % s, (s * 0.2, -0.95, 0.56), 0.11, skin, head, seg=16, rings=8)
        sphere('eyewhite%d' % s, (s * 0.2, -1.02, 0.6), 0.075, WHITE, head, seg=12, rings=6)
        sphere('eye%d' % s, (s * 0.2, -1.07, 0.61), 0.045, BLACK, head, seg=12, rings=6)
        sphere('nostril%d' % s, (s * 0.09, -1.8, 0.4), 0.03, ridge, head, seg=10, rings=6)
    cheeks(head, 0.28, -1.1, 0.42, 0.06)
    tail = empty('tail', root)
    tube('tailmesh', [(0, 1.05, 0.34), (0, 1.6, 0.3), (0.25, 2.1, 0.24), (0.6, 2.42, 0.18)], 0.28, skin, tail, radii=[1, 0.75, 0.5, 0.25])
    for i in range(4):
        t = i / 4
        sphere('tailridge%d' % i, (0.06 * i * i * 0.2, 1.15 + t * 1.0, 0.6 - t * 0.24), 0.05 - t * 0.012, ridge, tail, seg=10, rings=6)
    pivot(tail, (0, 1.0, 0.34))
    for i, (x, y) in enumerate([(-0.36, -0.45), (0.36, -0.45), (-0.36, 0.75), (0.36, 0.75)]):
        s = -1 if x < 0 else 1
        tube('leg%d' % i, [(x, y, 0.3), (x + s * 0.2, y - 0.05, 0.16), (x + s * 0.24, y - 0.12, 0.06)], 0.09, skin, root)
        sphere('foot%d' % i, (x + s * 0.26, y - 0.18, 0.05), (0.11, 0.14, 0.05), skin, root, seg=12, rings=6)
    pivot(head, (0, -0.6, 0.36))
    return root

def build_snake():
    root = empty('snake')
    skin = mat('#7DC950'); pat = mat('#F0E86A'); tongue = mat('#E2504C', 0.7)
    pts, radii = [], []
    n = 34
    for i in range(n):
        t = i / (n - 1)
        a = t * math.tau * 2.4
        rr = 0.42 - 0.2 * t
        pts.append((math.cos(a) * rr, math.sin(a) * rr, 0.1 + 0.36 * t * t))
        radii.append(0.45 + 0.55 * min(1, (1 - t) * 3) if t > 0.9 else (0.55 + 0.45 * min(1, t * 4)))
    tube('body', pts, 0.1, skin, root, radii=radii, res=6)
    for i in range(0, n - 4, 3):
        p = pts[i]
        sphere('pat%d' % i, (p[0], p[1], p[2] + 0.085), (0.05, 0.05, 0.02), pat, root, seg=10, rings=6)
    head = empty('head'); head.parent = root
    hx, hy, hz = pts[-1][0], pts[-1][1], pts[-1][2]
    ang = math.atan2(hy - pts[-3][1], hx - pts[-3][0])
    dirv = Vector((math.cos(ang), math.sin(ang), 0))
    hp = Vector((hx, hy, hz + 0.05)) + dirv * 0.12
    sphere('skull', hp, (0.15, 0.15, 0.12), skin, head, rot=(0, 0, math.degrees(ang)))
    side = Vector((-dirv.y, dirv.x, 0))
    for s in (-1, 1):
        ep = hp + dirv * 0.08 + side * s * 0.09 + Vector((0, 0, 0.05))
        sphere('eyewhite%d' % s, ep, 0.045, WHITE, head, seg=12, rings=6)
        sphere('eye%d' % s, ep + dirv * 0.03, 0.028, BLACK, head, seg=10, rings=6)
    tp = hp + dirv * 0.15 + Vector((0, 0, -0.02))
    tube('tongue', [tp, tp + dirv * 0.12, tp + dirv * 0.16 + side * 0.03], 0.012, tongue, head, res=6, bevel_res=4)
    tube('tongue2', [tp + dirv * 0.12, tp + dirv * 0.16 - side * 0.03], 0.012, tongue, head, res=6, bevel_res=4)
    pivot(head, tuple(hp - dirv * 0.12 - Vector((0, 0, 0.05))))
    return root

def build_bird():
    root = empty('bird')
    body = mat('#F48FB1'); wing = mat('#7BC67E'); belly = mat('#FFE08A'); beak = mat('#F7A93A'); crest = mat('#5EB4E8')
    sphere('body', (0, 0.02, 0.24), (0.17, 0.21, 0.17), body, root)
    sphere('belly', (0, -0.1, 0.2), (0.12, 0.1, 0.13), belly, root)
    head = empty('head'); head.parent = root
    sphere('skull', (0, -0.1, 0.44), 0.16, body, head)
    cone('beak', (0, -0.29, 0.42), 0.05, 0.005, 0.12, beak, head, rot=(-90, 0, 0), sub=0)
    eyes(head, 0.08, -0.22, 0.48, 0.03)
    cheeks(head, 0.12, -0.2, 0.42, 0.035)
    sphere('crest', (0, -0.06, 0.6), (0.05, 0.08, 0.05), crest, head, rot=(20, 0, 0), seg=12, rings=6)
    sphere('crest2', (0, 0.0, 0.58), (0.04, 0.07, 0.04), crest, head, rot=(45, 0, 0), seg=12, rings=6)
    for s, nm in ((-1, 'wingL'), (1, 'wingR')):
        w = empty(nm); w.parent = root; w.location = (s * 0.14, 0.02, 0.28)
        sphere('wingmesh%d' % s, (s * 0.07, 0.02, -0.03), (0.07, 0.15, 0.1), wing, w, rot=(0, s * 30, 0))
    for i in range(3):
        sphere('tailfeather%d' % i, (0, 0.24, 0.24 + (i - 1) * 0.03), (0.03, 0.1, 0.04), (crest, wing, belly)[i], root, rot=(-15 - i * 8, 0, 0), seg=12, rings=6)
    for s in (-1, 1):
        tube('leg%d' % s, [(s * 0.05, -0.02, 0.1), (s * 0.05, -0.02, 0.0)], 0.012, beak, root, res=4)
        sphere('foot%d' % s, (s * 0.05, -0.05, 0.0), (0.03, 0.045, 0.012), beak, root, seg=10, rings=6)
    pivot(head, (0, -0.08, 0.34))
    return root

def build_fish():
    root = empty('fish')
    body = mat('#F9A03F'); fin = mat('#5FB3E6'); stripe = mat('#FFE066'); lips = mat('#F27059')
    sphere('body', (0, 0, 0), (0.16, 0.32, 0.22), body, root)
    for i, y in enumerate((-0.08, 0.1)):
        f = math.sqrt(1 - (y / 0.32) ** 2)
        ring('stripe%d' % i, (0, y, 0), 1.0, 0.03, stripe, root, rot=(90, 0, 0), scale=(0.16 * f + 0.01, 0.22 * f + 0.01, 1))
    tf = empty('tailfin'); tf.parent = root; tf.location = (0, 0.3, 0)
    sphere('tailmesh', (0, 0.12, 0), (0.04, 0.16, 0.2), fin, tf)
    sphere('dorsal', (0, 0.02, 0.24), (0.035, 0.15, 0.1), fin, root, rot=(20, 0, 0))
    for s, nm in ((-1, 'finL'), (1, 'finR')):
        f = empty(nm); f.parent = root; f.location = (s * 0.14, -0.02, -0.04)
        sphere('finmesh%d' % s, (s * 0.05, 0.04, -0.02), (0.09, 0.1, 0.03), fin, f, rot=(0, s * 30, 0))
    for s in (-1, 1):
        sphere('eyewhite%d' % s, (s * 0.12, -0.2, 0.06), 0.06, WHITE, root, seg=12, rings=6)
        sphere('eye%d' % s, (s * 0.13, -0.25, 0.06), 0.035, BLACK, root, seg=12, rings=6)
    sphere('lips', (0, -0.32, -0.03), (0.05, 0.03, 0.035), lips, root, seg=12, rings=6)
    return root

# ----------------------------------------------------------------- characters
def build_explorer():
    root = empty('explorer')
    skin = mat('#FFDCC1'); hair = mat('#4A2E1F'); shirt = mat('#DCC79C'); shorts = mat('#B39A63')
    hat = mat('#E9D5A3'); band = mat('#8A6A3C'); shoe = mat('#7A5230')
    torso = rbox('torso', (0, 0, 0.6), (0.22, 0.15, 0.2), shirt, root, bevel=0.1, sharp=False)
    rbox('shorts', (0, 0, 0.36), (0.22, 0.15, 0.1), shorts, root, bevel=0.08, sharp=False)
    for s in (-1, 1):
        sphere('pocket%d' % s, (s * 0.12, -0.14, 0.62), (0.06, 0.02, 0.06), shorts, root, seg=12, rings=6)
        leg = empty('leg%d' % s); leg.parent = root; leg.location = (s * 0.1, 0, 0.3)
        limb('legmesh%d' % s, (0, 0, 0), (0, 0, -0.22), 0.07, skin, leg)
        sphere('shoe%d' % s, (0, -0.02, -0.25), (0.08, 0.11, 0.06), shoe, leg)
        arm = empty('arm%d' % s); arm.parent = root; arm.location = (s * 0.24, 0, 0.74)
        limb('sleeve%d' % s, (0, 0, 0), (s * 0.04, -0.03, -0.14), 0.065, shirt, arm)
        limb('armmesh%d' % s, (s * 0.04, -0.03, -0.14), (s * 0.06, -0.08, -0.3), 0.05, skin, arm)
        sphere('hand%d' % s, (s * 0.07, -0.1, -0.33), 0.065, skin, arm, seg=12, rings=6)
    head = empty('head'); head.parent = root; head.location = (0, 0, 0.84)
    sphere('skull', (0, 0, 0.24), 0.3, skin, head)
    sphere('hair', (0, 0.04, 0.32), (0.31, 0.3, 0.25), hair, head)
    sphere('bang', (0, -0.22, 0.44), (0.2, 0.1, 0.08), hair, head, rot=(20, 0, 0))
    sphere('hatdome', (0, 0, 0.5), (0.3, 0.3, 0.19), hat, head)
    cyl('brim', (0, 0, 0.45), 0.45, 0.04, hat, head, sub=1, verts=32)
    ring('hatband', (0, 0, 0.5), 0.3, 0.025, band, head, scale=(1, 1, 1))
    eyes(head, 0.1, -0.27, 0.27, 0.04)
    cheeks(head, 0.2, -0.24, 0.18, 0.06)
    smile(head, 0, -0.3, 0.14, 0.06, 0.035)
    sphere('nose', (0, -0.31, 0.22), 0.025, mat('#F2B99E'), head, seg=10, rings=6)
    return root

def build_robot():
    root = empty('robot')
    white = mat('#F4F6FA', 0.5); blue = mat('#5AB4F0', 0.6); dark = mat('#2A3F5F', 0.4); glow = mat('#7FEBFF', 0.3, emit=3.0)
    body = empty('body'); body.parent = root; body.location = (0, 0, 0.0)
    rbox('torso', (0, 0, 0.62), (0.22, 0.17, 0.22), white, body, bevel=0.1, sharp=False)
    ring('chestring', (0, -0.17, 0.62), 0.09, 0.02, blue, body, rot=(90, 0, 0))
    sphere('core', (0, -0.17, 0.62), 0.05, glow, body, seg=12, rings=6)
    rbox('skull', (0, 0, 1.06), (0.27, 0.23, 0.2), white, body, bevel=0.1, sharp=False)
    rbox('visor', (0, -0.2, 1.06), (0.2, 0.05, 0.11), dark, body, bevel=0.04, sharp=False)
    for s in (-1, 1):
        sphere('eye%d' % s, (s * 0.09, -0.25, 1.07), (0.04, 0.02, 0.035), glow, body, seg=12, rings=6)
        sphere('earcap%d' % s, (s * 0.28, 0, 1.06), (0.04, 0.08, 0.08), blue, body, seg=12, rings=6)
        arm = empty('arm%d' % s); arm.parent = body; arm.location = (s * 0.26, 0, 0.74)
        limb('armmesh%d' % s, (0, 0, 0), (s * 0.08, -0.06, -0.24), 0.05, white, arm)
        sphere('hand%d' % s, (s * 0.09, -0.07, -0.27), 0.07, blue, arm, seg=12, rings=6)
        limb('leg%d' % s, (s * 0.1, 0, 0.4), (s * 0.1, 0, 0.14), 0.06, white, body)
        sphere('foot%d' % s, (s * 0.1, -0.02, 0.1), (0.09, 0.12, 0.06), blue, body)
    tube('antenna', [(0, 0, 1.26), (0, 0, 1.42)], 0.015, blue, body, res=4)
    sphere('antennatip', (0, 0, 1.45), 0.04, glow, body, seg=12, rings=6)
    smile(body, 0, -0.26, 0.97, 0.05, 0.02, 0.01, glow)
    return root

# ----------------------------------------------------------------- props
def build_truck():
    root = empty('truck')
    paint = mat('#9C9A5E'); dark = mat('#6E6C3F'); tire = mat('#3A3634', 0.9); hub = mat('#E9E1C9'); glass = mat('#BFE6F5', 0.3)
    light = mat('#FFE27A', 0.5, emit=1.0)
    rbox('chassis', (0, 0.1, 0.62), (0.72, 1.25, 0.32), paint, root, bevel=0.1)
    rbox('cabin', (0, -0.15, 1.18), (0.62, 0.55, 0.28), paint, root, bevel=0.08)
    rbox('windshield', (0, -0.72, 1.18), (0.5, 0.03, 0.2), glass, root, bevel=0.02, sharp=False)
    for s in (-1, 1):
        rbox('sidewin%d' % s, (s * 0.64, -0.15, 1.2), (0.03, 0.4, 0.18), glass, root, bevel=0.02, sharp=False)
        sphere('headlight%d' % s, (s * 0.45, -1.36, 0.7), (0.1, 0.05, 0.1), light, root, seg=16, rings=8)
        sphere('taillight%d' % s, (s * 0.5, 1.36, 0.7), (0.07, 0.04, 0.07), mat('#E85D4A', 0.5), root, seg=12, rings=6)
        for yy in (-0.72, 0.78):
            wh = empty('wheel%s_%s' % (s, yy)); wh.parent = root; wh.location = (s * 0.72, yy, 0.34)
            cyl('tire', (0, 0, 0), 0.34, 0.26, tire, wh, rot=(0, 90, 0), sub=2)
            cyl('hub', (s * 0.14, 0, 0), 0.16, 0.04, hub, wh, rot=(0, 90, 0), sub=1)
    rbox('bumper', (0, -1.4, 0.45), (0.7, 0.08, 0.1), dark, root, bevel=0.04)
    rbox('rack', (0, -0.15, 1.5), (0.55, 0.5, 0.02), dark, root, bevel=0.01)
    for x in (-0.5, 0.5):
        for y in (-0.6, 0.3):
            cyl('rackpost', (x, y, 1.46), 0.025, 0.06, dark, root, sub=0)
    rbox('cargo', (0, 0.85, 1.05), (0.5, 0.35, 0.12), mat('#C7A46A'), root, bevel=0.05)
    rbox('cargo2', (0.1, 0.6, 1.25), (0.22, 0.18, 0.12), mat('#E3B77A'), root, bevel=0.05)
    return root

def build_stump():
    root = empty('stump')
    bark = mat('#8B5E3C'); top = mat('#E4B77E'); ringm = mat('#C9955E')
    cyl('trunk', (0, 0, 0.3), 0.5, 0.6, bark, root, sub=1, verts=32)
    cyl('top', (0, 0, 0.6), 0.44, 0.06, top, root, sub=1, verts=32)
    for i, rr in enumerate((0.12, 0.24, 0.35)):
        ring('ring%d' % i, (0, 0, 0.64), rr, 0.012, ringm, root)
    for i in range(5):
        a = i / 5 * math.tau
        tube('root%d' % i, [(math.cos(a) * 0.38, math.sin(a) * 0.38, 0.1), (math.cos(a) * 0.7, math.sin(a) * 0.7, 0.02)], 0.08, bark, root, radii=[1, 0.6])
    sphere('mushroom', (0.42, -0.3, 0.12), (0.06, 0.06, 0.09), mat('#FFF3D6'), root, seg=12, rings=6)
    sphere('mushcap', (0.42, -0.3, 0.2), (0.1, 0.1, 0.06), mat('#E85D4A'), root, seg=16, rings=8)
    return root

def build_bone():
    root = empty('bone')
    m = mat('#FFF8E7', 0.7)
    tube('shaft', [(-0.3, 0, 0.1), (0.3, 0, 0.1)], 0.07, m, root, res=4)
    for s in (-1, 1):
        for t in (-1, 1):
            sphere('knob%d%d' % (s, t), (s * 0.32, t * 0.08, 0.1 + t * 0.03), 0.11, m, root, seg=16, rings=8)
    return root

def build_flower():
    root = empty('flower')
    stem = mat('#6DBE5B'); center = mat('#FFD54F'); cols = ['#F48FB1', '#FFB74D', '#FFF176', '#81D4FA', '#B39DDB', '#F06292']
    tube('stem', [(0, 0, 0), (0.02, 0.02, 0.45), (0, 0, 0.8)], 0.04, stem, root)
    sphere('leaf', (0.18, 0.05, 0.35), (0.14, 0.06, 0.03), stem, root, rot=(0, 25, 0), seg=16, rings=8)
    head = empty('head'); head.parent = root; head.location = (0, -0.02, 0.86)
    sphere('center', (0, 0, 0), (0.17, 0.09, 0.17), center, head)
    for i in range(6):
        a = i / 6 * math.tau
        sphere('petal%d' % i, (math.cos(a) * 0.26, 0.03, math.sin(a) * 0.26), (0.13, 0.05, 0.13), mat(cols[i]), head, rot=(0, math.degrees(-a), 0), seg=16, rings=8)
    eyes(head, 0.06, -0.08, 0.03, 0.025)
    smile(head, 0, -0.09, -0.02, 0.04, 0.02, 0.008)
    cheeks(head, 0.1, -0.07, -0.02, 0.03)
    return root

def build_banana():
    root = empty('banana')
    y = mat('#FFD84D'); t = mat('#7A5A2A')
    tube('body', [(-0.28, 0, 0.12), (0, 0, 0.22), (0.28, 0, 0.12)], 0.08, y, root, radii=[0.55, 1, 0.55])
    sphere('tip1', (-0.29, 0, 0.11), 0.035, t, root, seg=10, rings=6)
    sphere('tip2', (0.29, 0, 0.11), 0.035, t, root, seg=10, rings=6)
    return root

def build_camera():
    root = empty('camera')
    body = mat('#F0B27A'); dark = mat('#4A3B36', 0.6); lens = mat('#2E3E5B', 0.3); cream = mat('#FFF1D6')
    rbox('body', (0, 0, 0.3), (0.42, 0.22, 0.28), body, root, bevel=0.1)
    rbox('stripe', (0, -0.225, 0.3), (0.42, 0.01, 0.08), cream, root, bevel=0.01, sharp=False)
    cyl('lensring', (0, -0.3, 0.3), 0.2, 0.18, dark, root, rot=(90, 0, 0), sub=1)
    cyl('lens', (0, -0.4, 0.3), 0.14, 0.04, lens, root, rot=(90, 0, 0), sub=1)
    sphere('lensglint', (-0.05, -0.43, 0.35), 0.03, WHITE, root, seg=10, rings=6)
    rbox('flash', (0.2, 0, 0.62), (0.1, 0.08, 0.05), dark, root, bevel=0.03)
    cyl('shutter', (-0.25, 0, 0.62), 0.06, 0.06, mat('#E85D4A'), root, sub=1)
    return root

def build_binoculars():
    root = empty('binoculars')
    dark = mat('#4A3B36', 0.6); lens = mat('#2E3E5B', 0.3); y = mat('#F2C94C', 0.6)
    for s in (-1, 1):
        cyl('barrel%d' % s, (s * 0.2, 0, 0.2), 0.16, 0.5, dark, root, rot=(90, 0, 0), sub=1)
        cyl('frontlens%d' % s, (s * 0.2, -0.26, 0.2), 0.12, 0.03, lens, root, rot=(90, 0, 0), sub=1)
        ring('band%d' % s, (s * 0.2, -0.05, 0.2), 0.165, 0.025, y, root, rot=(90, 0, 0))
        cyl('eyepiece%d' % s, (s * 0.2, 0.28, 0.2), 0.1, 0.08, y, root, rot=(90, 0, 0), sub=1)
    rbox('bridge', (0, 0.02, 0.2), (0.08, 0.15, 0.06), y, root, bevel=0.03)
    return root

# ----------------------------------------------------------------- export
def export(root, filename):
    deselect()
    root.select_set(True)
    for c in root.children_recursive:
        c.select_set(True)
    bpy.context.view_layer.objects.active = root
    path = os.path.join(OUT, filename)
    bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True,
                              export_apply=True, export_yup=True)
    verts = sum(len(c.data.vertices) for c in root.children_recursive if c.type == 'MESH')
    print('EXPORTED %-14s %7d KB  (%d base verts)' % (filename, os.path.getsize(path) // 1024, verts))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.curves):
        for b in block:
            if b.users == 0:
                block.remove(b)

BUILDERS = [
    ('lion', build_lion), ('giraffe', build_giraffe), ('zebra', build_zebra), ('elephant', build_elephant),
    ('monkey', build_monkey), ('hippo', build_hippo), ('crocodile', build_crocodile), ('snake', build_snake),
    ('bird', build_bird), ('fish', build_fish),
    ('explorer', build_explorer), ('robot', build_robot),
    ('truck', build_truck), ('stump', build_stump), ('bone', build_bone), ('flower', build_flower),
    ('banana', build_banana), ('camera', build_camera), ('binoculars', build_binoculars),
]
only = [a for a in argv[argv.index('--') + 2:]] if '--' in argv else []
for name, fn in BUILDERS:
    if only and name not in only:
        continue
    root = fn()
    export(root, name + '.glb')
print('ALL DONE')
