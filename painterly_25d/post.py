# SPDX-License-Identifier: GPL-3.0-or-later
"""Painterly compositor group (Blender 5.x node-group compositor).

All pixel sizes are authored for a 1920 px long edge and rescaled *inside* the
graph from the image resolution, so viewport, any render % and any aspect ratio
match the final render.
"""
import bpy
from .util import (TAG, POST_GROUP, AOV_SHADOW, AOV_INK, sock, new, iface, menu, mix, mix_io,
                   math, vmath, ensure_aov)

VER = 6


def _out(node, name):
    return next(o for o in node.outputs if o.name == name)


def _is_post(ng):
    return ng is not None and ng.bl_idname == "CompositorNodeTree" and ng.get(TAG + "_ver") is not None


def scene_post(scene):
    """This scene's own painterly compositor (each scene needs its own Render Layers node)."""
    if _is_post(scene.compositing_node_group):
        return scene.compositing_node_group
    return next((g for g in bpy.data.node_groups if _is_post(g) and
                 any(n.type == "R_LAYERS" and n.scene == scene for n in g.nodes)), None)


def build_post(scene, rebuild=False):
    for vl in scene.view_layers:
        ensure_aov(vl, AOV_SHADOW)
        ensure_aov(vl, AOV_INK)
        vl.use_pass_z = True
    if scene.compositing_node_group and not _is_post(scene.compositing_node_group) \
            and TAG + "_prev_comp" not in scene:
        scene[TAG + "_prev_comp"] = scene.compositing_node_group.name
    ng = scene_post(scene)
    if ng is None or rebuild or ng.get(TAG + "_ver") != VER:
        if ng is None:
            ng = bpy.data.node_groups.new(POST_GROUP, "CompositorNodeTree")
        _build(ng, scene)
    scene.compositing_node_group = ng
    scene.render.use_compositing = True
    apply_post_settings(scene)
    return ng


def _value(N, loc, name, v=0.0):
    n = new(N, "ShaderNodeValue", loc, name)
    n.outputs[0].default_value = v
    return n.outputs[0]


def _build(ng, scene):
    ng.nodes.clear()
    ng.interface.clear()
    iface(ng, "Image", "OUTPUT", "NodeSocketColor")
    ng[TAG + "_ver"] = VER
    N, L = ng.nodes, ng.links
    X = -2800
    rl = new(N, "CompositorNodeRLayers", (X, 0), "Render")
    rl.scene = scene
    img = _out(rl, "Image")
    ic = new(N, "CompositorNodeImageCoordinates", (X, -800))
    L.new(img, ic.inputs[0])
    uni, pix = ic.outputs["Uniform"], ic.outputs["Pixel"]

    # resolution scale = max(w, h) / 1920
    info = new(N, "CompositorNodeImageInfo", (X, -1100))
    L.new(img, info.inputs[0])
    res = next(o for o in info.outputs if o.name in ("Resolution", "Size"))
    rsep = new(N, "ShaderNodeSeparateXYZ", (X + 180, -1100)); L.new(res, rsep.inputs[0])
    rmax = math(N, (X + 330, -1100), "MAXIMUM"); L.new(rsep.outputs[0], rmax.inputs[0]); L.new(rsep.outputs[1], rmax.inputs[1])
    rs = math(N, (X + 480, -1100), "DIVIDE", b=1920.0, label="Res Scale"); L.new(rmax.outputs[0], rs.inputs[0])
    RS = rs.outputs[0]

    def scaled(name, loc, v):
        val = _value(N, loc, name, v)
        m = math(N, (loc[0] + 150, loc[1]), "MULTIPLY")
        L.new(val, m.inputs[0]); L.new(RS, m.inputs[1])
        return m.outputs[0]

    # -- depth fog, objects only (sky depth is ~infinite) ----------------
    depth = next((o for o in rl.outputs if o.name == "Depth"), None)
    fogr = new(N, "ShaderNodeMapRange", (X + 250, -300), "Fog Range")
    fogr.clamp = True
    fogr.interpolation_type = "SMOOTHSTEP"
    fobj = math(N, (X + 250, -480), "LESS_THAN", b=500.0)
    if depth:
        L.new(depth, fogr.inputs["Value"]); L.new(depth, fobj.inputs[0])
    ff = math(N, (X + 420, -380), "MULTIPLY"); L.new(fogr.outputs["Result"], ff.inputs[0]); L.new(fobj.outputs[0], ff.inputs[1])
    fog = mix(N, (X + 450, 0), "MIX", label="Depth Fog")
    f, a, b, fog_out = mix_io(fog)
    L.new(ff.outputs[0], f); L.new(img, a)

    # -- two-pass Kuwahara (sizes scaled by resolution) -----------------
    k1 = new(N, "CompositorNodeKuwahara", (X + 650, 0), "Kuwahara Clean")
    menu(k1.inputs["Type"], "Classic", "CLASSIC")
    L.new(fog_out, k1.inputs["Image"])
    L.new(scaled("Clean Size", (X + 350, 300), 4.0), k1.inputs["Size"])
    k2 = new(N, "CompositorNodeKuwahara", (X + 850, 0), "Kuwahara Paint")
    menu(k2.inputs["Type"], "Anisotropic", "ANISOTROPIC")
    k2.inputs["Uniformity"].default_value = 4
    L.new(k1.outputs[0], k2.inputs["Image"])
    L.new(scaled("Paint Size", (X + 550, 450), 6.0), k2.inputs["Size"])
    km = mix(N, (X + 1050, 0), "MIX", label="Kuwahara Mix")
    f, a, b, kout = mix_io(km)
    L.new(fog_out, a); L.new(k2.outputs[0], b)

    # -- keep ink crisp ---------------------------------------------------
    ink = next((o for o in rl.outputs if o.name == AOV_INK), None)
    inkd = new(N, "CompositorNodeDilateErode", (X + 1050, -300), "Ink Dilate")
    try:
        menu(inkd.inputs["Type"], "Feather", "FEATHER")
        inkd.inputs["Size"].default_value = 2
    except KeyError:
        pass
    if ink:
        L.new(ink, inkd.inputs[0])
    inkf = math(N, (X + 1250, -300), "MULTIPLY", label="Ink Protect Amount", clamp=True)
    L.new(inkd.outputs[0], inkf.inputs[0])
    inkm = mix(N, (X + 1250, 0), "MIX", label="Ink Protect")
    f, a, b, iout = mix_io(inkm)
    L.new(inkf.outputs[0], f); L.new(kout, a); L.new(fog_out, b)

    # -- halftone dots in shadows (AOV = shadow amount, background 0) ---
    shadow = next((o for o in rl.outputs if o.name == AOV_SHADOW), None)
    rot = new(N, "ShaderNodeVectorRotate", (X + 1250, -1000))
    rot.rotation_type = "Z_AXIS"
    rot.inputs["Angle"].default_value = 0.785398
    L.new(pix, rot.inputs["Vector"])
    spacing = scaled("Dot Spacing", (X + 1100, -1300), 5.0)
    dsc = vmath(N, (X + 1400, -1000), "DIVIDE")
    L.new(rot.outputs[0], dsc.inputs[0]); L.new(spacing, dsc.inputs[1])
    dfr = vmath(N, (X + 1550, -1000), "FRACTION"); L.new(dsc.outputs[0], dfr.inputs[0])
    dce = vmath(N, (X + 1700, -1000), "SUBTRACT"); dce.inputs[1].default_value = (0.5, 0.5, 0.0)
    L.new(dfr.outputs[0], dce.inputs[0])
    dln = vmath(N, (X + 1850, -1000), "LENGTH"); L.new(dce.outputs[0], dln.inputs[0])
    # hatching / cross-hatching: distance to lines instead of to dot centres
    dxy = new(N, "ShaderNodeSeparateXYZ", (X + 1850, -700)); L.new(dce.outputs[0], dxy.inputs[0])
    ax = math(N, (X + 2000, -650), "ABSOLUTE"); L.new(dxy.outputs[0], ax.inputs[0])
    ay = math(N, (X + 2000, -750), "ABSOLUTE"); L.new(dxy.outputs[1], ay.inputs[0])
    cr = math(N, (X + 2150, -700), "MINIMUM"); L.new(ax.outputs[0], cr.inputs[0]); L.new(ay.outputs[0], cr.inputs[1])
    pc = new(N, "ShaderNodeMix", (X + 2300, -700), "Pattern Cross Mix"); pc.data_type = "FLOAT"
    L.new(_value(N, (X + 2150, -550), "Pattern Cross"), sock(pc.inputs, "Factor", "VALUE"))
    L.new(ax.outputs[0], sock(pc.inputs, "A", "VALUE")); L.new(cr.outputs[0], sock(pc.inputs, "B", "VALUE"))
    thin = math(N, (X + 2450, -700), "MULTIPLY", b=1.8); L.new(sock(pc.outputs, "Result", "VALUE"), thin.inputs[0])
    pl = new(N, "ShaderNodeMix", (X + 2600, -850), "Pattern Line Mix"); pl.data_type = "FLOAT"
    L.new(_value(N, (X + 2450, -550), "Pattern Line"), sock(pl.inputs, "Factor", "VALUE"))
    L.new(dln.outputs["Value"], sock(pl.inputs, "A", "VALUE")); L.new(thin.outputs[0], sock(pl.inputs, "B", "VALUE"))
    # radius grows with shadow depth: r = 0.18 + 0.14 * shadow
    rad = math(N, (X + 1550, -1250), "MULTIPLY_ADD", b=0.14); rad.inputs[2].default_value = 0.18
    if shadow:
        L.new(shadow, rad.inputs[0])
    aa = math(N, (X + 1550, -1400), "DIVIDE", a=0.7); L.new(spacing, aa.inputs[1])
    r0 = math(N, (X + 1700, -1300), "SUBTRACT"); L.new(rad.outputs[0], r0.inputs[0]); L.new(aa.outputs[0], r0.inputs[1])
    r1 = math(N, (X + 1700, -1400), "ADD"); L.new(rad.outputs[0], r1.inputs[0]); L.new(aa.outputs[0], r1.inputs[1])
    dot = new(N, "ShaderNodeMapRange", (X + 2000, -1100), "Dot AA")
    dot.interpolation_type = "SMOOTHSTEP"
    dot.inputs["To Min"].default_value = 1.0
    dot.inputs["To Max"].default_value = 0.0
    L.new(sock(pl.outputs, "Result", "VALUE"), dot.inputs["Value"])
    L.new(r0.outputs[0], dot.inputs["From Min"]); L.new(r1.outputs[0], dot.inputs["From Max"])
    sgate = new(N, "ShaderNodeMapRange", (X + 2000, -800), "Dot Shadow Gate")
    sgate.interpolation_type = "SMOOTHSTEP"
    sgate.inputs["From Min"].default_value = 0.5
    sgate.inputs["From Max"].default_value = 0.9
    if shadow:
        L.new(shadow, sgate.inputs["Value"])
    dmask = math(N, (X + 2150, -900), "MULTIPLY"); L.new(dot.outputs["Result"], dmask.inputs[0])
    L.new(sgate.outputs["Result"], dmask.inputs[1])
    dstr = math(N, (X + 2300, -900), "MULTIPLY", label="Dots Amount"); L.new(dmask.outputs[0], dstr.inputs[0])
    dots = mix(N, (X + 1450, 0), "MULTIPLY", label="Texture Dots")
    f, a, b, dout = mix_io(dots)
    L.new(dstr.outputs[0], f); L.new(iout, a)
    b.default_value = (0.35, 0.28, 0.45, 1.0)

    # -- media: wet-edge wobble, pigment pooling at edges, granulation ----
    wnz = new(N, "ShaderNodeTexNoise", (X + 1300, 700), "Wobble Noise")
    wnz.inputs["Scale"].default_value = 35.0
    wnz.inputs["Detail"].default_value = 3.0
    L.new(uni, wnz.inputs["Vector"])
    wsub = vmath(N, (X + 1450, 700), "SUBTRACT"); wsub.inputs[1].default_value = (0.5, 0.5, 0.5)
    L.new(wnz.outputs["Color"], wsub.inputs[0])
    wsc = vmath(N, (X + 1600, 700), "SCALE"); L.new(wsub.outputs[0], wsc.inputs[0])
    L.new(scaled("Wobble Px", (X + 1350, 900), 0.0), wsc.inputs["Scale"])
    disp = new(N, "CompositorNodeDisplace", (X + 1550, 0), "Paint Wobble")
    for nm in ("Extension X", "Extension Y"):
        if nm in disp.inputs:
            menu(disp.inputs[nm], "Extend", "EXTEND", "Clip")
    L.new(dout, disp.inputs["Image"]); L.new(wsc.outputs[0], disp.inputs["Displacement"])
    wob = disp.outputs[0]
    eblur = new(N, "CompositorNodeBlur", (X + 1550, 350), "Edge Blur")
    menu(eblur.inputs["Type"], "Gaussian", "GAUSS")
    esz = scaled("Edge Size", (X + 1300, 500), 5.0)
    ev = new(N, "ShaderNodeCombineXYZ", (X + 1450, 500)); L.new(esz, ev.inputs[0]); L.new(esz, ev.inputs[1])
    L.new(ev.outputs[0], eblur.inputs["Size"]); L.new(wob, eblur.inputs["Image"])
    ediff = vmath(N, (X + 1700, 350), "SUBTRACT"); L.new(wob, ediff.inputs[0]); L.new(eblur.outputs[0], ediff.inputs[1])
    elen = vmath(N, (X + 1850, 350), "LENGTH"); L.new(ediff.outputs[0], elen.inputs[0])
    eamp = math(N, (X + 2000, 350), "MULTIPLY", b=5.0, clamp=True); L.new(elen.outputs["Value"], eamp.inputs[0])
    eamt = math(N, (X + 2150, 350), "MULTIPLY", label="Edge Darken Amount"); L.new(eamp.outputs[0], eamt.inputs[0])
    edk = mix(N, (X + 1700, 0), "MULTIPLY", label="Edge Darken")          # pooled pigment = colour x itself
    f, a, b, edout = mix_io(edk)
    L.new(eamt.outputs[0], f); L.new(wob, a); L.new(wob, b)
    gnz = new(N, "ShaderNodeTexNoise", (X + 1850, 700), "Granulation Noise")
    gnz.inputs["Scale"].default_value = 160.0
    gnz.inputs["Detail"].default_value = 8.0
    gnz.inputs["Roughness"].default_value = 0.8
    L.new(uni, gnz.inputs["Vector"])
    gmr = new(N, "ShaderNodeMapRange", (X + 2000, 700)); gmr.interpolation_type = "SMOOTHSTEP"
    gmr.inputs["From Min"].default_value = 0.45; gmr.inputs["From Max"].default_value = 0.72
    L.new(gnz.outputs["Fac"], gmr.inputs["Value"])
    gamt = math(N, (X + 2150, 700), "MULTIPLY", label="Granulation Amount"); L.new(gmr.outputs["Result"], gamt.inputs[0])
    gra = mix(N, (X + 1850, 0), "MULTIPLY", label="Granulation")
    f, a, b, grout = mix_io(gra)
    L.new(gamt.outputs[0], f); L.new(edout, a); L.new(edout, b)

    # -- bloom + halation (glare-only, tinted) --------------------------
    gl = new(N, "CompositorNodeGlare", (X + 2000, 0), "Bloom")
    menu(gl.inputs["Type"], "Bloom", "BLOOM", "Fog Glow")
    menu(gl.inputs["Quality"], "High", "HIGH", "Medium")
    gl.inputs["Tint"].default_value = (1.0, 0.43, 0.16, 1.0)
    L.new(grout, gl.inputs["Image"])
    hb = new(N, "CompositorNodeBlur", (X + 1850, -300), "Halation Blur")
    menu(hb.inputs["Type"], "Gaussian", "GAUSS")
    glare_only = next((o for o in gl.outputs if o.name == "Glare"), _out(gl, "Image"))
    L.new(glare_only, hb.inputs["Image"])
    hsz = scaled("Halation Size", (X + 1600, -500), 25.0)
    hv = new(N, "ShaderNodeCombineXYZ", (X + 1800, -500)); L.new(hsz, hv.inputs[0]); L.new(hsz, hv.inputs[1])
    L.new(hv.outputs[0], hb.inputs["Size"])
    htint = mix(N, (X + 2000, -300), "MULTIPLY", label="Halation Tint")
    f, a, b, htout = mix_io(htint)
    f.default_value = 1.0
    L.new(hb.outputs[0], a)
    b.default_value = (1.0, 0.35, 0.2, 1.0)
    hal = mix(N, (X + 1850, 0), "SCREEN", label="Halation")
    f, a, b, hout = mix_io(hal)
    L.new(_out(gl, "Image"), a); L.new(htout, b)

    # -- paper -----------------------------------------------------------
    fib = new(N, "ShaderNodeTexNoise", (X + 1850, -1600), "Paper Fibre")
    fib.inputs["Scale"].default_value = 260.0
    fib.inputs["Detail"].default_value = 6.0
    fib.inputs["Roughness"].default_value = 0.7
    L.new(uni, fib.inputs["Vector"])
    blot = new(N, "ShaderNodeTexNoise", (X + 1850, -1850), "Paper Blotch")
    blot.inputs["Scale"].default_value = 2.5
    blot.inputs["Detail"].default_value = 3.0
    L.new(uni, blot.inputs["Vector"])
    pm = math(N, (X + 2050, -1700), "MULTIPLY_ADD", b=0.35)
    L.new(blot.outputs["Fac"], pm.inputs[0]); L.new(fib.outputs["Fac"], pm.inputs[2])
    pr = new(N, "ShaderNodeMapRange", (X + 2200, -1700))
    pr.inputs["From Min"].default_value = 0.675 - 0.35
    pr.inputs["From Max"].default_value = 0.675 + 0.35
    L.new(pm.outputs[0], pr.inputs["Value"])
    pap = mix(N, (X + 2050, 0), "OVERLAY", label="Paper")
    f, a, b, pout = mix_io(pap)
    L.new(hout, a); L.new(pr.outputs["Result"], b)
    pt = mix(N, (X + 2250, 0), "MULTIPLY", label="Paper Tint")
    f, a, b, ptout = mix_io(pt)
    L.new(pout, a)

    # -- paper tooth: paper shows through the grain (crayon / pencil), more in light areas
    trot = new(N, "ShaderNodeVectorRotate", (X + 2050, -2600)); trot.rotation_type = "Z_AXIS"
    trot.inputs["Angle"].default_value = 0.55
    L.new(uni, trot.inputs["Vector"])
    tst = vmath(N, (X + 2200, -2600), "MULTIPLY"); tst.inputs[1].default_value = (1.0, 0.09, 1.0)
    L.new(trot.outputs[0], tst.inputs[0])
    tnz = new(N, "ShaderNodeTexNoise", (X + 2350, -2600), "Tooth Noise")
    tnz.inputs["Scale"].default_value = 230.0
    tnz.inputs["Detail"].default_value = 3.0
    tnz.inputs["Roughness"].default_value = 0.65
    L.new(tst.outputs[0], tnz.inputs["Vector"])
    tsum = math(N, (X + 2500, -2600), "MULTIPLY_ADD", b=0.6); L.new(tnz.outputs["Fac"], tsum.inputs[0])
    L.new(fib.outputs["Fac"], tsum.inputs[2])
    tsum2 = math(N, (X + 2600, -2600), "MULTIPLY", b=0.625); L.new(tsum.outputs[0], tsum2.inputs[0])
    try:
        lum = new(N, "CompositorNodeRGBToBW", (X + 2350, -2350))
    except RuntimeError:
        lum = new(N, "ShaderNodeRGBToBW", (X + 2350, -2350))
    L.new(ptout, lum.inputs[0])
    # paper shows at the grain peaks only; dark (heavily pressed) areas need a higher peak
    thr = math(N, (X + 2500, -2350), "MULTIPLY_ADD", b=-0.12); thr.inputs[2].default_value = 0.64
    L.new(lum.outputs[0], thr.inputs[0])
    thr2 = math(N, (X + 2650, -2350), "ADD", b=0.05); L.new(thr.outputs[0], thr2.inputs[0])
    tmr = new(N, "ShaderNodeMapRange", (X + 2800, -2450)); tmr.interpolation_type = "SMOOTHSTEP"
    L.new(tsum2.outputs[0], tmr.inputs["Value"]); L.new(thr.outputs[0], tmr.inputs["From Min"])
    L.new(thr2.outputs[0], tmr.inputs["From Max"])
    tamt = math(N, (X + 2950, -2450), "MULTIPLY", label="Paper Tooth Amount"); L.new(tmr.outputs["Result"], tamt.inputs[0])
    tooth = mix(N, (X + 2350, 0), "MIX", label="Paper Tooth")
    f, a, b, toout = mix_io(tooth)
    L.new(tamt.outputs[0], f); L.new(ptout, a)
    ptout = toout

    # -- sensor dust: sparse, varied size, soft ---------------------------
    dv = new(N, "ShaderNodeTexVoronoi", (X + 2250, -2100), "Dust Voronoi")
    dv.inputs["Scale"].default_value = 9.0
    L.new(uni, dv.inputs["Vector"])
    dsep = new(N, "CompositorNodeSeparateColor", (X + 2450, -2250)); L.new(dv.outputs["Color"], dsep.inputs[0])
    keep = math(N, (X + 2600, -2250), "GREATER_THAN", b=0.85); L.new(dsep.outputs[0], keep.inputs[0])
    drad = new(N, "ShaderNodeMapRange", (X + 2600, -2400))
    drad.inputs["To Min"].default_value = 0.006; drad.inputs["To Max"].default_value = 0.02
    L.new(dsep.outputs[1], drad.inputs["Value"])
    dsoft = new(N, "ShaderNodeMapRange", (X + 2800, -2100)); dsoft.interpolation_type = "SMOOTHSTEP"
    dsoft.inputs["From Min"].default_value = 0.0
    dsoft.inputs["To Min"].default_value = 1.0; dsoft.inputs["To Max"].default_value = 0.0
    L.new(dv.outputs["Distance"], dsoft.inputs["Value"]); L.new(drad.outputs["Result"], dsoft.inputs["From Max"])
    dk = math(N, (X + 2950, -2150), "MULTIPLY"); L.new(dsoft.outputs["Result"], dk.inputs[0]); L.new(keep.outputs[0], dk.inputs[1])
    dd = math(N, (X + 3100, -2150), "MULTIPLY", label="Dust Amount"); L.new(dk.outputs[0], dd.inputs[0])
    dust = mix(N, (X + 2450, 0), "SCREEN", label="Sensor Dust")
    f, a, b, duout = mix_io(dust)
    L.new(dd.outputs[0], f); L.new(ptout, a)
    b.default_value = (0.9, 0.85, 0.75, 1.0)

    # -- film grain (per pixel, animated) -------------------------------
    st = new(N, "CompositorNodeSceneTime", (X + 2450, -2600))
    wn = new(N, "ShaderNodeTexWhiteNoise", (X + 2650, -2600), "Grain Noise")
    wn.noise_dimensions = "4D"
    L.new(pix, wn.inputs["Vector"]); L.new(st.outputs["Frame"], wn.inputs["W"])
    grain = mix(N, (X + 2650, 0), "OVERLAY", label="Grain")
    f, a, b, gout = mix_io(grain)
    L.new(duout, a); L.new(wn.outputs["Value"], b)

    # -- chromatic aberration with a tiny overscan (no edge fringe) -------
    lens = new(N, "CompositorNodeLensdist", (X + 2850, 0), "Aberration")
    lens.inputs["Fit"].default_value = False
    L.new(gout, lens.inputs["Image"])
    ovs = new(N, "CompositorNodeTransform", (X + 3000, 0), "Overscan")
    ovs.inputs["Scale"].default_value = 1.006
    L.new(lens.outputs[0], ovs.inputs["Image"])

    # -- vignette ----------------------------------------------------------
    vl_ = vmath(N, (X + 2900, -400), "LENGTH"); L.new(uni, vl_.inputs[0])
    vr = new(N, "ShaderNodeMapRange", (X + 3050, -400), "Vignette Falloff")
    vr.interpolation_type = "SMOOTHSTEP"
    vr.inputs["From Min"].default_value = 0.45
    vr.inputs["From Max"].default_value = 1.15
    L.new(vl_.outputs["Value"], vr.inputs["Value"])
    vf = math(N, (X + 3200, -400), "MULTIPLY", label="Vignette Amount"); L.new(vr.outputs["Result"], vf.inputs[0])
    vig = mix(N, (X + 3150, 0), "MULTIPLY", label="Vignette")
    f, a, b, vout = mix_io(vig)
    L.new(vf.outputs[0], f); L.new(ovs.outputs[0], a)

    # -- grade -------------------------------------------------------------
    bc = new(N, "CompositorNodeBrightContrast", (X + 3350, 0), "Contrast")
    L.new(vout, bc.inputs["Image"])
    lift = mix(N, (X + 3550, 0), "SCREEN", label="Black Lift")
    f, a, b, lout = mix_io(lift)
    f.default_value = 1.0
    L.new(bc.outputs[0], a)
    grade = new(N, "CompositorNodeColorBalance", (X + 3750, 0), "Grade")
    L.new(lout, grade.inputs["Image"])
    sat = new(N, "CompositorNodeHueSat", (X + 3950, 0), "Saturation")
    L.new(grade.outputs[0], sat.inputs["Image"])
    go = new(N, "NodeGroupOutput", (X + 4150, 0))
    L.new(sat.outputs[0], go.inputs["Image"])


def apply_post_settings(scene):
    s = scene.p25d
    ng = scene.compositing_node_group
    if not _is_post(ng):
        return
    n = ng.nodes

    def setin(node, name, val, kind=None):
        nd = n.get(node)
        if nd is None:
            return
        try:
            (sock(nd.inputs, name, kind) if kind else nd.inputs[name]).default_value = val
        except (KeyError, TypeError, ValueError):
            pass

    def setval(node, val):
        nd = n.get(node)
        if nd is not None:
            nd.outputs[0].default_value = val

    col = lambda c: tuple(c) + (1.0,)
    setin("Fog Range", "From Min", s.fog_start)
    # Map Range with From Min > From Max inverts and fogs the whole frame; keep the end beyond the start
    setin("Fog Range", "From Max", max(s.fog_end, s.fog_start + 0.01))
    setin("Fog Range", "To Max", s.fog_amount)
    setin("Depth Fog", "B", col(s.fog_color), "RGBA")
    setval("Clean Size", float(s.kuwahara_clean))
    setval("Paint Size", float(s.kuwahara_size))
    setin("Kuwahara Paint", "Sharpness", s.kuwahara_sharpness)
    setin("Kuwahara Paint", "Eccentricity", s.kuwahara_eccentricity)
    setin("Kuwahara Mix", "Factor", s.kuwahara_mix, "VALUE")
    setin("Ink Protect Amount", 1, s.ink_protect)
    setval("Dot Spacing", s.dots_size)
    pat = getattr(s, "shadow_pattern", "DOTS")
    setval("Pattern Line", 0.0 if pat == "DOTS" else 1.0)
    setval("Pattern Cross", 1.0 if pat == "CROSS" else 0.0)
    setval("Wobble Px", s.paint_wobble)
    setin("Edge Darken Amount", 1, s.edge_darken)
    setin("Granulation Amount", 1, s.granulation * 0.7)
    setin("Paper Tooth Amount", 1, s.paper_tooth)
    setin("Paper Tooth", "B", col(s.paper_color), "RGBA")
    if n.get("Paint Wobble"):
        n["Paint Wobble"].mute = s.paint_wobble <= 0.0
    if n.get("Edge Blur"):
        n["Edge Blur"].mute = s.edge_darken <= 0.0
    setin("Dots Amount", 1, s.dots_strength)
    setin("Texture Dots", "B", col(s.dots_color), "RGBA")
    setin("Bloom", "Threshold", s.bloom_threshold)
    setin("Bloom", "Strength", s.bloom_strength)
    setin("Bloom", "Size", s.bloom_size)
    setin("Halation", "Factor", s.halation, "VALUE")
    setin("Paper", "Factor", s.paper_strength, "VALUE")
    setin("Paper Tint", "Factor", s.paper_tint, "VALUE")
    setin("Paper Tint", "B", col(s.paper_color), "RGBA")
    setin("Dust Amount", 1, s.dust)
    setin("Grain", "Factor", s.grain_strength, "VALUE")
    setin("Aberration", "Dispersion", s.aberration)
    setin("Vignette Amount", 1, s.vignette)
    setin("Vignette", "B", col(s.vignette_color), "RGBA")
    setin("Contrast", "Contrast", s.contrast * 100.0)
    setin("Black Lift", "B", col(s.black_lift), "RGBA")
    setin("Saturation", "Saturation", s.saturation)
    g = n.get("Grade")
    if g:
        try:
            w = s.warmth
            sock(g.inputs, "Gain", "RGBA").default_value = (1.0 + w * 0.08, 1.0, 1.0 - w * 0.08, 1.0)
            sock(g.inputs, "Gamma", "RGBA").default_value = (1.0 + w * 0.02, 1.0, 1.0 - w * 0.02, 1.0)
        except KeyError:
            pass
    for name in ("Kuwahara Clean", "Kuwahara Paint"):
        if n.get(name):
            n[name].mute = not s.post_kuwahara


def remove_post(scene):
    prev = scene.get(TAG + "_prev_comp")
    scene.compositing_node_group = bpy.data.node_groups.get(prev) if prev else None
    if TAG + "_prev_comp" in scene:
        del scene[TAG + "_prev_comp"]
