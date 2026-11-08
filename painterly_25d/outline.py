# SPDX-License-Identifier: GPL-3.0-or-later
"""Hand-drawn inverted-hull outline (Geometry Nodes)."""
import bpy
from .util import (TAG, OUTLINE_GROUP, OUTLINE_MAT, OUTLINE_MOD, AOV_INK, sock, new, iface,
                   math, vmath)


INK_VER = 2


def build_outline_material():
    """Emission ink. Colour = scene ink colour mixed with a darkened copy of each object's own
    colour (custom property "p25d_ink", written by Make It Painterly) -> coloured lines."""
    mat = bpy.data.materials.get(OUTLINE_MAT) or bpy.data.materials.new(OUTLINE_MAT)
    if hasattr(mat, "use_nodes") and not mat.node_tree:
        mat.use_nodes = True
    mat.use_backface_culling = True
    if hasattr(mat, "use_backface_culling_shadow"):
        mat.use_backface_culling_shadow = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = new(nt.nodes, "ShaderNodeOutputMaterial", (400, 0))
    em = new(nt.nodes, "ShaderNodeEmission", (100, 80), "Ink")
    N, L = nt.nodes, nt.links
    oc = new(N, "ShaderNodeAttribute", (-900, 200), "Object Colour")
    oc.attribute_type = "OBJECT"; oc.attribute_name = "p25d_ink"
    on = new(N, "ShaderNodeAttribute", (-900, 0), "Object Colour Set")
    on.attribute_type = "OBJECT"; on.attribute_name = "p25d_ink_on"
    dk = new(N, "ShaderNodeHueSaturation", (-650, 200), "Ink Darken")
    dk.inputs["Saturation"].default_value = 1.25
    dk.inputs["Value"].default_value = 0.4
    L.new(oc.outputs["Color"], dk.inputs["Color"])
    amt = new(N, "ShaderNodeValue", (-650, -50), "Ink From Object")
    fac = math(N, (-450, 0), "MULTIPLY"); L.new(on.outputs["Fac"], fac.inputs[0]); L.new(amt.outputs[0], fac.inputs[1])
    mx = new(N, "ShaderNodeMix", (-250, 100), "Ink Mix"); mx.data_type = "RGBA"
    L.new(fac.outputs[0], sock(mx.inputs, "Factor", "VALUE"))
    sock(mx.inputs, "A", "RGBA").default_value = (0.04, 0.015, 0.008, 1.0)
    L.new(dk.outputs[0], sock(mx.inputs, "B", "RGBA"))
    L.new(sock(mx.outputs, "Result", "RGBA"), em.inputs["Color"])
    lp = new(nt.nodes, "ShaderNodeLightPath", (-150, 250))
    tr = new(nt.nodes, "ShaderNodeBsdfTransparent", (100, -80))
    ms = new(nt.nodes, "ShaderNodeMixShader", (260, 0))
    nt.links.new(lp.outputs["Is Shadow Ray"], ms.inputs[0])
    nt.links.new(em.outputs[0], ms.inputs[1])
    nt.links.new(tr.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs["Surface"])
    aov = new(nt.nodes, "ShaderNodeOutputAOV", (400, -200), "P25D AOV")
    aov.aov_name = AOV_INK
    aov.inputs["Value"].default_value = 1.0
    mat[TAG + "_ver"] = INK_VER
    return mat


def build_outline_group(rebuild=False):
    ng = bpy.data.node_groups.get(OUTLINE_GROUP)
    if ng and not rebuild and ng.get(TAG + "_ver") == 4:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(OUTLINE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.nodes.clear()
    ng.interface.clear()
    iface(ng, "Geometry", "INPUT", "NodeSocketGeometry")
    iface(ng, "Thickness", "INPUT", "NodeSocketFloat", 0.006, 0.0, 1.0)
    iface(ng, "Screen Space", "INPUT", "NodeSocketFloat", 1.0, 0.0, 1.0)
    iface(ng, "Reference Distance", "INPUT", "NodeSocketFloat", 6.0, 0.01, 1000.0)
    iface(ng, "Fade Distance", "INPUT", "NodeSocketFloat", 30.0, 0.01, 10000.0)
    iface(ng, "Fade Min", "INPUT", "NodeSocketFloat", 0.35, 0.0, 1.0)
    iface(ng, "Jitter", "INPUT", "NodeSocketFloat", 0.7, 0.0, 1.0)
    iface(ng, "Jitter Scale", "INPUT", "NodeSocketFloat", 3.0, 0.0, 100.0)
    iface(ng, "Boil", "INPUT", "NodeSocketFloat", 1.0, 0.0, 1.0)
    iface(ng, "Boil Rate", "INPUT", "NodeSocketFloat", 2.0, 1.0, 24.0)
    iface(ng, "Camera Push", "INPUT", "NodeSocketFloat", 1.5, 0.0, 10.0)
    iface(ng, "Weld Seams", "INPUT", "NodeSocketBool", True)
    iface(ng, "Material", "INPUT", "NodeSocketMaterial")
    iface(ng, "Geometry", "OUTPUT", "NodeSocketGeometry")
    ng[TAG + "_ver"] = 4
    N, L = ng.nodes, ng.links
    gi = new(N, "NodeGroupInput", (-1600, 0))
    go = new(N, "NodeGroupOutput", (1000, 0))
    I = lambda n: gi.outputs[n]

    merge = new(N, "GeometryNodeMergeByDistance", (-1300, -150))
    merge.inputs["Distance"].default_value = 0.0005
    L.new(I("Geometry"), merge.inputs["Geometry"])
    weld = new(N, "GeometryNodeSwitch", (-1150, -150), "Weld Switch")
    weld.input_type = "GEOMETRY"
    L.new(I("Weld Seams"), weld.inputs["Switch"])
    L.new(I("Geometry"), weld.inputs["False"])
    L.new(merge.outputs[0], weld.inputs["True"])

    pos = new(N, "GeometryNodeInputPosition", (-1400, -400))
    nrm = new(N, "GeometryNodeInputNormal", (-1400, -300))
    cam = new(N, "GeometryNodeInputActiveCamera", (-1600, -600))
    oi = new(N, "GeometryNodeObjectInfo", (-1400, -600))
    oi.transform_space = "RELATIVE"
    L.new(cam.outputs[0], oi.inputs["Object"])
    rel = vmath(N, (-1200, -500), "SUBTRACT")
    L.new(pos.outputs[0], rel.inputs[0]); L.new(oi.outputs["Location"], rel.inputs[1])
    # world scale of this object (incl. parents): distances/widths are authored in world units,
    # the hull is built in object space -> convert with the mean absolute world scale
    selfo = new(N, "GeometryNodeSelfObject", (-1800, -800))
    soi = new(N, "GeometryNodeObjectInfo", (-1600, -800))
    soi.transform_space = "ORIGINAL"
    L.new(selfo.outputs[0], soi.inputs["Object"])
    sab = vmath(N, (-1450, -800), "ABSOLUTE"); L.new(soi.outputs["Scale"], sab.inputs[0])
    sdot = vmath(N, (-1300, -800), "DOT_PRODUCT"); L.new(sab.outputs[0], sdot.inputs[0])
    sdot.inputs[1].default_value = (1 / 3, 1 / 3, 1 / 3)
    wsc = math(N, (-1150, -800), "MAXIMUM", b=1e-8, label="World Scale"); L.new(sdot.outputs["Value"], wsc.inputs[0])
    WS = wsc.outputs[0]
    dl = vmath(N, (-1050, -650), "LENGTH")
    L.new(rel.outputs[0], dl.inputs[0])
    dist = math(N, (-950, -600), "MULTIPLY", label="World Distance")
    L.new(dl.outputs["Value"], dist.inputs[0]); L.new(WS, dist.inputs[1])
    away = vmath(N, (-1050, -450), "NORMALIZE")
    L.new(rel.outputs[0], away.inputs[0])

    # constant screen width
    dr = math(N, (-900, -650), "DIVIDE")
    L.new(dist.outputs[0], dr.inputs[0]); L.new(I("Reference Distance"), dr.inputs[1])
    ss = new(N, "ShaderNodeMix", (-750, -650)); ss.data_type = "FLOAT"
    L.new(I("Screen Space"), sock(ss.inputs, "Factor", "VALUE"))
    sock(ss.inputs, "A", "VALUE").default_value = 1.0
    L.new(dr.outputs[0], sock(ss.inputs, "B", "VALUE"))
    # fade with distance
    fade = new(N, "ShaderNodeMapRange", (-750, -850), "Distance Fade")
    fade.clamp = True
    L.new(dist.outputs[0], fade.inputs["Value"])
    L.new(I("Reference Distance"), fade.inputs["From Min"])
    L.new(I("Fade Distance"), fade.inputs["From Max"])
    fade.inputs["To Min"].default_value = 1.0
    L.new(I("Fade Min"), fade.inputs["To Max"])

    # boil on twos: W = floor(frame / rate) * boil
    st = new(N, "GeometryNodeInputSceneTime", (-1400, -1100))
    fr = math(N, (-1250, -1100), "DIVIDE"); L.new(st.outputs["Frame"], fr.inputs[0]); L.new(I("Boil Rate"), fr.inputs[1])
    fl = math(N, (-1100, -1100), "FLOOR"); L.new(fr.outputs[0], fl.inputs[0])
    fw = math(N, (-950, -1100), "MULTIPLY", b=1.37); L.new(fl.outputs[0], fw.inputs[0])
    fb = math(N, (-800, -1100), "MULTIPLY"); L.new(fw.outputs[0], fb.inputs[0]); L.new(I("Boil"), fb.inputs[1])
    nz = new(N, "ShaderNodeTexNoise", (-650, -1050), "Line Noise")
    nz.noise_dimensions = "4D"
    nz.inputs["Detail"].default_value = 1.5
    wpos = vmath(N, (-800, -1000), "SCALE"); L.new(pos.outputs[0], wpos.inputs[0]); L.new(WS, wpos.inputs["Scale"])
    L.new(wpos.outputs[0], nz.inputs["Vector"])
    L.new(fb.outputs[0], nz.inputs["W"])
    L.new(I("Jitter Scale"), nz.inputs["Scale"])
    nr = new(N, "ShaderNodeMapRange", (-450, -1050), "Line Breakup")
    nr.clamp = True
    nr.inputs["From Min"].default_value = 0.35
    nr.inputs["From Max"].default_value = 0.62
    nr.inputs["To Min"].default_value = 0.05
    nr.inputs["To Max"].default_value = 1.35
    L.new(nz.outputs["Fac"], nr.inputs["Value"])
    jm = new(N, "ShaderNodeMix", (-300, -1000)); jm.data_type = "FLOAT"
    L.new(I("Jitter"), sock(jm.inputs, "Factor", "VALUE"))
    sock(jm.inputs, "A", "VALUE").default_value = 1.0
    L.new(nr.outputs["Result"], sock(jm.inputs, "B", "VALUE"))

    t1 = math(N, (-500, -650), "MULTIPLY")
    L.new(I("Thickness"), t1.inputs[0]); L.new(sock(ss.outputs, "Result", "VALUE"), t1.inputs[1])
    t2 = math(N, (-350, -700), "MULTIPLY"); L.new(t1.outputs[0], t2.inputs[0]); L.new(fade.outputs["Result"], t2.inputs[1])
    t3 = math(N, (-150, -750), "MULTIPLY"); L.new(t2.outputs[0], t3.inputs[0]); L.new(sock(jm.outputs, "Result", "VALUE"), t3.inputs[1])

    t3l = math(N, (-50, -750), "DIVIDE", label="To Object Space"); L.new(t3.outputs[0], t3l.inputs[0]); L.new(WS, t3l.inputs[1])
    off_n = vmath(N, (0, -400), "SCALE"); L.new(nrm.outputs[0], off_n.inputs[0]); L.new(t3l.outputs[0], off_n.inputs["Scale"])
    pushw = math(N, (-100, -650), "MULTIPLY"); L.new(t2.outputs[0], pushw.inputs[0]); L.new(I("Camera Push"), pushw.inputs[1])
    pushf = math(N, (0, -650), "DIVIDE"); L.new(pushw.outputs[0], pushf.inputs[0]); L.new(WS, pushf.inputs[1])
    off_c = vmath(N, (150, -550), "SCALE"); L.new(away.outputs[0], off_c.inputs[0]); L.new(pushf.outputs[0], off_c.inputs["Scale"])
    off = vmath(N, (300, -450), "ADD"); L.new(off_n.outputs[0], off.inputs[0]); L.new(off_c.outputs[0], off.inputs[1])

    setp = new(N, "GeometryNodeSetPosition", (400, -150))
    L.new(weld.outputs[0], setp.inputs["Geometry"])
    L.new(off.outputs[0], setp.inputs["Offset"])
    flip = new(N, "GeometryNodeFlipFaces", (580, -150)); L.new(setp.outputs[0], flip.inputs[0])
    smat = new(N, "GeometryNodeSetMaterial", (740, -150))
    L.new(flip.outputs[0], smat.inputs["Geometry"]); L.new(I("Material"), smat.inputs["Material"])
    join = new(N, "GeometryNodeJoinGeometry", (880, 0))
    L.new(smat.outputs[0], join.inputs[0]); L.new(I("Geometry"), join.inputs[0])
    L.new(join.outputs[0], go.inputs["Geometry"])
    return ng


def set_mod_input(mod, name, value):
    for item in mod.node_group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.name == name:
            props = getattr(mod, "properties", None)          # Blender 5.x
            if props is not None and hasattr(props, "inputs"):
                getattr(props.inputs, item.identifier).value = value
            else:                                             # Blender 4.x
                mod[item.identifier] = value
            return True
    return False


def is_flat_plane(obj):
    """Test the original (un-modified) mesh, so displaced ground planes still count."""
    vs = obj.data.vertices
    if not vs or len(obj.data.polygons) > 256:
        return False
    zs = [v.co.z for v in vs]
    xs = [v.co.x for v in vs]
    return (max(zs) - min(zs)) < 1e-4 * max(1e-6, max(xs) - min(xs)) + 1e-6


def add_outline(obj, scene):
    if obj.type != "MESH" or obj.get(TAG + "_skip") or not obj.is_editable or is_flat_plane(obj):
        return False
    build_outline_group()
    mat = bpy.data.materials.get(OUTLINE_MAT)
    if mat is None or mat.get(TAG + "_ver") != INK_VER:
        mat = build_outline_material()
    mod = obj.modifiers.get(OUTLINE_MOD) or obj.modifiers.new(OUTLINE_MOD, "NODES")
    mod.node_group = bpy.data.node_groups[OUTLINE_GROUP]
    set_mod_input(mod, "Material", mat)
    apply_outline_settings(scene, [obj])
    return True


def remove_outline(obj):
    if not obj.is_editable:
        return
    mod = obj.modifiers.get(OUTLINE_MOD)
    if mod:
        obj.modifiers.remove(mod)
    if obj.type == "MESH":   # clean up slot left by v1
        for i, m in reversed(list(enumerate(obj.data.materials))):
            if m and m.name == OUTLINE_MAT:
                obj.data.materials.pop(index=i)


def apply_outline_settings(scene, objs=None):
    s = scene.p25d
    mat = bpy.data.materials.get(OUTLINE_MAT)
    if mat and mat.node_tree:
        nodes = mat.node_tree.nodes
        mx, amt = nodes.get("Ink Mix"), nodes.get("Ink From Object")
        if mx is not None:
            sock(mx.inputs, "A", "RGBA").default_value = tuple(s.outline_color) + (1.0,)
        elif nodes.get("Ink"):                                  # 1.0 material
            nodes["Ink"].inputs["Color"].default_value = tuple(s.outline_color) + (1.0,)
        if amt is not None:
            amt.outputs[0].default_value = s.ink_from_object
    if not objs:      # scene objects plus objects only reachable through collection instances
        from .autosetup import expand
        objs = [o for o in expand(scene.objects) if o.modifiers.get(OUTLINE_MOD)]
    for o in objs:
        mod = o.modifiers.get(OUTLINE_MOD)
        if not mod or not mod.node_group:
            continue
        ov = getattr(o, "p25d_obj", None)
        scale = ov.outline_scale if (ov and ov.use_override) else 1.0
        enabled = s.outline_enable and not (ov and ov.use_override and not ov.outline_enable)
        set_mod_input(mod, "Thickness", s.outline_thickness * scale)
        set_mod_input(mod, "Screen Space", 1.0 if s.outline_screen_space else 0.0)
        set_mod_input(mod, "Reference Distance", s.outline_ref_distance)
        set_mod_input(mod, "Fade Distance", s.outline_fade_distance)
        set_mod_input(mod, "Fade Min", s.outline_fade_min)
        set_mod_input(mod, "Jitter", s.outline_jitter)
        set_mod_input(mod, "Jitter Scale", s.outline_jitter_scale)
        set_mod_input(mod, "Boil", 1.0 if s.outline_boil else 0.0)
        set_mod_input(mod, "Boil Rate", float(s.boil_rate))
        set_mod_input(mod, "Weld Seams", bool(s.outline_weld))
        mod.show_viewport = mod.show_render = enabled
        o.update_tag()
