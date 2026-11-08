# Painterly 2.5D — instructions for AI agents

The human only says something like *"make my Blender scene look hand-painted"*, *「水彩っぽくして」* or
*「做成油画风」*. You do everything: install, apply, show a preview.
Do not ask the human to click anything in Blender.

## 1. Find Blender
- macOS: `/Applications/Blender*.app/Contents/MacOS/Blender`
- Windows: `C:\Program Files\Blender Foundation\Blender */blender.exe`
- Linux: `blender` on PATH

Needs **5.0+** (EEVEE). Folder names don't always show the version, so ask each one and pick the newest:
```bash
for b in /Applications/Blender*.app/Contents/MacOS/Blender; do echo "$("$b" --version | head -1) | $b"; done
```

## 2. Install (once)
Get the latest `painterly_25d-<version>.zip` from https://github.com/kanaworksai-hue/painterly-25d/releases
and `agent/painterly_agent.py` from the repository:
```bash
git clone --depth 1 https://github.com/kanaworksai-hue/painterly-25d.git
gh release download -R kanaworksai-hue/painterly-25d -p 'painterly_25d-*.zip'      # with gh
# or without gh:
curl -sL "$(curl -s https://api.github.com/repos/kanaworksai-hue/painterly-25d/releases/latest \
  | grep -o 'https://[^"]*painterly_25d-[^"]*\.zip' | head -1)" -o painterly_25d.zip
```
Then:
```bash
<blender> -b --python painterly-25d/agent/painterly_agent.py -- --install painterly_25d-<version>.zip
```
Never add `--factory-startup` to the install command — the install is saved into the user's
preferences and factory startup would overwrite them. The script refuses in that case.
Success = last line starts with `PAINTERLY OK`.

## 3. Apply

### a) To a .blend file (Blender closed, headless)
```bash
<blender> -b scene.blend --python agent/painterly_agent.py -- \
    --preset DAY --medium OIL --save scene_painted.blend --render preview.png
```
Install and apply can be one command: add `--install painterly_25d-<version>.zip`.
Show the human `preview.png`. Save to a new file unless they asked to overwrite.

### b) To a model file (.glb .gltf .fbx .obj)
```bash
<blender> -b --python agent/painterly_agent.py -- --model chair.glb --preset DAY --render preview.png
```
A camera is aimed at the model and a key light is added when the scene has none.

### c) Into a running Blender (e.g. through a Blender MCP / Python console)
```python
import bpy
s = bpy.context.scene.p25d
bpy.ops.p25d.apply_all()          # Make It Painterly (whole visible scene; set s.only_selected = True for the selection)
s.preset = "GOLDEN"               # colour & mood
s.medium = "WATERCOLOR"           # technique
s.variation = 918                 # or bpy.ops.p25d.shuffle()
s.kuwahara_size = 9               # any setting, see --list
bpy.ops.p25d.revert()             # undo everything
```

## 4. Turning the human's words into options

**If the human gives no style at all** ("make it painterly"), use `--preset DAY --medium OIL`.
On later tweaks, omit what they didn't mention: the current preset, medium and variation are kept.

| They say | `--medium` |
|---|---|
| oil painting, 油絵, 油画, painterly (default) | `OIL` |
| gouache, poster colour, ガッシュ, 水粉 | `GOUACHE` |
| watercolour, 水彩, 水彩画 | `WATERCOLOR` |
| crayon, pastel crayon, クレヨン, 蜡笔 | `CRAYON` |
| coloured pencil, sketchy, 色鉛筆, 彩铅 | `PENCIL` |
| anime, cel, clean toon, アニメ塗り, 赛璐璐, 动画风 | `ANIME` |

| They say | `--preset` |
|---|---|
| daylight, storybook, 昼, 绘本 (default) | `DAY` |
| sunset, golden hour, 夕焼け, 夕阳 | `GOLDEN` |
| night, blue hour, cosy lights, 夜, 夜景 | `NIGHT` |
| pastel, sweets, cute, パステル, 马卡龙 | `PASTEL` |
| product shot, subtle, clean, 商品, 产品图 | `CLEAN` |

| They say | option |
|---|---|
| "something different", "another version", 別パターン, 换一个 | `--shuffle` (prints the variation number) |
| "go back to version 918" | `--variation 918` |
| bigger / chunkier paint, 筆を大きく, 笔触大一点 | `--set kuwahara_size=10` |
| thinner lines, 線を細く, 线细一点 | `--set outline_thickness=<current × 0.6>` |
| no outlines, 線なし, 不要描边 | `--set outline_enable=false` |
| more coloured lines, 線に色を, 彩色线条 | `--set ink_from_object=0.9` |
| less film grain / dust | `--set grain_strength=0.01 --set dust=0` |
| more dramatic shadows | `--set shadow_value=0.55` |

Unknown names fail with a hint; run `--list` and pick the closest, then tell the human what you chose.

## Getting the best result (do this, the human won't ask)
1. Render a preview (`--render preview.png --preview-size 50`) and look at it before reporting back.
   If objects are cut off, add `--frame-camera` (a separate camera; the human's own camera is not touched).
2. Offer two or three variations as small previews (e.g. two media, or `--shuffle` twice) and let the human pick
   in one word.
3. Glass and see-through materials are kept as they are on purpose. Curves and text get the toon material but no outline.
4. Report what you changed in one sentence, with the preview.

## Notes
- Don't mix up the commands: **installing** must not use `--factory-startup`; the README's Development section uses it
  only for tests and builds.
- Needs EEVEE. Make It Painterly switches the scene to EEVEE and the Standard view transform; `--revert` restores them.
- Sister add-ons: [MochiToon](https://github.com/kanaworksai-hue/mochitoon/blob/main/AGENTS.md) (manga / comic / かわいく)
  and [KiraPaint](https://github.com/kanaworksai-hue/kirapaint/blob/main/AGENTS.md) (sparkly / キラキラ / 亮晶晶).
  Pick Painterly 2.5D for oil, watercolour, crayon, pencil or anime-cel looks. Use one add-on per scene.
