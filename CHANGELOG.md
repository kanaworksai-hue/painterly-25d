# Changelog

## 1.1.1 (2026-11-08): no more surface flicker

- **Dab Boil is now off by default.** It re-drew the brush dabs every 2 frames, so about 30 % of the picture changed
  between frames and surfaces shimmered (colour jitter followed the dabs and made it stronger). The effect is still
  there: turn on *Toon & Strokes › Brush dabs › Dab Boil* for the hand-drawn-animation look.
- **Film grain stays still by default.** New *Animated Grain* toggle (Post FX › Film) brings back per-frame grain.
- The hand-drawn outline still boils on twos (about 1.5 % of pixels per step).
- Reset to Defaults now also removes the dab-boil driver.
- Test: a static shot with default settings must not flicker.
- Files made with 1.1.0 keep their saved settings: untick *Dab Boil* there if surfaces shimmer.

## 1.1.0 (2026-11-08): media, shuffle and more variety

- **Medium** menu: Oil Paint (default), Gouache, Watercolour, Crayon, Coloured Pencil, Anime Cel.
  Media only change technique settings, presets only change colour and mood, so any combination works.
- **Variation / Shuffle**: one number re-rolls brush direction, stroke stretch, colour jitter, shadow tint, warmth,
  saturation, line colour, paint size and paper around the current preset and medium. 0 restores the base look;
  the same number always gives the same look.
- Toon shader: **Colour Jitter** (per-dab hue / saturation / value shift), **Colour Drift** (large soft patches) and
  **Stroke Angle**.
- Outlines: **Ink From Object Colour** tints each object's lines with a darker shade of its own colour.
- Post FX: **Edge Darkening**, **Wet Wobble**, **Granulation**, **Paper Tooth**, and a **Shadow Pattern** choice
  (dots, hatching, cross-hatching).
- AI agents: `AGENTS.md` and `agent/painterly_agent.py` (install, paint a .blend or a model file, preview, revert).
- README in Japanese, English and Simplified Chinese with gallery images.

## 1.0.0 (2026-11-08): first public release

- One-click **Make It Painterly** for any scene: toon shader, outlines, post FX and render setup.
- Generic setup:
  - Auto materials (keeps vertex colours).
  - Base colour from non-Principled materials.
  - Glass and alpha-blended surfaces left untouched.
  - Collection instances supported.
  - Automatic key Sun when the scene has none.
  - *Fit to Scene* (dab size, fog, outline fade from object size and camera distance).
  - *Ambient Compensation* for bright worlds and HDRIs.
- Presets: Blue-hour Night, Golden Hour, Pastel Sweets, Storybook Day, Clean / Product.
- Per-object overrides, Revert, Reset to Defaults.
- UI translations: Japanese and Simplified Chinese.
- Headless test: `tests/test_generic.py`.
