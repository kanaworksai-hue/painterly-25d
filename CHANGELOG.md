# Changelog

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
