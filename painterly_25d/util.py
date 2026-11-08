# SPDX-License-Identifier: GPL-3.0-or-later
"""Node-building helpers shared by the Painterly 2.5D modules."""
import bpy

TAG = "p25d"
TOON_GROUP = "P25D Toon"
OUTLINE_GROUP = "P25D Outline"
POST_GROUP = "P25D Post"
OUTLINE_MAT = "P25D Outline Ink"
OUTLINE_MOD = "P25D Outline"
AOV_SHADOW = "p25d_shadow"
AOV_LIGHT = AOV_SHADOW  # backwards name
AOV_INK = "p25d_ink"


def sock(sockets, name, kind=None):
    """Enabled socket by name (and optional type); falls back to any match."""
    for s in sockets:
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    for s in sockets:
        if s.name == name and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def new(nodes, idname, loc, label=None, **props):
    n = nodes.new(idname)
    n.location = loc
    if label:
        n.label = label
        n.name = label
    for k, v in props.items():
        setattr(n, k, v)
    return n


def iface(ng, name, in_out, stype, default=None, lo=None, hi=None):
    s = ng.interface.new_socket(name, in_out=in_out, socket_type=stype)
    if default is not None and hasattr(s, "default_value"):
        s.default_value = default
    if lo is not None and hasattr(s, "min_value"):
        s.min_value = lo
    if hi is not None and hasattr(s, "max_value"):
        s.max_value = hi
    return s


def menu(sock_, *choices):
    """Set a menu socket to the first choice this Blender build accepts."""
    for c in choices:
        try:
            sock_.default_value = c
            return c
        except TypeError:
            continue
    print(f"[Painterly 2.5D] menu value not accepted: {choices} on {sock_.node.name}.{sock_.name}")
    return None


def mix(nodes, loc, blend="MIX", dtype="RGBA", label=None):
    m = new(nodes, "ShaderNodeMix", loc, label)
    m.data_type = dtype
    if dtype == "RGBA":
        m.blend_type = blend
        m.clamp_result = False
    return m


def mix_io(m):
    kind = "RGBA" if m.data_type == "RGBA" else "VALUE"
    return (sock(m.inputs, "Factor", "VALUE"), sock(m.inputs, "A", kind),
            sock(m.inputs, "B", kind), sock(m.outputs, "Result", kind))


def math(nodes, loc, op, a=None, b=None, label=None, clamp=False):
    n = new(nodes, "ShaderNodeMath", loc, label)
    n.operation = op
    n.use_clamp = clamp
    if a is not None:
        n.inputs[0].default_value = a
    if b is not None:
        n.inputs[1].default_value = b
    return n


def vmath(nodes, loc, op, label=None):
    n = new(nodes, "ShaderNodeVectorMath", loc, label)
    n.operation = op
    return n


def srgb(hexstr):
    """'#3B1F14' -> linear RGB tuple (for colour properties)."""
    h = hexstr.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def ensure_aov(view_layer, name, kind="VALUE"):
    aov = next((a for a in view_layer.aovs if a.name == name), None)
    if aov is None:
        aov = view_layer.aovs.add()
        aov.name = name
    aov.type = kind
    return aov
