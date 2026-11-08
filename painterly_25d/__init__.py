# SPDX-License-Identifier: GPL-3.0-or-later
"""Painterly 2.5D — hand-painted / 2.5D NPR look for Blender 5.x (EEVEE).

  1. Toon material : normalised cel split, brush dabs only around the terminator,
                     coloured shadows from the albedo (HSV), texture glow, rim.
  2. Outline       : Geometry-Nodes inverted hull, constant screen width, distance
                     fade, broken hand-drawn width and "boil" on twos.
  3. Post FX       : depth fog, two-pass Kuwahara with ink protection, texture
                     dots in shadows, bloom + halation, paper, sensor dust, grain,
                     chromatic aberration, vignette and a vintage grade.
  4. Sketch lines  : optional Grease Pencil Line Art.
"""

bl_info = {
    "name": "Painterly 2.5D",
    "author": "Tokyo AI Visuals",
    "version": (1, 0, 0),
    "blender": (5, 0, 0),
    "location": "3D Viewport > Sidebar (N) > Painterly",
    "description": "Hand-painted 2.5D toon shading, hand-drawn outlines and painterly compositing",
    "category": "Render",
}

import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty,
                       IntProperty, PointerProperty)

from . import toon, outline, post, autosetup, translations
from .util import TAG, TOON_GROUP, OUTLINE_MAT, OUTLINE_MOD, srgb

# re-exports used by scripts
TOON_GROUP = TOON_GROUP
toon_materials = toon.toon_materials


# --------------------------------------------------------------------------
# update callbacks (use the scene that owns the settings, not context.scene)
# --------------------------------------------------------------------------
def _scene(self):
    return self.id_data if isinstance(self.id_data, bpy.types.Scene) else bpy.context.scene


def _upd_toon(self, context):
    if not self.get("_lock"):
        toon.apply_toon_settings(_scene(self))


def _upd_outline(self, context):
    if not self.get("_lock"):
        outline.apply_outline_settings(_scene(self))


def _upd_post(self, context):
    if not self.get("_lock"):
        post.apply_post_settings(_scene(self))


def _upd_boil_rate(self, context):
    _upd_outline(self, context)
    link_boil(_scene(self))


def _upd_obj(self, context):
    sc = context.scene
    toon.apply_toon_settings(sc)
    outline.apply_outline_settings(sc)


def _col(name, hexv, upd):
    return FloatVectorProperty(name=name, subtype="COLOR", size=3, min=0, max=1,
                               default=srgb(hexv), update=upd)


# --------------------------------------------------------------------------
# presets: each preset only lists the keys it changes; everything else keeps
# its current value (so toggles and per-shot tweaks survive)
# --------------------------------------------------------------------------
PRESETS = {
    "DEFAULT": {},
    "NIGHT": dict(shadow_tint=srgb("#5E4A8E"), shadow_tint_amount=0.35, shadow_value=0.62,
                  rim_color=srgb("#9FB4FF"), rim_strength=0.12, light_influence=0.2,
                  outline_color=srgb("#2A1610"), bloom_threshold=0.7, bloom_strength=0.8,
                  fog_color=srgb("#3A3A6E"), fog_amount=0.3, warmth=0.1, saturation=0.95,
                  vignette=0.3, vignette_color=srgb("#2A1810"), contrast=0.06,
                  black_lift=srgb("#1E1826")),
    "GOLDEN": dict(shadow_tint=srgb("#7A5A8C"), shadow_tint_amount=0.22, shadow_value=0.7,
                   rim_color=srgb("#FFB066"), rim_strength=0.3, light_influence=0.35,
                   outline_color=srgb("#3B1F14"), bloom_threshold=0.85, bloom_strength=0.4,
                   fog_color=srgb("#F2B88A"), fog_amount=0.15, warmth=0.3,
                   saturation=1.0, contrast=0.05, paper_tint=0.2),
    "PASTEL": dict(shadow_tint=srgb("#C89BD0"), shadow_tint_amount=0.35, shadow_value=0.8,
                   shadow_saturation=1.15, warmth=0.15, outline_color=srgb("#5A3240"),
                   kuwahara_size=5, paper_strength=0.25, fog_color=srgb("#F0D8E8")),
    "DAY": dict(shadow_tint=srgb("#6B5BA8"), shadow_tint_amount=0.25, shadow_value=0.72,
                rim_color=srgb("#FFE2B8"), rim_strength=0.15, light_influence=0.3,
                outline_color=srgb("#3B1F14"), bloom_threshold=0.95, bloom_strength=0.3,
                fog_color=srgb("#BFD3F0"), fog_amount=0.15, warmth=0.08, saturation=1.05,
                vignette=0.25, vignette_color=srgb("#2A1810"), contrast=0.08, black_lift=srgb("#141018")),
    "CLEAN": dict(kuwahara_mix=0.45, kuwahara_size=4, dots_strength=0.05, paper_strength=0.05,
                  paper_tint=0.1, dust=0.0, grain_strength=0.012, aberration=0.0, halation=0.02,
                  vignette=0.15, warmth=0.04, contrast=0.06),
}


def apply_preset(self, context):
    sc = _scene(self)
    s = sc.p25d
    s["_lock"] = True
    try:
        for k, v in PRESETS.get(s.preset, {}).items():
            setattr(s, k, v)
    finally:
        s["_lock"] = False
    _apply_all(sc)


def _apply_all(sc):
    toon.apply_toon_settings(sc)
    outline.apply_outline_settings(sc)
    post.apply_post_settings(sc)


class P25D_Settings(bpy.types.PropertyGroup):
    alive: BoolProperty(name="Add-on Loaded", default=True,
                        description="Read by the shader; missing when the add-on is not installed "
                                    "so materials fall back to baked values")
    preset: EnumProperty(name="Preset", items=[
        ("DEFAULT", "Default", "Keep current values"),
        ("NIGHT", "Blue-hour Night", "Cool lavender shadows, warm glowing windows, strong bloom"),
        ("GOLDEN", "Golden Hour", "Warm low sun, mauve shadows"),
        ("PASTEL", "Pastel Sweets", "Soft pastel shadows"),
        ("DAY", "Storybook Day", "Bright daylight, soft violet shadows, light paper"),
        ("CLEAN", "Clean / Product", "Subtle paint and film effects for product and character turntables")],
        update=apply_preset)
    only_selected: BoolProperty(name="Selected Objects Only", default=False,
                                description="Make It Painterly only converts the selected objects")
    auto_key_light: BoolProperty(name="Add Key Light if Missing", default=True,
                                 description="Make It Painterly adds a Sun aimed from the camera side when "
                                             "the scene has no Sun (removed again by Revert)")
    auto_fit: BoolProperty(name="Fit to Scene Scale", default=True,
                           description="Make It Painterly sets brush-dab size, depth fog and outline fade from "
                                       "the size of your objects and the camera distance")
    # light / cel
    key_light: PointerProperty(name="Key Light", type=bpy.types.Object,
                               poll=lambda self, o: o.type == "LIGHT",
                               description="Light the cel threshold is measured against (drives Light Scale)",
                               update=lambda self, ctx: link_key_light(self.id_data))
    light_scale: FloatProperty(name="Light Scale", default=1.0, min=0.001, soft_max=50,
                               description="Key light strength x brightest colour channel. Driven by "
                                           "Key Light when one is set", update=_upd_toon)
    ambient_level: FloatProperty(name="Ambient Compensation", default=0.0, min=0, soft_max=10,
                                 description="Sky/world fill removed before the light/shadow split, so bright "
                                             "worlds keep their shadows. Estimated by Setup Render", update=_upd_toon)
    threshold: FloatProperty(name="Threshold", default=0.5, min=0, max=2, update=_upd_toon)
    softness: FloatProperty(name="Softness", default=0.05, min=0.001, max=0.5, update=_upd_toon)
    albedo_flatten: FloatProperty(name="Albedo Flatten", default=0.15, min=0, max=1,
                                  description="Reduce lighting baked into AI/photo textures", update=_upd_toon)
    lit_value: FloatProperty(name="Lit Value", default=1.0, min=0, max=2, update=_upd_toon)
    shadow_value: FloatProperty(name="Shadow Value", default=0.7, min=0, max=1, update=_upd_toon)
    shadow_saturation: FloatProperty(name="Shadow Saturation", default=0.95, min=0, max=2, update=_upd_toon)
    shadow_hue_shift: FloatProperty(name="Shadow Hue Shift", default=0.0, min=-0.2, max=0.2, update=_upd_toon)
    shadow_tint: _col("Shadow Tint", "#5E4A8E", _upd_toon)
    shadow_tint_amount: FloatProperty(name="Tint Amount", default=0.3, min=0, max=1, update=_upd_toon)
    light_influence: FloatProperty(name="Light Colour", default=0.35, min=0, max=1, update=_upd_toon)
    # strokes
    stroke_strength: FloatProperty(name="Stroke Strength", default=0.7, min=0, max=3, update=_upd_toon)
    stroke_scale: FloatProperty(name="Stroke Scale", default=12.0, min=0.01, max=10000, soft_max=200,
                                description="Dabs per metre (set automatically by Fit to Scene)", update=_upd_toon)
    stroke_stretch: FloatProperty(name="Stroke Stretch", default=0.35, min=0.05, max=1, update=_upd_toon)
    stroke_distortion: FloatProperty(name="Stroke Distortion", default=0.3, min=0, max=1, update=_upd_toon)
    stroke_band: FloatProperty(name="Terminator Band", default=0.25, min=0.01, max=2,
                               description="Brush dabs only appear this close to the light/shadow line",
                               update=_upd_toon)
    base_stroke: FloatProperty(name="Lit Brush Texture", default=0.2, min=0, max=1,
                               description="Brush texture outside the terminator band", update=_upd_toon)
    stroke_seed: FloatProperty(name="Stroke Seed", default=0.0, update=_upd_toon)
    stroke_boil: BoolProperty(name="Dab Boil", default=True,
                              description="Slowly morph dabs on the boil rate (driver, no handler)",
                              update=lambda self, ctx: link_boil(self.id_data))
    stroke_phase: FloatProperty(name="Stroke Phase", default=0.0,
                                description="Driven: floor(frame / boil rate) * 0.03 when Dab Boil is on")
    paint_grain: FloatProperty(name="Paint Grain", default=0.04, min=0, max=0.5, update=_upd_toon)
    dab_variation: FloatProperty(name="Dab Variation", default=0.08, min=0, max=0.5, update=_upd_toon)
    rim_strength: FloatProperty(name="Rim", default=0.2, min=0, max=1, update=_upd_toon)
    rim_color: _col("Rim Colour", "#FFC98A", _upd_toon)
    glow_strength: FloatProperty(name="Texture Glow", default=0.0, min=0, max=20,
                                 description="Make bright warm texels (windows, lanterns) emit", update=_upd_toon)
    glow_threshold: FloatProperty(name="Glow Threshold", default=0.7, min=0, max=1, update=_upd_toon)
    # outline
    outline_enable: BoolProperty(name="Outlines", default=True, update=_upd_outline)
    outline_thickness: FloatProperty(name="Thickness", default=0.006, min=0, max=100, soft_max=0.2, precision=4,
                                     update=_upd_outline)
    outline_screen_space: BoolProperty(name="Constant Screen Width", default=True, update=_upd_outline)
    outline_ref_distance: FloatProperty(name="Reference Distance", default=6.0, min=0.01, update=_upd_outline)
    outline_fade_distance: FloatProperty(name="Fade Distance", default=30.0, min=0.01, update=_upd_outline)
    outline_fade_min: FloatProperty(name="Far Width", default=0.35, min=0, max=1, update=_upd_outline)
    outline_jitter: FloatProperty(name="Hand Jitter", default=0.7, min=0, max=1, update=_upd_outline)
    outline_jitter_scale: FloatProperty(name="Jitter Scale", default=3.0, min=0, max=100, update=_upd_outline)
    outline_boil: BoolProperty(name="Line Boil", default=True, update=_upd_outline,
                               description="Re-draw line wobble on the boil rate. Makes the outline re-evaluate "
                                           "every frame (with Weld on this includes Merge by Distance)")
    boil_rate: IntProperty(name="Boil Rate (frames)", default=2, min=1, max=12, update=_upd_boil_rate)
    outline_color: _col("Ink Colour", "#3B1F14", _upd_outline)
    outline_weld: BoolProperty(name="Weld UV Seams", default=True,
                               description="Merge split vertices before building the hull (prevents cracks; "
                                           "slower on dense meshes)", update=_upd_outline)
    # post
    post_kuwahara: BoolProperty(name="Kuwahara", default=True, update=_upd_post)
    kuwahara_clean: IntProperty(name="Clean Size", default=4, min=1, max=20, update=_upd_post)
    kuwahara_size: IntProperty(name="Paint Size", default=6, min=1, max=40, update=_upd_post)
    kuwahara_sharpness: FloatProperty(name="Sharpness", default=0.5, min=0, max=1, update=_upd_post)
    kuwahara_eccentricity: FloatProperty(name="Eccentricity", default=1.2, min=0, max=2, update=_upd_post)
    kuwahara_mix: FloatProperty(name="Paint Amount", default=0.75, min=0, max=1, update=_upd_post)
    ink_protect: FloatProperty(name="Ink Protect", default=0.8, min=0, max=1, update=_upd_post)
    dots_strength: FloatProperty(name="Texture Dots", default=0.12, min=0, max=1, update=_upd_post)
    dots_size: FloatProperty(name="Dot Spacing (px @1920)", default=5.0, min=2, max=40, update=_upd_post)
    dots_color: _col("Dot Colour", "#9F8FB3", _upd_post)
    fog_start: FloatProperty(name="Fog Start", default=16.0, min=0, update=_upd_post)
    fog_end: FloatProperty(name="Fog End", default=40.0, min=0, update=_upd_post)
    fog_amount: FloatProperty(name="Fog", default=0.3, min=0, max=1, update=_upd_post)
    fog_color: _col("Fog Colour", "#6E6A9E", _upd_post)
    bloom_threshold: FloatProperty(name="Bloom Threshold", default=0.8, min=0, max=10, update=_upd_post)
    bloom_strength: FloatProperty(name="Bloom Strength", default=0.5, min=0, max=5, update=_upd_post)
    bloom_size: FloatProperty(name="Bloom Size", default=0.8, min=0, max=1, update=_upd_post)
    halation: FloatProperty(name="Halation", default=0.06, min=0, max=1, update=_upd_post)
    paper_strength: FloatProperty(name="Paper", default=0.15, min=0, max=1, update=_upd_post)
    paper_tint: FloatProperty(name="Paper Tint", default=0.35, min=0, max=1, update=_upd_post)
    paper_color: _col("Paper Colour", "#F2E3C6", _upd_post)
    dust: FloatProperty(name="Sensor Dust", default=0.08, min=0, max=1, update=_upd_post)
    grain_strength: FloatProperty(name="Grain", default=0.035, min=0, max=1, update=_upd_post)
    aberration: FloatProperty(name="Aberration", default=0.006, min=0, max=0.1, precision=4, update=_upd_post)
    vignette: FloatProperty(name="Vignette", default=0.35, min=0, max=1, update=_upd_post)
    vignette_color: _col("Vignette Colour", "#2A1810", _upd_post)
    black_lift: _col("Black Lift", "#0E0A10", _upd_post)
    contrast: FloatProperty(name="Contrast", default=0.1, min=-1, max=1, update=_upd_post)
    warmth: FloatProperty(name="Warmth", default=0.12, min=-1, max=1, update=_upd_post)
    saturation: FloatProperty(name="Saturation", default=0.95, min=0, max=2, update=_upd_post)
    # sketch
    sketch_radius: FloatProperty(name="Line Radius", default=0.004, min=0.0001, max=0.1, precision=4)
    sketch_jitter: FloatProperty(name="Line Jitter", default=0.4, min=0, max=2)


def _upd_use_override(self, context):
    """Turning an override on starts from the scene's current values, not object defaults."""
    if self.use_override and not self.get("_seeded"):
        s = context.scene.p25d
        for k in ("threshold", "shadow_value", "stroke_strength", "stroke_scale", "albedo_flatten",
                  "rim_strength", "light_influence", "glow_strength"):
            if hasattr(s, k):
                setattr(self, k, getattr(s, k))
        self["_seeded"] = True
    _upd_obj(self, context)


class P25D_ObjSettings(bpy.types.PropertyGroup):
    use_override: BoolProperty(name="Override", default=False, update=_upd_use_override)
    threshold: FloatProperty(name="Threshold", default=0.5, min=0, max=2, update=_upd_obj)
    shadow_value: FloatProperty(name="Shadow Value", default=0.7, min=0, max=1, update=_upd_obj)
    stroke_strength: FloatProperty(name="Stroke Strength", default=0.7, min=0, max=3, update=_upd_obj)
    stroke_scale: FloatProperty(name="Stroke Scale", default=6.0, min=0.01, max=10000, soft_max=200, update=_upd_obj)
    albedo_flatten: FloatProperty(name="Albedo Flatten", default=0.15, min=0, max=1, update=_upd_obj)
    glow_strength: FloatProperty(name="Texture Glow", default=0.0, min=0, max=20, update=_upd_obj)
    glow_color: FloatVectorProperty(name="Glow Colour", subtype="COLOR", size=3, min=0, max=1,
                                    default=(1.0, 1.0, 1.0), update=_upd_obj)
    rim_strength: FloatProperty(name="Rim", default=0.2, min=0, max=1, update=_upd_obj)
    light_influence: FloatProperty(name="Light Colour", default=0.35, min=0, max=1, update=_upd_obj)
    outline_enable: BoolProperty(name="Outline", default=True, update=_upd_obj)
    outline_scale: FloatProperty(name="Outline Width x", default=1.0, min=0, max=10, update=_upd_obj)


# --------------------------------------------------------------------------
# drivers (no frame/render handlers: safe during renders, undo-friendly)
# --------------------------------------------------------------------------
def _driver_var(drv, name, id_type, idb, path):
    v = drv.variables.new()
    v.name = name
    v.type = "SINGLE_PROP"
    v.targets[0].id_type = id_type
    v.targets[0].id = idb
    v.targets[0].data_path = path


def link_key_light(scene):
    """Drive Light Scale from the key light (strength x brightest colour channel)."""
    s = scene.p25d
    try:
        scene.driver_remove("p25d.light_scale")
    except TypeError:
        pass
    key = s.key_light
    if key is None or key.type != "LIGHT":
        return
    fc = scene.driver_add("p25d.light_scale")
    drv = fc.driver
    drv.type = "SCRIPTED"
    _driver_var(drv, "e", "LIGHT", key.data, "energy")
    for i, c in enumerate("rgb"):
        _driver_var(drv, c, "LIGHT", key.data, f"color[{i}]")
    k = 1.0
    if key.data.type != "SUN":           # Watts -> irradiance at the subject (distance baked; Fit/Setup refresh it)
        c = autosetup.subject_centre(scene)
        k = autosetup.light_irradiance(key, c) / max(1e-9, key.data.energy * max(key.data.color))
    drv.expression = "e * max(max(r, g), b)" + (f" * {k:.6g}" if k != 1.0 else "")


def revalidate_drivers(*_):
    """Drivers on p25d.* are flagged invalid if a file loads before the add-on registers."""
    for sc in bpy.data.scenes:
        ad = sc.animation_data
        if ad:
            for fc in ad.drivers:
                if fc.data_path.startswith("p25d."):
                    fc.driver.is_valid = True
                    fc.is_valid = True


def link_boil(scene):
    """Phase = floor(frame / rate) * 0.03. Rate is baked into the expression
    (reading the scene's own props from a scene driver creates a depsgraph cycle)."""
    s = scene.p25d
    try:
        scene.driver_remove("p25d.stroke_phase")
    except TypeError:
        pass
    if not s.stroke_boil:
        s.stroke_phase = 0.0
        return
    fc = scene.driver_add("p25d.stroke_phase")
    drv = fc.driver
    drv.type = "SCRIPTED"
    drv.expression = f"floor(frame / {max(1, s.boil_rate)}) * 0.03"


# --------------------------------------------------------------------------
# operators
# --------------------------------------------------------------------------
SCOPE = EnumProperty(name="Scope", default="AUTO", options={"SKIP_SAVE", "HIDDEN"}, items=[
    ("AUTO", "Auto", "Selected objects, or all visible objects when nothing is selected"),
    ("ALL", "All Visible", "Every visible object"),
    ("SELECTED", "Selected", "Selected objects only")])


def _sel_meshes(context, scope="AUTO"):
    """Shadable objects (mesh/curve/text/surface, incl. collection instances)."""
    return autosetup.targets(context, scope)


def _key_sun(scene):
    """Strongest visible Sun; falls back to the light giving the most irradiance at the subject."""
    return autosetup.pick_key(scene, autosetup.subject_centre(scene))


class P25D_OT_setup_scene(bpy.types.Operator):
    bl_idname = "p25d.setup_scene"
    bl_label = "Setup Render"
    bl_description = ("EEVEE, Standard view transform, shadows; fills Light Scale from the key Sun. "
                      "Previous view settings are restored by Revert")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        vs = sc.view_settings
        if TAG + "_prev_view" not in sc:
            sc[TAG + "_prev_view"] = vs.view_transform
            sc[TAG + "_prev_look"] = vs.look
            sc[TAG + "_prev_engine"] = sc.render.engine
        sc.render.engine = "BLENDER_EEVEE"
        vs.view_transform = "Standard"
        try:
            vs.look = "None"
        except TypeError:
            pass
        sc.eevee.use_shadows = True
        sc.render.compositor_device = "GPU"
        sc.render.use_lock_interface = True
        key = sc.p25d.key_light
        if key is None or key.name not in sc.objects:
            sun = None
            if sc.p25d.auto_key_light:
                sun, made = autosetup.ensure_key_sun(sc)
                if made:
                    self.report({"INFO"}, "No Sun in the scene: added 'P25D Key Sun'")
            sun = sun or _key_sun(sc)
            if sun:
                sc.p25d.key_light = sun      # update callback creates the driver
        else:
            link_key_light(sc)
        link_boil(sc)
        sc.p25d.ambient_level = autosetup.estimate_ambient(sc)
        sp = context.space_data
        if sp and sp.type == "VIEW_3D":
            sp.shading.type = "RENDERED"
            sp.shading.use_compositor = "CAMERA"
        self.report({"INFO"}, f"Render ready (Light Scale {sc.p25d.light_scale:.2f})")
        return {"FINISHED"}


class P25D_OT_toonify(bpy.types.Operator):
    bl_idname = "p25d.toonify"
    bl_label = "Apply Toon Shader"
    bl_description = "Convert materials of the selected objects (or all visible) to the painterly toon shader"
    bl_options = {"REGISTER", "UNDO"}
    scope: SCOPE

    def execute(self, context):
        objs = _sel_meshes(context, self.scope)
        made = autosetup.ensure_materials(objs)
        n = sum(toon.toonify_material(m) for m in autosetup.materials_of(objs))
        toon.apply_toon_settings(context.scene)
        extra = f" ({made} object(s) had no material)" if made else ""
        self.report({"INFO"}, f"Toon shader on {n} material(s){extra}")
        return {"FINISHED"}


class P25D_OT_outline(bpy.types.Operator):
    bl_idname = "p25d.outline"
    bl_label = "Add Outlines"
    bl_description = "Add hand-drawn outlines (flat ground planes are skipped)"
    bl_options = {"REGISTER", "UNDO"}
    scope: SCOPE

    def execute(self, context):
        n = sum(outline.add_outline(o, context.scene)
                for o in autosetup.outline_targets(_sel_meshes(context, self.scope)))
        self.report({"INFO"}, f"Outline on {n} object(s)")
        return {"FINISHED"}


class P25D_OT_post(bpy.types.Operator):
    bl_idname = "p25d.post"
    bl_label = "Build Post FX"
    bl_description = "Create the painterly compositor (the previous compositor is remembered for Revert)"
    bl_options = {"REGISTER", "UNDO"}
    rebuild: BoolProperty(default=False, options={"SKIP_SAVE", "HIDDEN"})

    def execute(self, context):
        post.build_post(context.scene, rebuild=self.rebuild)
        return {"FINISHED"}


class P25D_OT_revert(bpy.types.Operator):
    bl_idname = "p25d.revert"
    bl_label = "Revert Painterly"
    bl_description = ("Restore original materials, remove outlines and restore compositor/view settings "
                      "(whole scene, or only the selection when 'Selected Objects Only' is on)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        full = not sc.p25d.only_selected
        objs = autosetup.all_targets(sc) if full else _sel_meshes(context, "SELECTED")
        n = sum(toon.revert_material(m) for m in autosetup.materials_of(objs))
        for o in objs:
            if o.type == "MESH":
                outline.remove_outline(o)
            if not o.is_editable:
                continue
            for s in o.material_slots:                    # object-linked slots Make It Painterly filled
                if s.link == "OBJECT" and s.material and s.material.get(TAG + "_auto"):
                    s.material = None
            mats = o.data.materials
            if getattr(o.data, "library", None):
                continue
            for i in reversed(range(len(mats))):          # drop materials Make It Painterly created
                if mats[i] and mats[i].get(TAG + "_auto"):
                    if len(mats) == 1:
                        mats.pop(index=i)
                    else:
                        mats[i] = None
        if full:
            post.remove_post(sc)
            for path in ("p25d.light_scale", "p25d.stroke_phase"):
                try:
                    sc.driver_remove(path)
                except TypeError:
                    pass
            if TAG + "_prev_view" in sc:
                sc.view_settings.view_transform = sc[TAG + "_prev_view"]
                try:
                    sc.view_settings.look = sc[TAG + "_prev_look"]
                except TypeError:
                    pass
                del sc[TAG + "_prev_view"], sc[TAG + "_prev_look"]
            if TAG + "_prev_engine" in sc:
                try:
                    sc.render.engine = sc[TAG + "_prev_engine"]
                except TypeError:
                    pass
                del sc[TAG + "_prev_engine"]
            for o in [o for o in sc.objects if o.type == "LIGHT" and o.get(TAG + "_auto")]:
                if sc.p25d.key_light == o:
                    sc.p25d.key_light = None
                ld = o.data
                bpy.data.objects.remove(o)
                if ld.users == 0:
                    bpy.data.lights.remove(ld)
        self.report({"INFO"}, f"Reverted {n} material(s)")
        return {"FINISHED"}


class P25D_OT_sketch(bpy.types.Operator):
    bl_idname = "p25d.sketch"
    bl_label = "Add Sketch Lines"
    bl_description = "Grease Pencil Line Art for the active collection (heavy on dense scenes; bake for animation)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.p25d
        before = set(context.scene.objects)
        try:
            bpy.ops.object.grease_pencil_add(type="LINEART_COLLECTION")
        except Exception as e:
            self.report({"WARNING"}, f"Line Art unavailable here: {e}")
            return {"CANCELLED"}
        gp = next((o for o in context.scene.objects if o not in before), context.active_object)
        try:
            gp.name = "P25D Sketch Lines"
            la = next((m for m in gp.modifiers if m.type == "LINEART"), None)
            if la:
                if hasattr(la, "radius"):
                    la.radius = s.sketch_radius
                elif hasattr(la, "thickness"):
                    la.thickness = int(s.sketch_radius * 2000)
                if hasattr(la, "source_collection"):
                    la.source_collection = context.collection
                for attr, val in (("use_crease", True), ("use_contour", True), ("use_intersection", False)):
                    if hasattr(la, attr):
                        setattr(la, attr, val)
            try:
                nz = gp.modifiers.new("Jitter", "GREASE_PENCIL_NOISE")
                for k, v in (("factor", s.sketch_jitter), ("noise_scale", 0.6), ("factor_thickness", 0.5)):
                    if hasattr(nz, k):
                        setattr(nz, k, v)
            except Exception:
                pass
        except Exception as e:
            bpy.data.objects.remove(gp, do_unlink=True)
            self.report({"ERROR"}, f"Sketch lines failed: {e}")
            return {"CANCELLED"}
        return {"FINISHED"}


class P25D_OT_reset(bpy.types.Operator):
    bl_idname = "p25d.reset"
    bl_label = "Reset to Defaults"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        s = sc.p25d
        s["_lock"] = True
        try:
            for name, prop in s.bl_rna.properties.items():
                if name in ("rna_type", "preset", "key_light", "light_scale", "stroke_phase", "ambient_level") or prop.is_readonly:
                    continue
                if getattr(prop, "is_array", False):
                    setattr(s, name, tuple(prop.default_array))
                elif hasattr(prop, "default"):
                    setattr(s, name, prop.default)
        finally:
            s["_lock"] = False
        _apply_all(sc)
        return {"FINISHED"}


class P25D_OT_all(bpy.types.Operator):
    bl_idname = "p25d.apply_all"
    bl_label = "Make It Painterly"
    bl_description = ("Setup render, toon shader, outlines and post FX in one click (whole scene, "
                      "or only the selection when 'Selected Objects Only' is on)")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        scope = "SELECTED" if sc.p25d.only_selected else "ALL"
        objs = _sel_meshes(context, scope)
        if not objs:
            self.report({"WARNING"}, "Nothing to paint: add or select a mesh, curve or text object")
            return {"CANCELLED"}
        bpy.ops.p25d.setup_scene()
        bpy.ops.p25d.toonify(scope=scope)
        bpy.ops.p25d.outline(scope=scope)
        if sc.p25d.auto_fit:
            autosetup.fit_to_scene(sc, objs)
        bpy.ops.p25d.post()
        _apply_all(sc)
        self.report({"INFO"}, f"Painterly look on {len(objs)} object(s)")
        return {"FINISHED"}


class P25D_OT_fit(bpy.types.Operator):
    bl_idname = "p25d.fit_scene"
    bl_label = "Fit to Scene"
    bl_description = "Set brush-dab size, depth fog and outline fade from object size and camera distance"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        sc = context.scene
        met = autosetup.fit_to_scene(sc, _sel_meshes(context))
        if met is None:
            self.report({"WARNING"}, "No measurable objects")
            return {"CANCELLED"}
        _apply_all(sc)
        self.report({"INFO"}, f"Fitted: object size {met[0]:.2f}, camera distance {met[3]:.2f}")
        return {"FINISHED"}


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
class P25D_PT_main(bpy.types.Panel):
    bl_label = "Painterly 2.5D"
    bl_idname = "P25D_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Painterly"

    def draw(self, context):
        s = context.scene.p25d
        col = self.layout.column(align=True)
        col.scale_y = 1.4
        col.operator("p25d.apply_all", icon="BRUSH_DATA")
        self.layout.prop(s, "preset")
        opt = self.layout.column(align=True)
        opt.prop(s, "only_selected")
        opt.prop(s, "auto_key_light")
        opt.prop(s, "auto_fit")
        row = self.layout.row(align=True)
        row.operator("p25d.setup_scene", icon="SCENE")
        row.operator("p25d.revert", icon="LOOP_BACK")
        row = self.layout.row(align=True)
        row.operator("p25d.fit_scene", icon="FULLSCREEN_ENTER")
        row.operator("p25d.reset", icon="FILE_REFRESH")


class _Sub:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Painterly"
    bl_parent_id = "P25D_PT_main"
    bl_options = {"DEFAULT_CLOSED"}


def _props(layout, s, keys, label=None):
    c = layout.column(align=True)
    if label:
        c.label(text=label)
    for k in keys:
        c.prop(s, k)


class P25D_PT_toon(_Sub, bpy.types.Panel):
    bl_label = "Toon & Strokes"

    def draw(self, context):
        s, l = context.scene.p25d, self.layout
        l.operator("p25d.toonify", icon="MATERIAL")
        _props(l, s, ("key_light", "light_scale", "ambient_level", "threshold", "softness", "albedo_flatten",
                      "light_influence"), "Light")
        _props(l, s, ("lit_value", "shadow_value", "shadow_saturation", "shadow_hue_shift",
                      "shadow_tint", "shadow_tint_amount"), "Shadow colour")
        _props(l, s, ("stroke_strength", "stroke_scale", "stroke_stretch", "stroke_distortion",
                      "stroke_band", "base_stroke", "stroke_seed", "stroke_boil", "dab_variation", "paint_grain"), "Brush dabs")
        _props(l, s, ("rim_strength", "rim_color", "glow_strength", "glow_threshold"), "Rim & glow")


class P25D_PT_outline(_Sub, bpy.types.Panel):
    bl_label = "Outline"

    def draw_header(self, context):
        self.layout.prop(context.scene.p25d, "outline_enable", text="")

    def draw(self, context):
        s, l = context.scene.p25d, self.layout
        l.operator("p25d.outline", icon="MOD_SOLIDIFY")
        _props(l, s, ("outline_thickness", "outline_color", "outline_screen_space", "outline_ref_distance",
                      "outline_fade_distance", "outline_fade_min", "outline_jitter", "outline_jitter_scale",
                      "outline_boil", "boil_rate", "outline_weld"))


class P25D_PT_post(_Sub, bpy.types.Panel):
    bl_label = "Post FX"

    def draw(self, context):
        s, l = context.scene.p25d, self.layout
        row = l.row(align=True)
        row.operator("p25d.post", icon="NODE_COMPOSITING")
        row.operator("p25d.post", icon="FILE_REFRESH", text="").rebuild = True
        _props(l, s, ("post_kuwahara", "kuwahara_clean", "kuwahara_size", "kuwahara_sharpness",
                      "kuwahara_eccentricity", "kuwahara_mix", "ink_protect"), "Paint")
        _props(l, s, ("dots_strength", "dots_size", "dots_color"), "Texture dots")
        _props(l, s, ("fog_start", "fog_end", "fog_amount", "fog_color"), "Depth fog")
        _props(l, s, ("bloom_threshold", "bloom_strength", "bloom_size", "halation"), "Glow")
        _props(l, s, ("paper_strength", "paper_tint", "paper_color", "dust", "grain_strength",
                      "aberration", "vignette", "vignette_color", "contrast", "black_lift", "warmth",
                      "saturation"), "Film")


class P25D_PT_sketch(_Sub, bpy.types.Panel):
    bl_label = "Sketch Lines (Line Art)"

    def draw(self, context):
        s, l = context.scene.p25d, self.layout
        l.prop(s, "sketch_radius"); l.prop(s, "sketch_jitter")
        l.operator("p25d.sketch", icon="OUTLINER_OB_GREASEPENCIL")


class P25D_PT_object(bpy.types.Panel):
    bl_label = "Painterly 2.5D Override"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == "MESH"

    def draw_header(self, context):
        self.layout.prop(context.object.p25d_obj, "use_override", text="")

    def draw(self, context):
        o = context.object.p25d_obj
        l = self.layout
        l.active = o.use_override
        _props(l, o, ("threshold", "shadow_value", "stroke_strength", "stroke_scale", "albedo_flatten",
                      "rim_strength", "light_influence", "glow_strength", "glow_color", "outline_enable",
                      "outline_scale"))


class P25D_PT_object_side(_Sub, bpy.types.Panel):
    bl_label = "Active Object Override"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == "MESH"

    def draw_header(self, context):
        self.layout.prop(context.object.p25d_obj, "use_override", text="")

    def draw(self, context):
        P25D_PT_object.draw(self, context)


@bpy.app.handlers.persistent
def _load_post(*_):
    revalidate_drivers()
    for sc in bpy.data.scenes:     # migrate old boil drivers that read scene props (depsgraph cycle)
        ad = sc.animation_data
        if ad and any(fc.data_path == "p25d.stroke_phase" for fc in ad.drivers):
            link_boil(sc)
    sc = getattr(bpy.context, "scene", None)
    if sc is not None and hasattr(sc, "p25d"):
        toon.apply_toon_settings(sc)


@bpy.app.handlers.persistent
def _save_pre(*_):
    """Refresh baked fallbacks (incl. driven Light Scale) so the file renders the same without the add-on.
    The toon group is shared, so bake the active scene only (not whichever scene sorts last)."""
    sc = getattr(bpy.context, "scene", None)
    if sc is not None and hasattr(sc, "p25d"):
        toon.apply_toon_settings(sc)


CLASSES = (P25D_Settings, P25D_ObjSettings, P25D_OT_setup_scene, P25D_OT_toonify, P25D_OT_outline,
           P25D_OT_post, P25D_OT_revert, P25D_OT_sketch, P25D_OT_reset, P25D_OT_all, P25D_OT_fit, P25D_PT_main, P25D_PT_toon,
           P25D_PT_outline, P25D_PT_post, P25D_PT_sketch, P25D_PT_object_side, P25D_PT_object)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.p25d = PointerProperty(type=P25D_Settings)
    bpy.types.Object.p25d_obj = PointerProperty(type=P25D_ObjSettings)
    if _load_post not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_load_post)
    if _save_pre not in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.append(_save_pre)
    bpy.app.timers.register(revalidate_drivers, first_interval=0.1)
    translations.register()



def unregister():
    if bpy.app.timers.is_registered(revalidate_drivers):
        bpy.app.timers.unregister(revalidate_drivers)
    translations.unregister()
    if _load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_load_post)
    if _save_pre in bpy.app.handlers.save_pre:
        bpy.app.handlers.save_pre.remove(_save_pre)
    del bpy.types.Object.p25d_obj
    del bpy.types.Scene.p25d
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
