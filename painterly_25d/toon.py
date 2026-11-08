# SPDX-License-Identifier: GPL-3.0-or-later
"""Painterly toon material: cel split + terminator brush dabs + shadow colouring."""
import bpy
from .util import (TAG, TOON_GROUP, OUTLINE_MAT, AOV_SHADOW, sock, new, iface, mix, mix_io,
                   math, vmath)

TOON_INPUTS = [
    # material-specific inputs only; every look setting is read from the scene
    # (VIEW_LAYER attribute "p25d.<prop>") or the object override
    # (OBJECT attribute "p25d_obj.<prop>") so shared materials stay correct
    ("Base Color", "NodeSocketColor", (0.8, 0.8, 0.8, 1.0), None, None),
    ("Alpha", "NodeSocketFloat", 1.0, 0.0, 1.0),
    ("Emission", "NodeSocketColor", (0.0, 0.0, 0.0, 1.0), None, None),
    ("Normal", "NodeSocketVector", (0.0, 0.0, 1.0), None, None),
    ("Use Normal", "NodeSocketFloat", 0.0, 0.0, 1.0),
]

# group-internal setting name -> (scene prop, object-override prop or None, kind)
SETTINGS = {
    "Light Scale": ("light_scale", None, "Fac"),
    "Ambient": ("ambient_level", None, "Fac"),
    "Threshold": ("threshold", "threshold", "Fac"),
    "Softness": ("softness", None, "Fac"),
    "Albedo Flatten": ("albedo_flatten", "albedo_flatten", "Fac"),
    "Lit Value": ("lit_value", None, "Fac"),
    "Shadow Value": ("shadow_value", "shadow_value", "Fac"),
    "Shadow Saturation": ("shadow_saturation", None, "Fac"),
    "Shadow Hue Shift": ("shadow_hue_shift", None, "Fac"),
    "Shadow Tint": ("shadow_tint", None, "Color"),
    "Shadow Tint Amount": ("shadow_tint_amount", None, "Fac"),
    "Stroke Strength": ("stroke_strength", "stroke_strength", "Fac"),
    "Stroke Scale": ("stroke_scale", "stroke_scale", "Fac"),
    "Stroke Stretch": ("stroke_stretch", None, "Fac"),
    "Stroke Distortion": ("stroke_distortion", None, "Fac"),
    "Stroke Band": ("stroke_band", None, "Fac"),
    "Base Stroke": ("base_stroke", None, "Fac"),
    "Stroke Seed": ("stroke_seed", None, "Fac"),
    "Stroke Phase": ("stroke_phase", None, "Fac"),
    "Light Color Influence": ("light_influence", "light_influence", "Fac"),
    "Rim Strength": ("rim_strength", "rim_strength", "Fac"),
    "Rim Color": ("rim_color", None, "Color"),
    "Paint Grain": ("paint_grain", None, "Fac"),
    "Dab Variation": ("dab_variation", None, "Fac"),
    "Glow Strength": ("glow_strength", "glow_strength", "Fac"),
    "Glow Threshold": ("glow_threshold", None, "Fac"),
    "Glow Color": (None, "glow_color", "Color"),
}


class _Settings:
    """Lazily creates attribute readers inside the group."""

    def __init__(self, N, L, x=-3000):
        self.N, self.L, self.cache, self.y = N, L, {}, 1500
        self.x = x
        self.ov = None
        self.alive = None

    def _attr(self, kind, path):
        n = new(self.N, "ShaderNodeAttribute", (self.x, self.y))
        self.y -= 160
        n.attribute_type = kind
        n.attribute_name = path
        return n

    def override_fac(self):
        if self.ov is None:
            self.ov = self._attr("OBJECT", "p25d_obj.use_override").outputs["Fac"]
        return self.ov

    def alive_fac(self):
        if self.alive is None:
            self.alive = self._attr("VIEW_LAYER", "p25d.alive").outputs["Fac"]
        return self.alive

    def _fallback(self, scene_prop, dtype):
        """Baked copy of the scene value, used when the add-on is not loaded
        (render farm / collaborator) - otherwise every lookup would return 0."""
        if dtype == "RGBA":
            n = new(self.N, "ShaderNodeRGB", (self.x - 220, self.y + 160), "P25D Fallback " + scene_prop)
        else:
            n = new(self.N, "ShaderNodeValue", (self.x - 220, self.y + 160), "P25D Fallback " + scene_prop)
        n["p25d_prop"] = scene_prop
        return n.outputs[0]

    def __call__(self, name):
        if name in self.cache:
            return self.cache[name]
        scene_prop, obj_prop, out = SETTINGS[name]
        dtype = "RGBA" if out == "Color" else "FLOAT"
        if scene_prop:
            live = self._attr("VIEW_LAYER", "p25d." + scene_prop).outputs[out]
            fb = self._fallback(scene_prop, dtype)
            am = mix(self.N, (self.x + 120, self.y + 160), dtype=dtype)
            if dtype == "RGBA":
                am.blend_type = "MIX"
            f, a, b, g = mix_io(am)
            self.L.new(self.alive_fac(), f)
            self.L.new(fb, a)
            self.L.new(live, b)
        else:
            g = None
        if obj_prop:
            o = self._attr("OBJECT", "p25d_obj." + obj_prop).outputs[out]
            m = mix(self.N, (self.x + 200, self.y + 160), dtype=dtype)
            if dtype == "RGBA":
                m.blend_type = "MIX"
            f, a, b, r = mix_io(m)
            self.L.new(self.override_fac(), f)
            if g is not None:
                self.L.new(g, a)
            else:
                a.default_value = (1, 1, 1, 1)
            self.L.new(o, b)
            g = r
        self.cache[name] = g
        return g


def _light_term(N, L, normal_out, light_scale, x, y, tag, ambient=None):
    """Diffuse -> Shader to RGB -> ((irradiance - ambient) / light scale, colour).
    Subtracting the sky/world fill keeps the cel split working under bright worlds."""
    diff = new(N, "ShaderNodeBsdfDiffuse", (x, y), f"{tag} Diffuse")
    diff.inputs["Color"].default_value = (1, 1, 1, 1)
    L.new(normal_out, diff.inputs["Normal"])
    s2r = new(N, "ShaderNodeShaderToRGB", (x + 180, y), f"{tag} ShaderToRGB")
    L.new(diff.outputs[0], s2r.inputs[0])
    # brightest channel, so coloured (e.g. blue moon) light still crosses the threshold
    sp = new(N, "ShaderNodeSeparateColor", (x + 300, y + 60))
    L.new(s2r.outputs["Color"], sp.inputs[0])
    mx1 = math(N, (x + 420, y + 100), "MAXIMUM")
    L.new(sp.outputs[0], mx1.inputs[0]); L.new(sp.outputs[1], mx1.inputs[1])
    mx2 = math(N, (x + 420, y + 20), "MAXIMUM")
    L.new(mx1.outputs[0], mx2.inputs[0]); L.new(sp.outputs[2], mx2.inputs[1])
    div = math(N, (x + 520, y + 60), "DIVIDE")
    L.new(mx2.outputs[0], div.inputs[0]); L.new(light_scale, div.inputs[1])
    # Diffuse returns irradiance / pi -> rescale so 1.0 == light hitting head-on
    pi = math(N, (x + 660, y + 60), "MULTIPLY", b=3.14159265)
    L.new(div.outputs[0], pi.inputs[0])
    if ambient is None:
        return pi.outputs[0], s2r.outputs["Color"]
    amb = math(N, (x + 660, y - 60), "DIVIDE", label=f"{tag} Ambient / Scale")
    L.new(ambient, amb.inputs[0]); L.new(light_scale, amb.inputs[1])
    sub = math(N, (x + 800, y + 60), "SUBTRACT", label=f"{tag} Minus Ambient")
    L.new(pi.outputs[0], sub.inputs[0]); L.new(amb.outputs[0], sub.inputs[1])
    return sub.outputs[0], s2r.outputs["Color"]


def build_toon_group(rebuild=False):
    ng = bpy.data.node_groups.get(TOON_GROUP)
    if ng and not rebuild and ng.get(TAG + "_ver") == 8:
        return ng
    if ng is None:
        ng = bpy.data.node_groups.new(TOON_GROUP, "ShaderNodeTree")
    ng.nodes.clear()
    ng.interface.clear()
    for name, st, d, lo, hi in TOON_INPUTS:
        iface(ng, name, "INPUT", st, d, lo, hi)
    iface(ng, "Shader", "OUTPUT", "NodeSocketShader")
    iface(ng, "Color", "OUTPUT", "NodeSocketColor")
    iface(ng, "Light Mask", "OUTPUT", "NodeSocketFloat")
    ng[TAG + "_ver"] = 8

    N, L = ng.nodes, ng.links
    gi = new(N, "NodeGroupInput", (-2400, 0))
    go = new(N, "NodeGroupOutput", (2000, 0))
    S = _Settings(N, L)
    I = lambda n: gi.outputs[n] if n in gi.outputs else S(n)

    # ---- base normal (geometry or material normal map) -----------------
    geo = new(N, "ShaderNodeNewGeometry", (-2200, 300))
    bn = mix(N, (-2000, 300), dtype="VECTOR", label="Base Normal")
    bn.factor_mode = "UNIFORM"
    L.new(I("Use Normal"), sock(bn.inputs, "Factor", "VALUE"))
    L.new(geo.outputs["Normal"], sock(bn.inputs, "A", "VECTOR"))
    L.new(I("Normal"), sock(bn.inputs, "B", "VECTOR"))
    bnn = vmath(N, (-1850, 300), "NORMALIZE")
    L.new(sock(bn.outputs, "Result", "VECTOR"), bnn.inputs[0])
    base_n = bnn.outputs[0]

    # ---- clean light pass -> terminator band ---------------------------
    raw0, _ = _light_term(N, L, base_n, I("Light Scale"), -1700, 700, "Clean", I("Ambient"))
    dist = math(N, (-1000, 760), "SUBTRACT")
    L.new(raw0, dist.inputs[0]); L.new(I("Threshold"), dist.inputs[1])
    dabs = math(N, (-860, 760), "ABSOLUTE")
    L.new(dist.outputs[0], dabs.inputs[0])
    dnorm = math(N, (-720, 760), "DIVIDE")
    L.new(dabs.outputs[0], dnorm.inputs[0]); L.new(I("Stroke Band"), dnorm.inputs[1])
    band = math(N, (-580, 760), "SUBTRACT", a=1.0, clamp=True, label="Terminator Band")
    L.new(dnorm.outputs[0], band.inputs[1])

    # ---- brush dab vector (stretched voronoi, noise distorted) ---------
    tc = new(N, "ShaderNodeTexCoord", (-2200, -300))
    # per-axis world scale (parents included): |object->world applied to each unit axis|
    oscale = new(N, "ShaderNodeCombineXYZ", (-2400, -450), "World Scale")
    for i, axis in enumerate(((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
        vt = new(N, "ShaderNodeVectorTransform", (-2800, -350 - 120 * i))
        vt.vector_type = "VECTOR"; vt.convert_from = "OBJECT"; vt.convert_to = "WORLD"
        vt.inputs["Vector"].default_value = axis
        ln = vmath(N, (-2600, -350 - 120 * i), "LENGTH")
        L.new(vt.outputs[0], ln.inputs[0]); L.new(ln.outputs["Value"], oscale.inputs[i])
    wcoord = vmath(N, (-2150, -400), "MULTIPLY", "World Scale Coords")
    L.new(tc.outputs["Object"], wcoord.inputs[0]); L.new(oscale.outputs[0], wcoord.inputs[1])
    mp = new(N, "ShaderNodeMapping", (-2000, -300), "Stroke Mapping")
    L.new(wcoord.outputs[0], mp.inputs["Vector"])
    stretch = new(N, "ShaderNodeCombineXYZ", (-2200, -550))
    stretch.inputs[0].default_value = 1.0
    stretch.inputs[1].default_value = 1.0
    L.new(I("Stroke Stretch"), stretch.inputs[2])
    L.new(stretch.outputs[0], mp.inputs["Scale"])
    mp.inputs["Rotation"].default_value = (0.0, 0.52, 0.0)  # ~30 deg diagonal strokes

    nscale = math(N, (-1850, -500), "MULTIPLY", b=0.5)
    L.new(I("Stroke Scale"), nscale.inputs[0])
    noise = new(N, "ShaderNodeTexNoise", (-1700, -450), "Stroke Noise")
    noise.inputs["Detail"].default_value = 2.0
    L.new(mp.outputs[0], noise.inputs["Vector"])
    L.new(nscale.outputs[0], noise.inputs["Scale"])
    dst = mix(N, (-1500, -300), "LINEAR_LIGHT", label="Stroke Distort")
    f, a, b, r = mix_io(dst)
    L.new(I("Stroke Distortion"), f); L.new(mp.outputs[0], a); L.new(noise.outputs["Color"], b)
    vor = new(N, "ShaderNodeTexVoronoi", (-1300, -300), "Stroke Voronoi")
    vor.voronoi_dimensions = "4D"
    vor.feature = "F1"
    vor.distance = "EUCLIDEAN"
    L.new(r, vor.inputs["Vector"])
    L.new(I("Stroke Scale"), vor.inputs["Scale"])
    seedw = math(N, (-1500, -550), "ADD", label="Seed + Boil")
    L.new(I("Stroke Seed"), seedw.inputs[0]); L.new(I("Stroke Phase"), seedw.inputs[1])
    L.new(seedw.outputs[0], vor.inputs["W"])
    signed = vmath(N, (-1100, -300), "MULTIPLY_ADD")
    signed.inputs[1].default_value = (2.0, 2.0, 2.0)
    signed.inputs[2].default_value = (-1.0, -1.0, -1.0)
    L.new(vor.outputs["Color"], signed.inputs[0])
    bmix = new(N, "ShaderNodeMix", (-1250, -650), "Band Or Base"); bmix.data_type = "FLOAT"
    L.new(band.outputs[0], sock(bmix.inputs, "Factor", "VALUE"))
    L.new(I("Base Stroke"), sock(bmix.inputs, "A", "VALUE"))
    sock(bmix.inputs, "B", "VALUE").default_value = 1.0
    eband = sock(bmix.outputs, "Result", "VALUE")
    seff = math(N, (-1100, -500), "MULTIPLY", label="Stroke x Band")
    L.new(I("Stroke Strength"), seff.inputs[0]); L.new(band.outputs[0], seff.inputs[1])
    scl = vmath(N, (-900, -300), "SCALE")
    L.new(signed.outputs[0], scl.inputs[0]); L.new(seff.outputs[0], scl.inputs["Scale"])
    add = vmath(N, (-750, 0), "ADD")
    L.new(base_n, add.inputs[0]); L.new(scl.outputs[0], add.inputs[1])
    nrm = vmath(N, (-600, 0), "NORMALIZE")
    L.new(add.outputs[0], nrm.inputs[0])

    # ---- painted light pass -> hard ramp -------------------------------
    raw1, lcol_raw = _light_term(N, L, nrm.outputs[0], I("Light Scale"), -450, 300, "Paint", I("Ambient"))
    lo = math(N, (300, 200), "SUBTRACT")
    L.new(I("Threshold"), lo.inputs[0]); L.new(I("Softness"), lo.inputs[1])
    hi = math(N, (300, 80), "ADD")
    L.new(I("Threshold"), hi.inputs[0]); L.new(I("Softness"), hi.inputs[1])
    ramp = new(N, "ShaderNodeMapRange", (480, 300), "Light Ramp")
    ramp.clamp = True
    ramp.interpolation_type = "SMOOTHSTEP"
    L.new(raw1, ramp.inputs["Value"])
    L.new(lo.outputs[0], ramp.inputs["From Min"])
    L.new(hi.outputs[0], ramp.inputs["From Max"])
    mask = ramp.outputs["Result"]

    # normalised light colour for coloured lamps
    sep = new(N, "ShaderNodeSeparateColor", (300, 560))
    L.new(lcol_raw, sep.inputs[0])
    m1 = math(N, (460, 600), "MAXIMUM")
    L.new(sep.outputs[0], m1.inputs[0]); L.new(sep.outputs[1], m1.inputs[1])
    m2 = math(N, (600, 600), "MAXIMUM")
    L.new(m1.outputs[0], m2.inputs[0]); L.new(sep.outputs[2], m2.inputs[1])
    m3 = math(N, (740, 600), "MAXIMUM", b=1e-4)
    L.new(m2.outputs[0], m3.inputs[0])
    lcol = vmath(N, (880, 560), "DIVIDE")
    L.new(lcol_raw, lcol.inputs[0]); L.new(m3.outputs[0], lcol.inputs[1])

    # ---- albedo: flatten baked lighting, lit / shadow versions ---------
    flat_c = math(N, (-600, -650), "MULTIPLY", b=-0.6)
    L.new(I("Albedo Flatten"), flat_c.inputs[0])
    bc = new(N, "ShaderNodeBrightContrast", (-450, -700), "Albedo Flatten")
    L.new(I("Base Color"), bc.inputs["Color"])
    L.new(flat_c.outputs[0], bc.inputs["Contrast"])
    albedo = bc.outputs[0]

    hsv_lit = new(N, "ShaderNodeHueSaturation", (-200, -650), "Lit HSV")
    L.new(albedo, hsv_lit.inputs["Color"])
    L.new(I("Lit Value"), hsv_lit.inputs["Value"])
    hue = math(N, (-400, -950), "ADD", b=0.5)
    L.new(I("Shadow Hue Shift"), hue.inputs[0])
    hsv_sh = new(N, "ShaderNodeHueSaturation", (-200, -900), "Shadow HSV")
    L.new(albedo, hsv_sh.inputs["Color"])
    L.new(hue.outputs[0], hsv_sh.inputs["Hue"])
    L.new(I("Shadow Saturation"), hsv_sh.inputs["Saturation"])
    L.new(I("Shadow Value"), hsv_sh.inputs["Value"])
    tint = mix(N, (50, -900), "MULTIPLY", label="Shadow Tint")
    f, a, b, tint_out = mix_io(tint)
    L.new(I("Shadow Tint Amount"), f); L.new(hsv_sh.outputs[0], a)
    # multiply by tint normalised to white so it colours without crushing value
    tsep = new(N, "ShaderNodeSeparateColor", (-300, -1250))
    L.new(I("Shadow Tint"), tsep.inputs[0])
    tm1 = math(N, (-150, -1300), "MAXIMUM"); L.new(tsep.outputs[0], tm1.inputs[0]); L.new(tsep.outputs[1], tm1.inputs[1])
    tm2 = math(N, (0, -1300), "MAXIMUM"); L.new(tm1.outputs[0], tm2.inputs[0]); L.new(tsep.outputs[2], tm2.inputs[1])
    tm3 = math(N, (120, -1300), "MAXIMUM", b=1e-4); L.new(tm2.outputs[0], tm3.inputs[0])
    tdiv = vmath(N, (240, -1250), "DIVIDE")
    L.new(I("Shadow Tint"), tdiv.inputs[0]); L.new(tm3.outputs[0], tdiv.inputs[1])
    L.new(tdiv.outputs[0], b)

    lit_t = mix(N, (50, -650), "MULTIPLY", label="Light Colour")
    f, a, b, lit_out = mix_io(lit_t)
    L.new(I("Light Color Influence"), f); L.new(hsv_lit.outputs[0], a); L.new(lcol.outputs[0], b)

    toon_m = mix(N, (750, -500), "MIX", label="Toon Mix")
    f, a, b, toon = mix_io(toon_m)
    L.new(mask, f); L.new(tint_out, a); L.new(lit_out, b)

    # ---- rim (on lit side, using painted normal) -----------------------
    lw = new(N, "ShaderNodeLayerWeight", (600, -1000))
    lw.inputs["Blend"].default_value = 0.25
    L.new(base_n, lw.inputs["Normal"])
    rs = new(N, "ShaderNodeMapRange", (780, -1000))
    rs.inputs["From Min"].default_value = 0.7
    rs.inputs["From Max"].default_value = 0.75
    L.new(lw.outputs["Facing"], rs.inputs["Value"])
    rm = math(N, (940, -1000), "MULTIPLY"); L.new(rs.outputs[0], rm.inputs[0]); L.new(mask, rm.inputs[1])
    nb = math(N, (940, -1150), "SUBTRACT", a=1.0); L.new(band.outputs[0], nb.inputs[1])
    rmb = math(N, (1010, -1080), "MULTIPLY"); L.new(rm.outputs[0], rmb.inputs[0]); L.new(nb.outputs[0], rmb.inputs[1])
    rf = math(N, (1080, -1000), "MULTIPLY"); L.new(rmb.outputs[0], rf.inputs[0]); L.new(I("Rim Strength"), rf.inputs[1])
    rim = mix(N, (1000, -500), "SCREEN", label="Rim")
    f, a, b, rim_out = mix_io(rim)
    L.new(rf.outputs[0], f); L.new(toon, a); L.new(I("Rim Color"), b)

    # ---- grain + dab colour variation (dabs only near terminator) -----
    gn = new(N, "ShaderNodeTexNoise", (1000, -1300), "Grain Noise")
    gn.inputs["Scale"].default_value = 60.0
    gn.inputs["Detail"].default_value = 4.0
    L.new(wcoord.outputs[0], gn.inputs["Vector"])
    gs = math(N, (1160, -1300), "SUBTRACT", b=0.5); L.new(gn.outputs["Fac"], gs.inputs[0])
    gm = math(N, (1300, -1300), "MULTIPLY"); L.new(gs.outputs[0], gm.inputs[0]); L.new(I("Paint Grain"), gm.inputs[1])
    dsep = new(N, "ShaderNodeSeparateColor", (1000, -1550)); L.new(vor.outputs["Color"], dsep.inputs[0])
    ds = math(N, (1160, -1550), "SUBTRACT", b=0.5); L.new(dsep.outputs[0], ds.inputs[0])
    dm = math(N, (1300, -1550), "MULTIPLY"); L.new(ds.outputs[0], dm.inputs[0]); L.new(I("Dab Variation"), dm.inputs[1])
    db = math(N, (1440, -1550), "MULTIPLY"); L.new(dm.outputs[0], db.inputs[0]); L.new(eband, db.inputs[1])
    gsum = math(N, (1440, -1300), "ADD"); L.new(gm.outputs[0], gsum.inputs[0]); L.new(db.outputs[0], gsum.inputs[1])
    gone = math(N, (1580, -1300), "ADD", a=1.0); L.new(gsum.outputs[0], gone.inputs[1])
    graded = vmath(N, (1250, -500), "SCALE")
    L.new(rim_out, graded.inputs[0]); L.new(gone.outputs[0], graded.inputs["Scale"])

    # ---- glow from bright warm texels (lit windows, lanterns) ---------
    lum = new(N, "ShaderNodeRGBToBW", (600, -1700)); L.new(I("Base Color"), lum.inputs[0])
    ghi = math(N, (760, -1800), "ADD", b=0.12); L.new(I("Glow Threshold"), ghi.inputs[0])
    gl = new(N, "ShaderNodeMapRange", (920, -1700)); gl.interpolation_type = "SMOOTHSTEP"
    L.new(lum.outputs[0], gl.inputs["Value"]); L.new(I("Glow Threshold"), gl.inputs["From Min"])
    L.new(ghi.outputs[0], gl.inputs["From Max"])
    csep = new(N, "ShaderNodeSeparateColor", (600, -1950)); L.new(I("Base Color"), csep.inputs[0])
    warm = math(N, (760, -1950), "SUBTRACT"); L.new(csep.outputs[0], warm.inputs[0]); L.new(csep.outputs[2], warm.inputs[1])
    wr = new(N, "ShaderNodeMapRange", (920, -1950)); wr.interpolation_type = "SMOOTHSTEP"
    wr.inputs["From Min"].default_value = 0.08; wr.inputs["From Max"].default_value = 0.25
    L.new(warm.outputs[0], wr.inputs["Value"])
    shsv = new(N, "ShaderNodeSeparateColor", (600, -2200)); shsv.mode = "HSV"
    L.new(I("Base Color"), shsv.inputs[0])
    sr = new(N, "ShaderNodeMapRange", (760, -2200)); sr.interpolation_type = "SMOOTHSTEP"
    sr.inputs["From Min"].default_value = 0.3; sr.inputs["From Max"].default_value = 0.45
    L.new(shsv.outputs[1], sr.inputs["Value"])
    g0 = math(N, (920, -2050), "MULTIPLY"); L.new(wr.outputs[0], g0.inputs[0]); L.new(sr.outputs[0], g0.inputs[1])
    g1 = math(N, (1100, -1800), "MULTIPLY"); L.new(gl.outputs[0], g1.inputs[0]); L.new(g0.outputs[0], g1.inputs[1])
    g2 = math(N, (1240, -1800), "MULTIPLY"); L.new(g1.outputs[0], g2.inputs[0]); L.new(I("Glow Strength"), g2.inputs[1])
    gtint = vmath(N, (1300, -1950), "MULTIPLY"); L.new(I("Base Color"), gtint.inputs[0]); L.new(I("Glow Color"), gtint.inputs[1])
    gcol = vmath(N, (1400, -1700), "SCALE"); L.new(gtint.outputs[0], gcol.inputs[0]); L.new(g2.outputs[0], gcol.inputs["Scale"])
    add_g = vmath(N, (1500, -500), "ADD"); L.new(graded.outputs[0], add_g.inputs[0]); L.new(gcol.outputs[0], add_g.inputs[1])
    add_e = vmath(N, (1650, -500), "ADD"); L.new(add_g.outputs[0], add_e.inputs[0]); L.new(I("Emission"), add_e.inputs[1])
    final = add_e.outputs[0]

    emit = new(N, "ShaderNodeEmission", (1750, 0))
    emit.inputs["Strength"].default_value = 1.0
    L.new(final, emit.inputs["Color"])
    tr = new(N, "ShaderNodeBsdfTransparent", (1750, 150))
    ms = new(N, "ShaderNodeMixShader", (1880, 50))
    L.new(I("Alpha"), ms.inputs[0]); L.new(tr.outputs[0], ms.inputs[1]); L.new(emit.outputs[0], ms.inputs[2])
    L.new(ms.outputs[0], go.inputs["Shader"])
    L.new(final, go.inputs["Color"])
    L.new(mask, go.inputs["Light Mask"])
    return ng


# --------------------------------------------------------------------------
def _output_node(nt):
    """The output EEVEE actually uses: an EEVEE-target output wins over the active 'All' output."""
    outs = [n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"]
    return (next((n for n in outs if n.target == "EEVEE"), None)
            or next((n for n in outs if n.is_active_output and n.target == "ALL"), None)
            or next((n for n in outs if n.is_active_output), None)
            or (outs[0] if outs else None))


def _toon_node(nt):
    return next((n for n in nt.nodes if n.type == "GROUP" and n.node_tree and n.node_tree.name == TOON_GROUP), None)


_COLOR_INPUTS = ("Base Color", "Color", "Base Colour")
_CLEAR = ("BSDF_TRANSPARENT", "HOLDOUT")


def _upstream(out):
    """Nodes feeding the output's Surface socket (through groups' sockets, reroutes, mixes)."""
    seen, stack = set(), []
    if out and out.inputs["Surface"].is_linked:
        stack.append(out.inputs["Surface"].links[0].from_node)
    while stack:
        n = stack.pop()
        if n.name in seen:
            continue
        seen.add(n.name)
        yield n
        for i in n.inputs:
            for l in i.links:
                stack.append(l.from_node)


def _mix_alpha(out):
    """Classic cut-out: Mix Shader(Fac, Transparent, X) on the surface -> (socket, invert)."""
    surf = out.inputs["Surface"] if out else None
    n = surf.links[0].from_node if (surf and surf.is_linked) else None
    if n is None or n.type != "MIX_SHADER" or not n.inputs[0].is_linked:
        return None
    a, b = n.inputs[1], n.inputs[2]
    if a.is_linked and a.links[0].from_node.type in _CLEAR:
        return n.inputs[0].links[0].from_socket, False     # Fac=1 -> second (opaque) shader
    if b.is_linked and b.links[0].from_node.type in _CLEAR:
        return n.inputs[0].links[0].from_socket, True
    return None


def _base_color_source(nt, out):
    """Base colour for materials without a Principled BSDF: the colour input of the node
    driving the surface (Diffuse / Toon / Emission / custom groups), else the first image."""
    surf = out.inputs["Surface"] if out else None
    node = surf.links[0].from_node if (surf and surf.is_linked) else None
    seen = set()
    while node is not None and node.name not in seen:
        seen.add(node.name)
        if node.type == "TEX_IMAGE":
            return node.outputs["Color"]
        for name in _COLOR_INPUTS:
            i = node.inputs.get(name)
            if i is not None and i.type == "RGBA":
                return i.links[0].from_socket if i.is_linked else tuple(i.default_value)
        # mix / add shader: follow the first linked shader input that isn't a cut-out
        shaders = [i for i in node.inputs if i.is_linked and i.type == "SHADER"]
        nxt = next((i for i in shaders if i.links[0].from_node.type not in _CLEAR), None) or \
            (shaders[0] if shaders else None)
        node = nxt.links[0].from_node if nxt else None
    img = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and n.image), None)
    return img.outputs["Color"] if img else None


def is_glass(mat):
    """Principled with (mostly) transmission, or a Glass/Refraction BSDF on the surface."""
    nt = mat.node_tree
    if nt is None:
        return False
    for n in _upstream(_output_node(nt)):      # ignore spare nodes that don't reach the output
        if n.type in ("BSDF_GLASS", "BSDF_REFRACTION"):
            return True
        if n.type == "BSDF_PRINCIPLED":
            met = n.inputs.get("Metallic")
            metallic = met is not None and (met.is_linked or met.default_value > 0.5)   # metals ignore transmission
            tw = n.inputs.get("Transmission Weight") or n.inputs.get("Transmission")
            if not metallic and tw is not None and not tw.is_linked and tw.default_value > 0.5:
                return True
            # alpha-blended see-through surfaces (window glass, bottles); alpha-clipped leaves stay toon
            al = n.inputs.get("Alpha")
            if getattr(mat, "surface_render_method", "") == "BLENDED" and al is not None and \
                    (al.is_linked or al.default_value < 0.95):
                return True
    return False


def toonify_material(mat):
    if mat is None or mat.name == OUTLINE_MAT or getattr(mat, "library", None):
        return False
    if mat.node_tree is None:
        try:
            mat.use_nodes = True
        except Exception:
            return False
        if mat.node_tree is None:
            return False
    nt = mat.node_tree
    if is_glass(mat):
        mat[TAG + "_glass"] = True          # glass/water: keep the original shader (cel shading would make it opaque)
        return False
    ng = build_toon_group()
    out = _output_node(nt) or nt.nodes.new("ShaderNodeOutputMaterial")
    grp = _toon_node(nt)
    if grp is None:
        grp = nt.nodes.new("ShaderNodeGroup")
        grp.node_tree = ng
        grp.name = grp.label = TOON_GROUP
        grp.location = (out.location.x - 280, out.location.y - 300)
        grp.width = 240
    bsdf = next((n for n in _upstream(out) if n.type == "BSDF_PRINCIPLED"), None) or \
        next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bcs = bsdf.inputs["Base Color"]
        if bcs.is_linked:
            nt.links.new(bcs.links[0].from_socket, grp.inputs["Base Color"])
        else:
            grp.inputs["Base Color"].default_value = bcs.default_value
        al = bsdf.inputs["Alpha"]
        if al.is_linked:
            nt.links.new(al.links[0].from_socket, grp.inputs["Alpha"])
        else:
            grp.inputs["Alpha"].default_value = al.default_value
        nm = bsdf.inputs["Normal"]
        if nm.is_linked:
            nt.links.new(nm.links[0].from_socket, grp.inputs["Normal"])
            grp.inputs["Use Normal"].default_value = 1.0
        ec, es = bsdf.inputs.get("Emission Color"), bsdf.inputs.get("Emission Strength")
        if ec is not None and es is not None and (ec.is_linked or es.default_value > 0):
            sc = nt.nodes.get("P25D Emission") or nt.nodes.new("ShaderNodeVectorMath")
            sc.operation = "SCALE"
            sc.location = (grp.location.x - 200, grp.location.y - 400)
            sc.name = sc.label = "P25D Emission"
            if ec.is_linked:
                nt.links.new(ec.links[0].from_socket, sc.inputs[0])
            else:
                sc.inputs[0].default_value = ec.default_value[:3]
            if es.is_linked:
                nt.links.new(es.links[0].from_socket, sc.inputs["Scale"])
            else:
                sc.inputs["Scale"].default_value = es.default_value
            nt.links.new(sc.outputs[0], grp.inputs["Emission"])
    else:
        src = _base_color_source(nt, out)
        if src is None:
            grp.inputs["Base Color"].default_value = tuple(mat.diffuse_color)
        elif isinstance(src, tuple):
            grp.inputs["Base Color"].default_value = src
        else:
            nt.links.new(src, grp.inputs["Base Color"])
    ma = _mix_alpha(out) if not grp.inputs["Alpha"].is_linked else None
    if ma:
        sock_, invert = ma
        inv = nt.nodes.get("P25D Alpha") or nt.nodes.new("ShaderNodeMath")
        inv.name = inv.label = "P25D Alpha"
        inv.operation = "SUBTRACT" if invert else "ADD"
        inv.inputs[0].default_value = 1.0 if invert else 0.0
        inv.location = (grp.location.x - 200, grp.location.y - 250)
        nt.links.new(sock_, inv.inputs[1])
        nt.links.new(inv.outputs[0], grp.inputs["Alpha"])
    surf = out.inputs["Surface"]
    if surf.is_linked and surf.links[0].from_node != grp:
        mat[TAG + "_orig_node"] = surf.links[0].from_node.name
        mat[TAG + "_orig_sock"] = surf.links[0].from_socket.identifier
    mat[TAG + "_out_node"] = out.name
    nt.links.new(grp.outputs["Shader"], surf)
    # light-mask AOV for the compositor (texture dots in shadows)
    aov = nt.nodes.get("P25D AOV") or nt.nodes.new("ShaderNodeOutputAOV")
    aov.name = aov.label = "P25D AOV"
    aov.aov_name = AOV_SHADOW
    aov.location = (out.location.x, out.location.y - 200)
    enc = nt.nodes.get("P25D AOV Map") or nt.nodes.new("ShaderNodeMath")
    enc.name = enc.label = "P25D AOV Map"
    enc.operation = "SUBTRACT"              # shadow amount; background stays 0
    enc.inputs[0].default_value = 1.0
    enc.location = (out.location.x - 150, out.location.y - 220)
    nt.links.new(grp.outputs["Light Mask"], enc.inputs[1])
    nt.links.new(enc.outputs[0], aov.inputs["Value"])
    mat[TAG] = True
    return True


def revert_material(mat):
    if not mat or not mat.get(TAG):
        return False
    nt = mat.node_tree
    out = nt.nodes.get(mat.get(TAG + "_out_node", "")) or _output_node(nt)
    on = nt.nodes.get(mat.get(TAG + "_orig_node", ""))
    if out and on:
        s = next((s for s in on.outputs if s.identifier == mat.get(TAG + "_orig_sock")), on.outputs[0])
        nt.links.new(s, out.inputs["Surface"])
    for n in list(nt.nodes):
        base = n.name.rsplit(".", 1)[0] if n.name[-4:-3] == "." and n.name[-3:].isdigit() else n.name
        if (n.type == "GROUP" and n.node_tree and n.node_tree.name == TOON_GROUP) or \
                base in ("P25D AOV", "P25D Emission", "P25D AOV Map", "P25D Alpha"):
            nt.nodes.remove(n)
    for k in (TAG, TAG + "_orig_node", TAG + "_orig_sock", TAG + "_out_node"):
        if k in mat:
            del mat[k]
    return True


# --------------------------------------------------------------------------
def apply_toon_settings(scene):
    """Settings are read inside the shader. Only the baked fallbacks (used when the
    add-on is missing) are refreshed here: one shared group -> one write per setting."""
    ng = bpy.data.node_groups.get(TOON_GROUP)
    s = getattr(scene, "p25d", None)
    if ng and s:
        for n in ng.nodes:
            prop = n.get("p25d_prop")
            if prop and hasattr(s, prop):
                v = getattr(s, prop)
                if n.type == "RGB":
                    n.outputs[0].default_value = tuple(v)[:3] + (1.0,)
                else:
                    n.outputs[0].default_value = float(v)
    for m in toon_materials():
        m.node_tree.update_tag()
    scene.update_tag()


def toon_materials():
    return [m for m in bpy.data.materials if m.get(TAG) and m.node_tree]
