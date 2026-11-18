"""Procedural flower meshes for KitsuneFlora ~ run inside Blender.

These are our own meshes (no Asset Store source), so the script and its
output can live in the repo.

    blender --background --python Workspace/build_flowers.py -- Workspace/FlowerMeshes
    blender --background --python Workspace/build_flowers.py -- Workspace/FlowerMeshes KitsuneFlora/UIAtlases/ItemIconAtlas

The optional second folder gets a 1024 px transparent item icon per block,
rendered from the same meshes (treeKitsuneX.png and treePlantedKitsuneX1m.png).

Writes, per flower, <name>.fbx and <name>Small.fbx (the seed-stage mesh),
one shared palette texture (flowers_palette.png) and a preview render each.

Mesh notes for the Unity side:
- Units are metres, the plant stands on the origin, +Y up after export.
- Petals and leaves are single sided: the material must render both faces
  (Cull Off).
- Everything maps into one small palette texture, so a single material
  covers every flower.
"""
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

UP = Vector((0, 0, 1))
GOLDEN = math.pi * (3 - math.sqrt(5))

# Palette bands, left to right. Each band is a vertical gradient: v=0 is the
# base of the part, v=1 its tip. The texture always has BAND_SLOTS columns so
# adding a band never moves the existing ones.
BAND_SLOTS = 16
BANDS = [
    ("petal",      (0.42, 0.01, 0.02), (0.95, 0.07, 0.05)),   # spider lily
    ("stem",       (0.10, 0.22, 0.06), (0.30, 0.42, 0.12)),
    ("stamen",     (0.80, 0.06, 0.05), (0.35, 0.02, 0.02)),
    ("bud",        (0.26, 0.38, 0.10), (0.80, 0.06, 0.05)),
    ("leaf",       (0.08, 0.22, 0.06), (0.26, 0.46, 0.13)),   # hydrangea
    ("hyd_blue",   (0.20, 0.22, 0.70), (0.62, 0.74, 0.98)),
    ("hyd_pink",   (0.46, 0.24, 0.70), (0.93, 0.64, 0.88)),
    ("cam_leaf",   (0.02, 0.11, 0.04), (0.08, 0.25, 0.08)),   # camellia
    ("cam_petal",  (0.50, 0.02, 0.07), (0.92, 0.11, 0.17)),
    ("cam_stamen", (0.85, 0.58, 0.05), (1.00, 0.86, 0.22)),
    ("wood",       (0.15, 0.10, 0.06), (0.30, 0.22, 0.13)),
]
BAND_INDEX = {name: i for i, (name, _, _) in enumerate(BANDS)}

LEAF_PROFILE = (0.12, 0.72, 1.0, 0.86, 0.52, 0.04)


def bezier(p0, p1, p2, n):
    return [p0 * ((1 - t) ** 2) + p1 * (2 * (1 - t) * t) + p2 * (t * t)
            for t in (i / (n - 1) for i in range(n))]


def sample(pts, t):
    """(point, tangent) at t in 0..1 along a polyline."""
    f = min(max(t, 0.0), 1.0) * (len(pts) - 1)
    i = min(int(f), len(pts) - 2)
    return pts[i].lerp(pts[i + 1], f - i), (pts[i + 1] - pts[i]).normalized()


def perp_frame(t):
    ref = UP if abs(t.z) < 0.9 else Vector((1, 0, 0))
    e1 = t.cross(ref).normalized()
    return e1, t.cross(e1)


def sphere_dirs(n):
    """Evenly spread unit vectors (Fibonacci sphere)."""
    out = []
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        out.append(Vector((r * math.cos(GOLDEN * i), r * math.sin(GOLDEN * i), z)))
    return out


class MeshBuilder:
    def __init__(self):
        self.verts, self.faces, self.uvs = [], [], []

    @staticmethod
    def _u(band):
        i = BAND_INDEX[band]
        return (i + 0.25) / BAND_SLOTS, (i + 0.75) / BAND_SLOTS

    @staticmethod
    def _v(t):
        return 0.03 + 0.94 * t

    def quad(self, pts, band, vs):
        u0, u1 = self._u(band)
        um = (u0 + u1) / 2
        base = len(self.verts)
        self.verts += pts
        self.faces.append((base, base + 1, base + 2, base + 3))
        self.uvs.append(tuple((um, self._v(v)) for v in vs))

    def ribbon(self, pts, widths, side, band):
        """Flat strip along pts; `side` is the across-the-strip direction."""
        u0, u1 = self._u(band)
        base = len(self.verts)
        for p, w in zip(pts, widths):
            self.verts += [p - side * (w / 2), p + side * (w / 2)]
        n = len(pts)
        for i in range(n - 1):
            a = base + 2 * i
            t0, t1 = self._v(i / (n - 1)), self._v((i + 1) / (n - 1))
            self.faces.append((a, a + 1, a + 3, a + 2))
            self.uvs.append(((u0, t0), (u1, t0), (u1, t1), (u0, t1)))

    def leaf(self, base, direction, length, width, band, droop=0.2, fold=0.1,
             side=None, normal=None, profile=LEAF_PROFILE):
        """Leaf or petal: a strip three verts wide, folded along its midrib.
        Positive droop bends the tip away from `normal`, negative cups it."""
        d = direction.normalized()
        if side is None:
            side = d.cross(UP if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized()
        if normal is None:
            normal = side.cross(d).normalized()
        u0, u1 = self._u(band)
        um = (u0 + u1) / 2
        start = len(self.verts)
        n = len(profile)
        for i, w in enumerate(profile):
            t = i / (n - 1)
            p = base + d * (length * t) - normal * (droop * length * t * t)
            hw = w * width / 2
            lift = normal * (fold * hw * 2)
            self.verts += [p - side * hw + lift, p, p + side * hw + lift]
        for i in range(n - 1):
            a = start + 3 * i
            t0, t1 = self._v(i / (n - 1)), self._v((i + 1) / (n - 1))
            self.faces.append((a, a + 1, a + 4, a + 3))
            self.uvs.append(((u0, t0), (um, t0), (um, t1), (u0, t1)))
            self.faces.append((a + 1, a + 2, a + 5, a + 4))
            self.uvs.append(((um, t0), (u1, t0), (u1, t1), (um, t1)))

    def tube(self, pts, radii, band, sides=3, vr=(0.0, 1.0)):
        u0, u1 = self._u(band)
        base = len(self.verts)
        n = len(pts)
        for i, (p, r) in enumerate(zip(pts, radii)):
            t = (pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized()
            n1, n2 = perp_frame(t)
            for s in range(sides):
                a = 2 * math.pi * s / sides
                self.verts.append(p + (n1 * math.cos(a) + n2 * math.sin(a)) * r)
        for i in range(n - 1):
            t0 = self._v(vr[0] + (vr[1] - vr[0]) * i / (n - 1))
            t1 = self._v(vr[0] + (vr[1] - vr[0]) * (i + 1) / (n - 1))
            for s in range(sides):
                a = base + i * sides + s
                b = base + i * sides + (s + 1) % sides
                self.faces.append((a, b, b + sides, a + sides))
                self.uvs.append(((u0, t0), (u1, t0), (u1, t1), (u0, t1)))

    def to_object(self, name, material):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([tuple(v) for v in self.verts], [], self.faces)
        uv = mesh.uv_layers.new(name="UVMap")
        for poly, face_uv in zip(mesh.polygons, self.uvs):
            poly.use_smooth = True
            for li, coord in zip(poly.loop_indices, face_uv):
                uv.data[li].uv = coord
        mesh.materials.append(material)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        return obj


def scatter(rng, count, radius, min_gap):
    out = []
    while len(out) < count:
        a, r = rng.uniform(0, 2 * math.pi), radius * math.sqrt(rng.random())
        p = Vector((r * math.cos(a), r * math.sin(a), 0))
        if all((p - q).length > min_gap for q in out):
            out.append(p)
    return out


# ---------- spider lily (higanbana, Lycoris radiata) ----------------------

def stem_points(base, height, lean, n=6):
    return [base + Vector((lean.x * t * t, lean.y * t * t, height * t))
            for t in (i / (n - 1) for i in range(n))]


def lily_bud(mb, rng, tip, direction, length=0.06):
    pts = [tip + direction * (length * t) for t in (0, 0.2, 0.5, 0.8, 1.0)]
    mb.tube(pts, [0.003, 0.010, 0.012, 0.008, 0.001], "bud", sides=5)


def lily_floret(mb, rng, base, axis, s=1.0):
    """Six narrow petals curling right back, six long stamens sweeping up."""
    u = axis.cross(UP).normalized()
    v = axis.cross(u)
    length, width = rng.uniform(0.08, 0.095) * s, 0.013 * s
    profile = [0.45, 0.9, 1.0, 0.9, 0.7, 0.4, 0.1]
    spin = rng.uniform(0, math.pi)
    for j in range(6):
        psi = spin + 2 * math.pi * j / 6
        radial = u * math.cos(psi) + v * math.sin(psi)
        side = axis.cross(radial).normalized()
        steps = len(profile) - 1
        th0, th1 = math.radians(20), math.radians(rng.uniform(190, 230))
        p, pts = base.copy(), [base.copy()]
        for i in range(steps):
            th = th0 + (th1 - th0) * (i + 0.5) / steps
            p = p + (axis * math.cos(th) + radial * math.sin(th)) * (length / steps)
            pts.append(p.copy())
        mb.ribbon(pts, [w * width for w in profile], side, "petal")
    for j in range(6):
        psi = spin + 2 * math.pi * (j + 0.5) / 6
        radial = u * math.cos(psi) + v * math.sin(psi)
        slen = rng.uniform(0.10, 0.13) * s
        p, pts = base.copy(), [base.copy()]
        for i in range(4):
            t = (i + 0.5) / 4
            d = (axis * (1 - t) + radial * 0.3 + UP * (1.4 * t)).normalized()
            p = p + d * (slen / 4)
            pts.append(p.copy())
        mb.tube(pts, [r * s for r in (0.0016, 0.0014, 0.0012, 0.0012, 0.0018)], "stamen", sides=3)


def lily_stem(mb, rng, base, height, bud=False, s=1.0):
    lean = Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0))
    pts = stem_points(base, height, lean)
    mb.tube(pts, [r * s for r in (0.0075, 0.007, 0.0065, 0.006, 0.0055, 0.005)], "stem", sides=5)
    top = pts[-1]
    if bud:
        lily_bud(mb, rng, top, (pts[-1] - pts[-2]).normalized(), length=0.06 * s)
        return
    florets = rng.choice((5, 6, 6, 7))
    spin = rng.uniform(0, 2 * math.pi)
    for k in range(florets):
        az = spin + 2 * math.pi * k / florets + rng.uniform(-0.15, 0.15)
        el = math.radians(rng.uniform(10, 30))
        axis = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
        tip = top + axis * (0.03 * s)
        mb.tube([top, tip], [0.003 * s, 0.0025 * s], "stem", sides=3)
        lily_floret(mb, rng, tip, axis, s)


def spider_lily(mb, rng):
    for i, base in enumerate(scatter(rng, 10, 0.32, 0.10)):
        lily_stem(mb, rng, base, rng.uniform(0.52, 0.80), bud=(i >= 8), s=1.6)


def spider_lily_small(mb, rng):
    for base in scatter(rng, 3, 0.10, 0.06):
        lily_stem(mb, rng, base, rng.uniform(0.16, 0.28), bud=True, s=1.4)


# ---------- hydrangea (ajisai, Hydrangea macrophylla) ---------------------

def leaf_pair(mb, rng, pts, t, turn, length, width, band="leaf"):
    """Two opposite leaves on a stem; `turn` rotates the pair around it."""
    p, tan = sample(pts, t)
    e1, e2 = perp_frame(tan)
    out = e1 * math.cos(turn) + e2 * math.sin(turn)
    for sign in (1, -1):
        d = out * (0.85 * sign) + tan * 0.45 + UP * 0.12
        size = rng.uniform(0.85, 1.1)
        mb.leaf(p, d, length * size, width * size, band,
                droop=rng.uniform(0.25, 0.45), fold=0.14)


def mophead(mb, rng, centre, stem_dir, radius, band):
    """Ball of four-petalled florets around a dark core."""
    core = [centre + stem_dir * (radius * z) for z in (-0.85, -0.5, 0.0, 0.5, 0.85)]
    mb.tube(core, [radius * r for r in (0.05, 0.62, 0.82, 0.62, 0.05)], band,
            sides=6, vr=(0.0, 0.12))
    size = radius * 0.34
    for d in sphere_dirs(52):
        if d.dot(stem_dir) < -0.7:  # underside, hidden by the stem and leaves
            continue
        c = centre + d * (radius * rng.uniform(0.93, 1.06))
        e1, e2 = perp_frame(d)
        spin = rng.uniform(0, math.pi / 2)
        v0, v1 = rng.uniform(0.15, 0.55), rng.uniform(0.6, 1.0)
        for j in range(4):
            a = spin + j * math.pi / 2
            r = e1 * math.cos(a) + e2 * math.sin(a)
            s = d.cross(r)
            mb.quad([c + d * (size * 0.04),
                     c + r * (size * 0.55) - s * (size * 0.42) + d * (size * 0.10),
                     c + r * size - d * (size * 0.12),
                     c + r * (size * 0.55) + s * (size * 0.42) + d * (size * 0.10)],
                    band, (v0, (v0 + v1) / 2, v1, (v0 + v1) / 2))


def hydrangea_shoot(mb, rng, tip, head_band=None, leaf_ts=(0.42, 0.6, 0.78, 0.94)):
    base = Vector((tip.x * 0.12, tip.y * 0.12, 0))
    ctrl = Vector((tip.x * 0.30, tip.y * 0.30, tip.z * 0.65))
    pts = bezier(base, ctrl, tip, 7)
    mb.tube(pts, [0.009, 0.0085, 0.008, 0.0072, 0.0065, 0.0058, 0.005], "stem", sides=4)
    turn = rng.uniform(0, math.pi)
    for k, t in enumerate(leaf_ts):
        leaf_pair(mb, rng, pts, t, turn + k * math.pi / 2, 0.14, 0.10)
    if head_band:
        tan = (pts[-1] - pts[-2]).normalized()
        radius = rng.uniform(0.075, 0.095)
        mophead(mb, rng, tip + tan * (radius * 0.7), tan, radius, head_band)


def hydrangea(mb, rng):
    radius, centre_z = 0.34, 0.36
    heads = 9
    for i in range(heads):
        z = 1.0 - 0.82 * (i + 0.5) / heads          # 0.95 at the crown .. 0.22
        r = math.sqrt(1 - z * z) * radius
        az = GOLDEN * i + rng.uniform(-0.2, 0.2)
        tip = Vector((r * math.cos(az), r * math.sin(az), centre_z + radius * 0.85 * z))
        hydrangea_shoot(mb, rng, tip, "hyd_blue" if i % 3 else "hyd_pink")
    for i in range(8):                               # leafy shoots fill the skirt
        az = GOLDEN * i + 1.1
        r = radius * rng.uniform(0.75, 1.0)
        tip = Vector((r * math.cos(az), r * math.sin(az), rng.uniform(0.22, 0.42)))
        hydrangea_shoot(mb, rng, tip, leaf_ts=(0.35, 0.6, 0.85, 1.0))


def hydrangea_small(mb, rng):
    for i in range(3):
        az = 2 * math.pi * i / 3 + rng.uniform(-0.3, 0.3)
        r = rng.uniform(0.05, 0.09)
        tip = Vector((r * math.cos(az), r * math.sin(az), rng.uniform(0.16, 0.26)))
        hydrangea_shoot(mb, rng, tip, leaf_ts=(0.55, 1.0))


# ---------- camellia (tsubaki, Camellia japonica) -------------------------

def camellia_flower(mb, rng, base, axis):
    """Two whorls of rounded petals cupped round a yellow stamen boss."""
    e1, e2 = perp_frame(axis)
    spin = rng.uniform(0, math.pi)
    profile = (0.45, 0.95, 1.0, 0.72, 0.2)
    for whorl, (count, open_deg, length) in enumerate(((5, 62, 0.064), (4, 36, 0.052))):
        for j in range(count):
            a = spin + whorl * 0.6 + 2 * math.pi * j / count
            r = e1 * math.cos(a) + e2 * math.sin(a)
            th = math.radians(open_deg + rng.uniform(-6, 6))
            d = axis * math.cos(th) + r * math.sin(th)
            side = axis.cross(r).normalized()
            normal = side.cross(d).normalized()
            if normal.dot(axis) < 0:
                normal = -normal
            mb.leaf(base, d, length, length * 0.95, "cam_petal", droop=-0.25, fold=0.18,
                    side=side, normal=normal, profile=profile)
    mb.tube([base, base + axis * 0.020, base + axis * 0.028], [0.009, 0.015, 0.001],
            "cam_stamen", sides=6)


CAMELLIA_LEAF = (0.15, 1.0, 0.78, 0.05)


def camellia_branch(mb, rng, pts, leaves, radii, flower=False, start=0.28, twigs=0):
    mb.tube(pts, radii, "wood", sides=3)
    spin = rng.uniform(0, 2 * math.pi)
    for k in range(leaves):
        t = start + (1 - start) * k / (leaves - 1)
        p, tan = sample(pts, t)
        e1, e2 = perp_frame(tan)
        a = spin + GOLDEN * k
        out = e1 * math.cos(a) + e2 * math.sin(a)
        size = rng.uniform(0.85, 1.15)
        mb.leaf(p, out * 0.8 + tan * 0.65 + UP * 0.1, 0.12 * size, 0.068 * size, "cam_leaf",
                droop=rng.uniform(0.05, 0.25), fold=0.12, profile=CAMELLIA_LEAF)
    for k in range(twigs):
        p, tan = sample(pts, 0.4 + 0.3 * k + rng.uniform(-0.05, 0.05))
        e1, e2 = perp_frame(tan)
        a = spin + math.pi * k + rng.uniform(-0.6, 0.6)
        out = (e1 * math.cos(a) + e2 * math.sin(a)) * 0.9 + tan * 0.5 + UP * 0.2
        end = p + out.normalized() * rng.uniform(0.14, 0.2)
        twig = bezier(p, p.lerp(end, 0.5) + UP * 0.03, end, 4)
        camellia_branch(mb, rng, twig, 6, [0.004, 0.0035, 0.003, 0.002],
                        flower=rng.random() < 0.3, start=0.25)
    if flower:
        tan = (pts[-1] - pts[-2]).normalized()
        axis = (tan + Vector((pts[-1].x, pts[-1].y, 0)).normalized() * 0.6 + UP * 0.25).normalized()
        camellia_flower(mb, rng, pts[-1] + axis * 0.01, axis)


def camellia(mb, rng):
    trunk = [Vector((0.02 * math.sin(z * 5), 0.02 * math.cos(z * 4) - 0.02, z))
             for z in (0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.18)]
    mb.tube(trunk, [0.030, 0.026, 0.022, 0.018, 0.015, 0.012, 0.008], "wood", sides=6)
    centre_z, rx, rz = 0.80, 0.38, 0.62
    count = 30
    for i in range(count):
        zc = -0.92 + 1.84 * (i + 0.5) / count            # canopy bottom .. top
        r = math.sqrt(max(0.0, 1 - zc * zc)) * rx * rng.uniform(0.9, 1.05)
        az = GOLDEN * i
        tip = Vector((r * math.cos(az), r * math.sin(az), centre_z + rz * zc))
        start, _ = sample(trunk, min(max(tip.z * 0.62, 0.12), 1.1) / 1.18)
        ctrl = start.lerp(tip, 0.5) + UP * 0.07
        pts = bezier(start, ctrl, tip, 6)
        camellia_branch(mb, rng, pts, 11, [0.010, 0.008, 0.007, 0.006, 0.005, 0.003],
                        flower=(i % 2 == 0), twigs=2)
    top = bezier(trunk[-1], trunk[-1] + UP * 0.12, trunk[-1] + Vector((0.03, 0.02, 0.26)), 5)
    camellia_branch(mb, rng, top, 9, [0.008, 0.007, 0.006, 0.004, 0.003], flower=True, start=0.1)


def camellia_small(mb, rng):
    pts = bezier(Vector((0, 0, 0)), Vector((0.02, 0.0, 0.16)), Vector((0.0, 0.02, 0.32)), 6)
    camellia_branch(mb, rng, pts, 9, [0.008, 0.007, 0.006, 0.005, 0.004, 0.003], start=0.2)


FLOWERS = [
    # preview group, bundle mesh name, builder, random seed
    ("spider_lily", "treeKitsuneSpiderLily", spider_lily, 11),
    ("spider_lily", "treeKitsuneSpiderLilySmall", spider_lily_small, 12),
    ("hydrangea", "treeKitsuneHydrangea", hydrangea, 21),
    ("hydrangea", "treeKitsuneHydrangeaSmall", hydrangea_small, 22),
    ("camellia", "treeKitsuneCamellia", camellia, 31),
    ("camellia", "treeKitsuneCamelliaSmall", camellia_small, 32),
]


# ---------- scene, export, preview ----------------------------------------

def make_palette(path, band_px=8, height=64):
    width = band_px * BAND_SLOTS
    img = bpy.data.images.new("flowers_palette", width, height, alpha=False)
    px = [0.0] * (width * height * 4)
    for y in range(height):
        t = y / (height - 1)
        for x in range(width):
            band = x // band_px
            i = (y * width + x) * 4
            if band < len(BANDS):
                _, c0, c1 = BANDS[band]
                px[i:i + 3] = [c0[k] + (c1[k] - c0[k]) * t for k in range(3)]
            px[i + 3] = 1.0
    img.pixels = px
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    return img


def make_material(img):
    mat = bpy.data.materials.new("KitsuneFlowers")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.7
    return mat


def export_fbx(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(path), use_selection=True, object_types={"MESH"},
        apply_scale_options="FBX_SCALE_UNITS", bake_space_transform=True,
        axis_forward="-Z", axis_up="Y", mesh_smooth_type="FACE", path_mode="RELATIVE")


def flat_material(name, color):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    return mat


def setup_lighting():
    scene = bpy.context.scene
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    scene.collection.objects.link(sun)
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(35))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    scene.world = world
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.render.image_settings.file_format = "PNG"


def render_preview(objs, all_objs, path):
    """Mature and seed-stage mesh side by side, each on a 1 m block tile."""
    scene = bpy.context.scene
    spacing = 1.1
    temp = []
    for other in all_objs:
        other.hide_render = other not in objs
    for i, obj in enumerate(objs):
        obj.location.x = i * spacing
        bpy.ops.mesh.primitive_plane_add(size=1.0, location=(i * spacing, 0, -0.001))
        bpy.context.object.data.materials.append(flat_material("tile", (0.16, 0.13, 0.10)))
        temp.append(bpy.context.object)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -0.002))
    bpy.context.object.data.materials.append(flat_material("ground", (0.07, 0.08, 0.07)))
    temp.append(bpy.context.object)

    height = max(o.dimensions.z for o in objs)
    mid = (len(objs) - 1) * spacing / 2
    dist = 1.6 + 2.0 * height
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    temp.append(cam)
    cam.location = (mid + 0.28 * dist, -dist, 0.42 * dist + height * 0.1)
    cam.data.lens = 55
    target = Vector((mid, 0, height * 0.5))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    scene.render.filepath = str(path)
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "CYCLES"):
        try:
            scene.render.engine = engine
            if engine == "CYCLES":
                scene.cycles.samples = 48
            bpy.ops.render.render(write_still=True)
            break
        except Exception as exc:  # engine missing or no GPU in background mode
            print("render failed with", engine, exc)
    for t in temp:
        bpy.data.objects.remove(t, do_unlink=True)
    for obj in objs:
        obj.location.x = 0


def icon_name(mesh_name):
    """treeKitsuneXSmall is the seed block treePlantedKitsuneX1m."""
    if mesh_name.endswith("Small"):
        return "treePlanted" + mesh_name[len("tree"):-len("Small")] + "1m"
    return mesh_name


def render_icon(obj, all_objs, path):
    scene = bpy.context.scene
    for other in all_objs:
        other.hide_render = other is not obj
    corners = [obj.matrix_world @ v.co for v in obj.data.vertices]
    cam = bpy.data.objects.new("icon_cam", bpy.data.cameras.new("icon_cam"))
    scene.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    view = Vector((0.35, -1.0, 0.38)).normalized()
    cam.rotation_euler = (-view).to_track_quat("-Z", "Y").to_euler()
    rot = cam.rotation_euler.to_matrix()
    right, up = rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0))
    xs, ys = [c.dot(right) for c in corners], [c.dot(up) for c in corners]
    centre = right * ((min(xs) + max(xs)) / 2) + up * ((min(ys) + max(ys)) / 2)
    cam.location = centre + view * 10
    cam.data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.08
    scene.camera = cam
    old = (scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent)
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.film_transparent = True
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    scene.render.resolution_x, scene.render.resolution_y, scene.render.film_transparent = old
    bpy.data.objects.remove(cam, do_unlink=True)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["Workspace/FlowerMeshes"]
    out = Path(argv[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    material = make_material(make_palette(out / "flowers_palette.png"))
    setup_lighting()

    groups = {}
    for group, name, build, seed in FLOWERS:
        mb = MeshBuilder()
        build(mb, random.Random(seed))
        obj = mb.to_object(name, material)
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        size = obj.dimensions
        print(f"MESH {name}: {tris} tris, {size.x:.2f} x {size.y:.2f} x {size.z:.2f} m")
        export_fbx(obj, out / f"{name}.fbx")
        groups.setdefault(group, []).append(obj)

    all_objs = [o for objs in groups.values() for o in objs]
    for group, objs in groups.items():
        render_preview(objs, all_objs, out / f"preview_{group}.png")
        print("PREVIEW", group)

    if len(argv) > 1:
        icons = Path(argv[1]).resolve()
        for obj in all_objs:
            render_icon(obj, all_objs, icons / f"{icon_name(obj.name)}.png")
            print("ICON", icon_name(obj.name))


main()
