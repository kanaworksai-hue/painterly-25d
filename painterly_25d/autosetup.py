# SPDX-License-Identifier: GPL-3.0-or-later
"""Make the one-click setup work on *any* scene, not just a hand-tuned one.

* target collection : meshes / curves / text / surfaces, including objects inside
                      collection instances (asset-browser / linked assets)
* auto materials    : objects with no material get one (keeps vertex colours)
* key light         : adds a Sun aimed from the camera side when the scene has none
* fit to scene      : brush-dab size, fog and outline fade follow the scene scale
"""
import math as _m
import statistics

import bpy
from mathutils import Vector

from .util import TAG, OUTLINE_MAT

SHADE_TYPES = {"MESH", "CURVE", "FONT", "SURFACE"}   # get the toon material
OUTLINE_TYPES = {"MESH"}                            # get the GN inverted-hull outline
KEY_SUN = "P25D Key Sun"


# --------------------------------------------------------------------------
# targets
# --------------------------------------------------------------------------
def _ok(o):
    return o.type in SHADE_TYPES and not o.get(TAG + "_skip") and hasattr(o.data, "materials")


def _expand(objs):
    """Objects plus everything inside collection instances (recursively, once)."""
    out, seen = [], set()

    def add(o):
        if o.name_full in seen:
            return
        seen.add(o.name_full)
        if _ok(o):
            out.append(o)
        if o.instance_type == "COLLECTION" and o.instance_collection:
            for c in o.instance_collection.all_objects:
                add(c)

    for o in objs:
        add(o)
    return out


expand = _expand


def _renders(o, view_layer):
    """Hidden in the viewport (eye / monitor icon) but still rendered."""
    return (not o.hide_render and o.name in view_layer.objects
            and all(not c.hide_render for c in o.users_collection))


def targets(context, scope="AUTO"):
    """scope AUTO: selection, or every visible object when nothing shadable is selected.
    ALL: every visible object. SELECTED: selection only."""
    if scope != "ALL":
        sel = _expand(context.selected_objects)
        if sel or scope == "SELECTED":
            return sel
    vl = context.view_layer
    return _expand([o for o in context.scene.objects if o.visible_get() or _renders(o, vl)])


def all_targets(scene):
    """Every shadable object of the scene, visible or not (used by a full Revert)."""
    return _expand(list(scene.objects))


def outline_targets(objs):
    return [o for o in objs if o.type in OUTLINE_TYPES and o.is_editable]


# --------------------------------------------------------------------------
# auto materials
# --------------------------------------------------------------------------
def _new_material(o):
    m = bpy.data.materials.new(f"P25D {o.name}")
    if m.node_tree is None:
        try:
            m.use_nodes = True       # deprecated in 5.x (always on); harmless where still needed
        except Exception:
            pass
    nt = m.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or \
            nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    col = tuple(o.color)
    if col[:3] == (1.0, 1.0, 1.0):
        col = (0.8, 0.8, 0.8, 1.0)
    bsdf.inputs["Base Color"].default_value = col
    attrs = getattr(o.data, "color_attributes", None)
    if attrs and len(attrs):          # scans / PLY / vertex-painted meshes
        vc = nt.nodes.new("ShaderNodeVertexColor")
        act = attrs.active_color or attrs[0]
        vc.layer_name = act.name
        vc.location = (bsdf.location.x - 300, bsdf.location.y)
        nt.links.new(vc.outputs["Color"], bsdf.inputs["Base Color"])
    m[TAG + "_auto"] = True
    return m


def ensure_materials(objs):
    """Give material-less objects (or empty slots) a Principled material. Returns count."""
    n = 0
    for o in objs:
        slots = o.material_slots                      # effective material (object- or data-linked)
        if len(slots) and all(s.material is not None for s in slots):
            continue
        data_linked = bool(getattr(o.data, "library", None))
        if not len(slots):
            if data_linked or not o.is_editable:      # linked data: can't edit
                continue
            o.data.materials.append(_new_material(o))
            n += 1
            continue
        empty = [s for s in slots if s.material is None and (s.link == "OBJECT" or not data_linked)]
        if not empty or not o.is_editable:
            continue
        m = _new_material(o)
        for s in empty:
            s.material = m
        n += 1
    return n


def materials_of(objs):
    return {s.material for o in objs for s in o.material_slots
            if s.material and s.material.name != OUTLINE_MAT}


# --------------------------------------------------------------------------
# key light
# --------------------------------------------------------------------------
def _cam_axes(scene):
    cam = scene.camera
    if cam is None:
        return Vector((0, 1, 0)), Vector((1, 0, 0))
    q = cam.matrix_world.to_quaternion()
    f = q @ Vector((0, 0, -1))
    f.z = 0
    if f.length < 1e-4:
        f = q @ Vector((0, 1, 0))
        f.z = 0
    f.normalize()
    r = Vector((f.y, -f.x, 0))
    return f, r


def light_irradiance(o, centre=None):
    """Irradiance (Sun-strength units) a light puts on a surface facing it at `centre`.
    Measured in EEVEE 5.2: point/spot = P / (4 pi d^2), area = P / (pi d^2)."""
    ld = o.data
    e = ld.energy * max(ld.color)
    if ld.type == "SUN" or centre is None:
        return e
    d2 = max((o.matrix_world.translation - centre).length_squared, 1e-6)
    return e / ((4.0 if ld.type in ("POINT", "SPOT") else 1.0) * _m.pi * d2)


def pick_key(scene, centre=None):
    """Strongest visible Sun, else the light giving the most irradiance at the subject."""
    lights = [o for o in scene.objects if o.type == "LIGHT" and o.visible_get()]
    suns = [o for o in lights if o.data.type == "SUN"]
    if suns:
        return max(suns, key=lambda o: o.data.energy)
    return max(lights, key=lambda o: light_irradiance(o, centre), default=None)


def ensure_key_sun(scene):
    """Return the key light; create a Sun aimed from the camera side only if the scene has no light."""
    key = pick_key(scene, subject_centre(scene))
    if key is not None:
        return key, False
    f, r = _cam_axes(scene)
    # light comes from behind the camera, upper-left: classic 3/4 key that shows form
    to_light = (-f * 0.55 - r * 0.65 + Vector((0, 0, 1.0))).normalized()
    ld = bpy.data.lights.new(KEY_SUN, "SUN")
    ld.energy = 3.0
    ld.angle = _m.radians(3.0)
    ld.color = (1.0, 0.95, 0.88)
    ob = bpy.data.objects.new(KEY_SUN, ld)
    scene.collection.objects.link(ob)
    ob.rotation_euler = (-to_light).to_track_quat("-Z", "Y").to_euler()
    ob[TAG + "_auto"] = True
    return ob, True


# --------------------------------------------------------------------------
# fit to scene scale
# --------------------------------------------------------------------------
def _world_bbox(o):
    return [o.matrix_world @ Vector(c) for c in o.bound_box]


def _instance_matrices(objs):
    """World matrices as evaluated (collection instances included), keyed by original object."""
    want = {o.name_full for o in objs}
    mats = []
    try:
        dg = bpy.context.evaluated_depsgraph_get()
        for inst in dg.object_instances:
            ob = inst.object.original
            if ob.name_full in want:
                mats.append((ob, inst.matrix_world.copy()))
    except Exception:
        pass
    seen = {ob.name_full for ob, _ in mats}
    mats += [(o, o.matrix_world.copy()) for o in objs if o.name_full not in seen]
    return mats


def scene_metrics(scene, objs):
    """(median object size, scene centre, scene radius, camera distance) from non-flat objects."""
    sizes, pts = [], []
    for o, mw in _instance_matrices(objs):
        bb = [mw @ Vector(c) for c in o.bound_box]
        lo = Vector(tuple(min(v[i] for v in bb) for i in range(3)))
        hi = Vector(tuple(max(v[i] for v in bb) for i in range(3)))
        d = hi - lo
        if max(d) <= 0 or min(d.x, d.y, d.z) < 1e-4 * max(d):     # skip ground planes / cards
            continue
        sizes.append(max(d))
        pts += [lo, hi]
    if not sizes:
        return None
    size = statistics.median(sizes)
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    centre = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    cam = scene.camera
    dist = (cam.matrix_world.translation - centre).length if cam else radius * 3
    return size, centre, radius, max(dist, 1e-3)


def subject_centre(scene):
    objs = _expand([o for o in scene.objects if o.visible_get()])
    met = scene_metrics(scene, objs) if objs else None
    return met[1] if met else None


def fit_to_scene(scene, objs):
    """Scale-dependent settings. Tuned so a ~2.5 m prop gives the reference look."""
    met = scene_metrics(scene, objs)
    if met is None:
        return None
    size, _c, radius, dist = met
    s = scene.p25d
    s["_lock"] = True
    try:
        s.stroke_scale = max(0.01, min(10000.0, 30.0 / size))
        s.fog_start = dist + radius * 0.6
        s.fog_end = s.fog_start + max(radius * 2.5, dist)
        # outline width is angular (thickness / reference distance); moving the reference to the
        # subject keeps that width but starts the far-distance thinning behind the subject
        ang = s.outline_thickness / max(1e-6, s.outline_ref_distance)
        s.outline_ref_distance = max(0.01, dist)
        s.outline_thickness = ang * s.outline_ref_distance
        s.outline_fade_distance = max(s.fog_end, dist * 3.0)
    finally:
        s["_lock"] = False
    return met


# --------------------------------------------------------------------------
# world fill estimate
# --------------------------------------------------------------------------
AMBIENT_COMP = 0.8      # fraction of the sky fill removed before the cel split


def _image_mean_max(img, cap=262144):
    """Mean of the brightest channel of an image (subsampled)."""
    try:
        import numpy as np
        n = len(img.pixels)
        if n == 0:
            return None
        buf = np.empty(n, dtype=np.float32)
        img.pixels.foreach_get(buf)
        px = buf.reshape(-1, 4)[:, :3]
        step = max(1, len(px) // cap)
        return float(px[::step].max(axis=1).mean())
    except Exception:
        return None


def estimate_ambient(scene):
    """Irradiance the world adds on an upward-facing surface (same units as the key Sun)."""
    w = scene.world
    if w is None or w.node_tree is None:
        return 0.0
    out = next((n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD" and n.is_active_output), None) or \
        next((n for n in w.node_tree.nodes if n.type == "OUTPUT_WORLD"), None)
    if out is None or not out.inputs["Surface"].is_linked:
        return 0.0
    bg = out.inputs["Surface"].links[0].from_node
    if bg.type != "BACKGROUND":
        return 0.0
    k = bg.inputs["Strength"].default_value if not bg.inputs["Strength"].is_linked else 1.0
    c = bg.inputs["Color"]
    if not c.is_linked:
        level = max(c.default_value[:3])
    else:
        src = c.links[0].from_node
        level = None
        if src.type in ("TEX_ENVIRONMENT", "TEX_IMAGE") and src.image:
            level = _image_mean_max(src.image)
        if level is None:
            level = 0.5          # procedural sky / gradient: neutral guess, tweak in the panel
    return _m.pi * k * level * AMBIENT_COMP


# --------------------------------------------------------------------------
# object colour -> coloured outlines
# --------------------------------------------------------------------------
def _image_mean_rgb(img, cap=65536):
    try:
        import numpy as np
        n = len(img.pixels)
        if n == 0:
            return None
        buf = np.empty(n, dtype=np.float32)
        img.pixels.foreach_get(buf)
        px = buf.reshape(-1, 4)
        px = px[::max(1, len(px) // cap)]
        w = px[:, 3:4] if img.depth in (32, 128) or img.alpha_mode != "NONE" else None
        if w is not None and float(w.sum()) > 1e-3:
            return tuple(float(x) for x in (px[:, :3] * w).sum(axis=0) / float(w.sum()))
        return tuple(float(x) for x in px[:, :3].mean(axis=0))
    except Exception:
        return None


def _socket_colour(sock_, obj, depth=0):
    """Average colour arriving at a colour socket (constant, image texture or vertex colours)."""
    if not sock_.is_linked:
        v = sock_.default_value
        return tuple(v[:3]) if hasattr(v, "__len__") and len(v) >= 3 else None
    node = sock_.links[0].from_node
    if node.type == "TEX_IMAGE" and node.image:
        return _image_mean_rgb(node.image)
    if node.type in ("VERTEX_COLOR", "ATTRIBUTE"):
        attrs = getattr(obj.data, "color_attributes", None)
        if attrs and len(attrs):
            try:
                import numpy as np
                ca = attrs.get(getattr(node, "layer_name", "") or getattr(node, "attribute_name", "")) or \
                    attrs.active_color or attrs[0]
                buf = np.empty(len(ca.data) * 4, dtype=np.float32)
                ca.data.foreach_get("color", buf)
                return tuple(float(x) for x in buf.reshape(-1, 4)[:, :3].mean(axis=0))
            except Exception:
                return None
        return None
    if depth < 4:                          # follow mixes, hue/sat, gamma, reroutes ... to the first colour input
        for i in node.inputs:
            if i.type == "RGBA" and (i.is_linked or depth == 0):
                c = _socket_colour(i, obj, depth + 1)
                if c is not None:
                    return c
    return None


def object_colour(o):
    """Area-weighted mean albedo of an object's painterly materials (None when unknown)."""
    from .util import TOON_GROUP
    me = o.data if o.type == "MESH" else None
    counts = {}
    if me is not None and len(me.polygons):
        try:
            import numpy as np
            idx = np.empty(len(me.polygons), dtype=np.int32)
            me.polygons.foreach_get("material_index", idx)
            counts = {int(k): int(v) for k, v in zip(*np.unique(idx, return_counts=True))}
        except Exception:
            counts = {}
    acc, wsum = [0.0, 0.0, 0.0], 0.0
    for i, slot in enumerate(o.material_slots):
        m = slot.material
        if not m or not m.node_tree:
            continue
        grp = next((n for n in m.node_tree.nodes if n.type == "GROUP" and n.node_tree
                    and n.node_tree.name == TOON_GROUP), None)
        if grp is None:
            continue
        c = _socket_colour(grp.inputs["Base Color"], o)
        if c is None:
            continue
        w = counts.get(i, 1 if not counts else 0)
        if w == 0:
            continue
        for k in range(3):
            acc[k] += c[k] * w
        wsum += w
    return tuple(a / wsum for a in acc) if wsum else None


def store_ink_colours(objs):
    """Write each object's mean colour to custom properties read by the outline material."""
    n = 0
    for o in objs:
        if o.type != "MESH" or not o.is_editable:
            continue
        c = object_colour(o)
        if c is None:
            o[TAG + "_ink_on"] = 0.0
            continue
        o[TAG + "_ink"] = [max(0.0, min(1.0, x)) for x in c]
        o[TAG + "_ink_on"] = 1.0
        n += 1
    return n
