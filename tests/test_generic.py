"""Headless test: Painterly 2.5D on a scene it was never tuned for.
blender -b --factory-startup --python tests/test_generic.py -- <out_dir>"""
import bpy, sys, os, math
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import painterly_25d as P
P.register()
sc = bpy.context.scene
fails = []
def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg); (None if cond else fails.append(msg))

# default startup: Cube (material), Light (point 1000 W), Camera
cube = bpy.data.objects["Cube"]; cube.location = (-2.2, 0, 0)
# 1 no material sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8, location=(0, 0, 0)); sph = bpy.context.active_object
bpy.ops.object.shade_smooth(); sph.color = (0.9, 0.35, 0.3, 1)
# 2 text object
bpy.ops.object.text_add(location=(-1.5, -1.6, -0.9)); txt = bpy.context.active_object
txt.data.body = "P25D"; txt.data.extrude = 0.08; txt.rotation_euler = (math.radians(90), 0, 0)
# 3 bevelled curve
bpy.ops.curve.primitive_bezier_circle_add(radius=0.6, location=(2.2, 0, 0)); crv = bpy.context.active_object
crv.data.bevel_depth = 0.15; crv.rotation_euler = (math.radians(70), 0, 0)
# 4 vertex colour monkey without material
bpy.ops.mesh.primitive_monkey_add(size=1.2, location=(0, 2.2, 0.2)); mk = bpy.context.active_object
ca = mk.data.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
for i, d in enumerate(ca.data):
    d.color = (0.2 + 0.6 * (i % 7) / 7, 0.5, 0.9 - 0.6 * (i % 5) / 5, 1)
mk.data.color_attributes.active_color = ca
# 5 Diffuse BSDF + image texture (checker generated image)
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=1.2, location=(2.2, 2.2, 0)); cyl = bpy.context.active_object
m = bpy.data.materials.new("DiffuseImg"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
img = bpy.data.images.new("chk", 256, 256); img.generated_type = "COLOR_GRID"
ti = nt.nodes.new("ShaderNodeTexImage"); ti.image = img
df = nt.nodes.new("ShaderNodeBsdfDiffuse"); out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(ti.outputs[0], df.inputs["Color"]); nt.links.new(df.outputs[0], out.inputs["Surface"])
cyl.data.materials.append(m)
# 6 emission-only material
bpy.ops.mesh.primitive_ico_sphere_add(radius=0.35, location=(-2.2, 2.2, 0)); ico = bpy.context.active_object
me = bpy.data.materials.new("EmitOnly"); me.use_nodes = True; nt = me.node_tree; nt.nodes.clear()
em = nt.nodes.new("ShaderNodeEmission"); em.inputs[0].default_value = (1, 0.6, 0.2, 1); em.inputs[1].default_value = 3
o2 = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], o2.inputs["Surface"]); ico.data.materials.append(me)
# 7 collection instance of a cone
col = bpy.data.collections.new("Asset"); 
bpy.ops.mesh.primitive_cone_add(radius1=0.4, depth=0.9, location=(0, 0, 0)); cone = bpy.context.active_object
for c in cone.users_collection: c.objects.unlink(cone)
col.objects.link(cone)
inst = bpy.data.objects.new("ConeInstance", None); inst.instance_type = "COLLECTION"; inst.instance_collection = col
inst.location = (0, -2.2, -0.5); sc.collection.objects.link(inst)
# ground
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -1)); gnd = bpy.context.active_object
cam = bpy.data.objects["Camera"]; cam.location = (0, -10.5, 5.5); cam.rotation_euler = (math.radians(63), 0, 0)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 50
bpy.ops.object.select_all(action="DESELECT")

r = bpy.ops.p25d.apply_all()
check(r == {"FINISHED"}, "apply_all finished")
key = sc.p25d.key_light
check(key is not None and key.name == "Light" and bpy.data.objects.get("P25D Key Sun") is None,
      "existing point light used as key (no extra Sun)")
check(0.5 < sc.p25d.light_scale < 5, f"point-light Light Scale is irradiance at the subject ({sc.p25d.light_scale:.2f})")
check(sph.data.materials and sph.data.materials[0].get("p25d"), "material-less sphere got a toon material")
check(mk.data.materials and any(n.type == "VERTEX_COLOR" for n in mk.data.materials[0].node_tree.nodes), "vertex colours kept")
check(txt.data.materials and txt.data.materials[0].get("p25d"), "text object toonified")
check(crv.data.materials and crv.data.materials[0].get("p25d"), "curve object toonified")
grp = next(n for n in m.node_tree.nodes if n.type == "GROUP")
check(grp.inputs["Base Color"].is_linked and grp.inputs["Base Color"].links[0].from_node.type == "TEX_IMAGE", "diffuse+image base colour linked")
ge = next(n for n in me.node_tree.nodes if n.type == "GROUP")
check(tuple(round(x, 2) for x in ge.inputs["Base Color"].default_value[:3]) == (1.0, 0.6, 0.2), "emission colour used as base")
check(cone.data.materials and cone.data.materials[0].get("p25d"), "collection-instance object toonified")
check(cone.modifiers.get(P.OUTLINE_MOD if hasattr(P, "OUTLINE_MOD") else "P25D Outline") is not None, "collection-instance object outlined")
check(gnd.modifiers.get("P25D Outline") is None, "ground plane skipped by outline")
print("FIT stroke_scale", round(sc.p25d.stroke_scale, 2), "fog", round(sc.p25d.fog_start, 1), round(sc.p25d.fog_end, 1))
sc.render.filepath = OUT + "/generic_painted.png"; bpy.ops.render.render(write_still=True)

# tiny-object fit: scale everything by 0.05 and refit -> stroke scale should grow ~20x
s0 = sc.p25d.stroke_scale
for o in (cube, sph, txt, crv, mk, cyl, ico, inst, gnd): o.scale = tuple(x * 0.05 for x in o.scale); o.location = tuple(x * 0.05 for x in o.location)
cam.location = tuple(x * 0.05 for x in cam.location)
bpy.context.view_layer.update()
bpy.ops.p25d.fit_scene()
check(15 < sc.p25d.stroke_scale / s0 < 25, f"fit_to_scene scales strokes for tiny scene ({sc.p25d.stroke_scale / s0:.1f}x)")
sc.render.filepath = OUT + "/generic_tiny.png"; bpy.ops.render.render(write_still=True)

# presets
fit_fog = (sc.p25d.fog_start, sc.p25d.fog_end)
bad = []
for p in ("DAY", "CLEAN", "NIGHT", "GOLDEN", "PASTEL", "DEFAULT"):
    sc.p25d.preset = p
    if (sc.p25d.fog_start, sc.p25d.fog_end) != fit_fog:
        bad.append(p)
check(True, "all presets apply")
# presets must not overwrite the fitted fog distances (an absolute fog_start once fogged small products completely)
check(not bad, f"presets keep fitted fog distances (changed by: {bad})")

# 1.1: coloured ink, media, variation
check(sph.get("p25d_ink_on") == 1.0 and abs(sph["p25d_ink"][0] - 0.9) < 0.05, "object colour stored for coloured ink")
check(cyl.get("p25d_ink_on") == 1.0, "image-textured object colour stored")
ink = bpy.data.materials["P25D Outline Ink"].node_tree.nodes
check(ink.get("Ink Mix") is not None and abs(ink["Ink From Object"].outputs[0].default_value - sc.p25d.ink_from_object) < 1e-6,
      "outline ink mixes object colour")
pn = sc.compositing_node_group.nodes
check(all(pn.get(k) for k in ("Paint Wobble", "Edge Darken", "Granulation", "Paper Tooth", "Pattern Line")),
      "media nodes in compositor")
tg = bpy.data.node_groups["P25D Toon"].nodes
check(tg.get("Colour Jitter") is not None and tg.get("Stroke Rotation") is not None, "colour jitter / stroke angle in toon group")
snap = P.MEDIA["OIL"]
eq = lambda a, b: a == b if isinstance(b, str) else abs(a - b) < 1e-5
for med in ("WATERCOLOR", "CRAYON", "PENCIL", "ANIME", "GOUACHE"):
    sc.p25d.medium = med
    sc.render.filepath = f"{OUT}/medium_{med.lower()}.png"
    if med in ("WATERCOLOR", "CRAYON"):
        sc.p25d.fog_start, sc.p25d.fog_end = fit_fog
        bpy.ops.render.render(write_still=True)
check(eq(sc.p25d.edge_darken, 0.18) and sc.p25d.shadow_pattern == "DOTS", "medium sets its keys")
sc.p25d.medium = "OIL"
check(all(eq(getattr(sc.p25d, k), v) for k, v in snap.items()), "switching media back to oil is lossless")
before = {k: (tuple(getattr(sc.p25d, k)) if k in ("shadow_tint", "paper_color") else getattr(sc.p25d, k)) for k in P.VARY_KEYS}
bpy.ops.p25d.shuffle(); v1 = sc.p25d.variation; a1 = sc.p25d.stroke_angle
bpy.ops.p25d.shuffle(); bpy.ops.p25d.shuffle()
sc.p25d.variation = v1
check(v1 > 0 and abs(sc.p25d.stroke_angle - a1) < 1e-6, "variation is reproducible from its number")
sc.p25d.medium = "WATERCOLOR"; sc.p25d.medium = "OIL"
check(abs(sc.p25d.stroke_angle - a1) < 1e-6, "variation survives a medium round trip")
sc.p25d.variation = 0
after = {k: (tuple(getattr(sc.p25d, k)) if k in ("shadow_tint", "paper_color") else getattr(sc.p25d, k)) for k in P.VARY_KEYS}
check(all(abs(sum(x) - sum(y)) < 1e-5 if isinstance(x, tuple) else abs(x - y) < 1e-5 for x, y in
          ((before[k], after[k]) for k in P.VARY_KEYS)), "variation 0 restores the base look")

# translations
import bpy.app.translations as T
check(T.pgettext_iface("Make It Painterly", "Operator") is not None, "translations registered")

# revert
r = bpy.ops.p25d.revert()
check(sc.compositing_node_group is None, "revert restored compositor")
check(len(sph.data.materials) == 0, "revert removed auto material")
check(not m.get("p25d") and m.node_tree.nodes["Diffuse BSDF"].outputs[0].links[0].to_node.type == "OUTPUT_MATERIAL", "revert restored diffuse material")
check(all(o.modifiers.get("P25D Outline") is None for o in (cube, sph, mk, cyl, cone)), "revert removed outlines")
P.unregister()
check(True, "unregister clean")
print("RESULT", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
