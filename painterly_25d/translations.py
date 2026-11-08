# SPDX-License-Identifier: GPL-3.0-or-later
"""UI translations (Edit > Preferences > Interface > Translation). English is the source."""
import bpy

# msgid: (Japanese, Simplified Chinese)
_UI = {
    # panels
    "Painterly 2.5D": ("Painterly 2.5D", "Painterly 2.5D"),
    "Toon & Strokes": ("トゥーン＆筆タッチ", "卡通与笔触"),
    "Outline": ("アウトライン", "描边"),
    "Post FX": ("ポストエフェクト", "后期效果"),
    "Sketch Lines (Line Art)": ("スケッチ線（ラインアート）", "素描线（线条画）"),
    "Active Object Override": ("アクティブオブジェクトの上書き", "活动物体覆盖"),
    "Painterly 2.5D Override": ("Painterly 2.5D 上書き", "Painterly 2.5D 覆盖"),
    # groups
    "Light": ("ライト", "灯光"),
    "Shadow colour": ("影の色", "阴影颜色"),
    "Brush dabs": ("筆タッチ", "笔触"),
    "Rim & glow": ("リム＆発光", "边缘光与发光"),
    "Paint": ("ペイント", "绘画"),
    "Texture dots": ("テクスチャドット", "纹理网点"),
    "Depth fog": ("深度フォグ", "深度雾"),
    "Glow": ("グロー", "辉光"),
    "Film": ("フィルム", "胶片"),
    # presets
    "Preset": ("プリセット", "预设"),
    "Default": ("デフォルト", "默认"),
    "Blue-hour Night": ("ブルーアワーの夜", "蓝调夜晚"),
    "Golden Hour": ("ゴールデンアワー", "黄金时刻"),
    "Pastel Sweets": ("パステルスイーツ", "马卡龙甜点"),
    "Storybook Day": ("絵本の昼", "绘本白天"),
    "Clean / Product": ("クリーン／プロダクト", "简洁／产品"),
    "Selected Objects Only": ("選択中のオブジェクトのみ", "仅选中物体"),
    "Add Key Light if Missing": ("キーライトがなければ追加", "缺少主光时自动添加"),
    "Fit to Scene Scale": ("シーンのスケールに合わせる", "适配场景尺寸"),
    # light / cel
    "Key Light": ("キーライト", "主光源"),
    "Light Scale": ("ライトスケール", "光照比例"),
    "Ambient Compensation": ("環境光の補正", "环境光补偿"),
    "Threshold": ("しきい値", "阈值"),
    "Softness": ("やわらかさ", "柔和度"),
    "Albedo Flatten": ("アルベド平坦化", "固有色压平"),
    "Light Colour": ("ライトの色の影響", "灯光颜色影响"),
    "Lit Value": ("明部の明るさ", "亮部明度"),
    "Shadow Value": ("影の明るさ", "阴影明度"),
    "Shadow Saturation": ("影の彩度", "阴影饱和度"),
    "Shadow Hue Shift": ("影の色相シフト", "阴影色相偏移"),
    "Shadow Tint": ("影の色味", "阴影色调"),
    "Tint Amount": ("色味の量", "色调强度"),
    # strokes
    "Stroke Strength": ("筆タッチの強さ", "笔触强度"),
    "Stroke Scale": ("筆タッチの細かさ", "笔触密度"),
    "Stroke Stretch": ("筆タッチの伸び", "笔触拉伸"),
    "Stroke Distortion": ("筆タッチのゆがみ", "笔触扭曲"),
    "Terminator Band": ("明暗境界の幅", "明暗交界带"),
    "Lit Brush Texture": ("明部の筆質感", "亮部笔刷质感"),
    "Stroke Seed": ("筆タッチのシード", "笔触种子"),
    "Dab Boil": ("筆タッチのゆらぎ", "笔触抖动"),
    "Paint Grain": ("絵の具の粒子", "颜料颗粒"),
    "Dab Variation": ("筆タッチのばらつき", "笔触变化"),
    "Rim": ("リムライト", "边缘光"),
    "Rim Colour": ("リムの色", "边缘光颜色"),
    "Texture Glow": ("テクスチャ発光", "贴图发光"),
    "Glow Threshold": ("発光しきい値", "发光阈值"),
    "Glow Colour": ("発光色", "发光颜色"),
    # outline
    "Outlines": ("アウトライン", "描边"),
    "Thickness": ("太さ", "粗细"),
    "Constant Screen Width": ("画面上で一定の太さ", "屏幕恒定粗细"),
    "Reference Distance": ("基準距離", "参考距离"),
    "Fade Distance": ("フェード距離", "渐隐距离"),
    "Far Width": ("遠景の太さ", "远处粗细"),
    "Hand Jitter": ("手描きのゆらぎ", "手绘抖动"),
    "Jitter Scale": ("ゆらぎの細かさ", "抖动尺度"),
    "Line Boil": ("線のゆらぎ（ボイル）", "线条抖动"),
    "Boil Rate (frames)": ("ゆらぎ間隔（フレーム）", "抖动间隔（帧）"),
    "Ink Colour": ("線の色", "线条颜色"),
    "Weld UV Seams": ("UVシームを溶接", "焊接UV接缝"),
    "Outline Width x": ("アウトライン太さ倍率", "描边粗细倍数"),
    "Override": ("上書き", "覆盖"),
    # post
    "Kuwahara": ("桑原フィルタ", "桑原滤镜"),
    "Clean Size": ("下地サイズ", "底层尺寸"),
    "Paint Size": ("筆サイズ", "笔触尺寸"),
    "Sharpness": ("シャープさ", "锐度"),
    "Eccentricity": ("異方性", "各向异性"),
    "Paint Amount": ("油彩の量", "油画强度"),
    "Ink Protect": ("線の保護", "线条保护"),
    "Texture Dots": ("テクスチャドット", "纹理网点"),
    "Dot Spacing (px @1920)": ("ドット間隔（px @1920）", "网点间距（px @1920）"),
    "Dot Colour": ("ドットの色", "网点颜色"),
    "Fog Start": ("フォグ開始", "雾起始"),
    "Fog End": ("フォグ終了", "雾结束"),
    "Fog": ("フォグ", "雾"),
    "Fog Colour": ("フォグの色", "雾颜色"),
    "Bloom Threshold": ("ブルームしきい値", "泛光阈值"),
    "Bloom Strength": ("ブルームの強さ", "泛光强度"),
    "Bloom Size": ("ブルームのサイズ", "泛光尺寸"),
    "Halation": ("ハレーション", "光晕"),
    "Paper": ("紙の質感", "纸纹"),
    "Paper Tint": ("紙の色味", "纸张色调"),
    "Paper Colour": ("紙の色", "纸张颜色"),
    "Sensor Dust": ("レンズのほこり", "镜头灰尘"),
    "Grain": ("フィルム粒子", "胶片颗粒"),
    "Aberration": ("色収差", "色差"),
    "Vignette": ("周辺減光", "暗角"),
    "Vignette Colour": ("周辺減光の色", "暗角颜色"),
    "Black Lift": ("黒の持ち上げ", "黑位提升"),
    "Contrast": ("コントラスト", "对比度"),
    "Warmth": ("暖かさ", "色温"),
    "Saturation": ("彩度", "饱和度"),
    # 1.1: media + variation
    "Medium": ("画材", "画材"),
    "Oil Paint": ("油絵", "油画"),
    "Gouache": ("ガッシュ", "水粉"),
    "Watercolour": ("水彩", "水彩"),
    "Crayon": ("クレヨン", "蜡笔"),
    "Coloured Pencil": ("色鉛筆", "彩色铅笔"),
    "Anime Cel": ("アニメ塗り", "动画赛璐璐"),
    "Variation": ("バリエーション", "变化"),
    "Stroke Angle": ("筆の向き", "笔触方向"),
    "Colour Jitter": ("色のゆらぎ", "颜色抖动"),
    "Colour Drift": ("色むら", "颜色斑驳"),
    "Colour variation": ("色のばらつき", "颜色变化"),
    "Ink From Object Colour": ("線にモデルの色を使う", "线条使用物体颜色"),
    "Shadow pattern": ("影の模様", "阴影图案"),
    "Shadow Pattern": ("影の模様", "阴影图案"),
    "Dots": ("網点", "网点"),
    "Hatching": ("斜線", "排线"),
    "Cross-hatching": ("クロスハッチング", "交叉排线"),
    "Edge Darkening": ("にじみの縁", "边缘积色"),
    "Wet Wobble (px @1920)": ("にじみのゆらぎ（px @1920）", "湿边抖动（px @1920）"),
    "Granulation": ("顔料の粒状感", "颜料颗粒沉淀"),
    "Paper Tooth": ("紙の凹凸", "纸面纹理"),
    "Animated Grain": ("粒子のアニメーション", "颗粒动画"),
    "Line Radius": ("線の半径", "线条半径"),
    "Line Jitter": ("線のゆらぎ", "线条抖动"),
}

_OPS = {
    "Make It Painterly": ("ワンクリックで絵画風に", "一键绘画风格"),
    "Setup Render": ("レンダー設定", "渲染设置"),
    "Apply Toon Shader": ("トゥーンシェーダーを適用", "应用卡通着色器"),
    "Add Outlines": ("アウトラインを追加", "添加描边"),
    "Build Post FX": ("ポストエフェクトを作成", "创建后期效果"),
    "Revert Painterly": ("絵画風を解除", "撤销绘画风格"),
    "Add Sketch Lines": ("スケッチ線を追加", "添加素描线"),
    "Reset to Defaults": ("初期値にリセット", "恢复默认值"),
    "Fit to Scene": ("シーンに合わせる", "适配场景"),
    "Shuffle": ("シャッフル", "随机一下"),
}


def _build():
    ja, zh = {}, {}
    for msg, (j, z) in _UI.items():
        ja[("*", msg)] = j
        zh[("*", msg)] = z
    for msg, (j, z) in _OPS.items():
        ja[("Operator", msg)] = j
        zh[("Operator", msg)] = z
        ja[("*", msg)] = j
        zh[("*", msg)] = z
    return {"ja_JP": ja, "zh_HANS": zh, "zh_CN": zh}


def register():
    try:
        bpy.app.translations.register(__package__, _build())
    except ValueError:
        pass   # already registered (reload)


def unregister():
    try:
        bpy.app.translations.unregister(__package__)
    except ValueError:
        pass
