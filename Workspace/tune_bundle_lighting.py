"""Dev tool: set ambient strength (and optionally scale the tint) on the tree
materials in a built bundle, without a Unity rebuild.

Why this exists
---------------
The two tree shaders (Tree_Bumped_Diffuse_twosided_alpha and its _Wind variant)
used to take Unity's stock ambient light at full strength. In game that made
every Flora tree, bark included, look lit at night while vanilla trees went
dark. The shaders now switch stock ambient off (`noambient`) and add it back
themselves, multiplied by a material property, `_AmbientScale`.

Turning the tint (`_Color`) down does NOT fix the glow: it darkens daylight by
the same amount. Ambient and tint are separate knobs:

    _AmbientScale   how much ambient light the material takes (night glow, and
                    how bright shaded sides are by day)
    _Color          overall tint (sun and moon light, and ambient too)

Shipped values (0.4.1): _AmbientScale 0.3 on every tree material, tints at
1.5x their old values (capped at 1.0). Those values are also saved in the
Unity project's materials, so a plain rebuild already has them; use this tool
to try other values quickly.

Only materials that carry `_AmbientScale` are touched, so a bundle built from
the old shaders is left alone (and reported as 0 materials).

Usage:
    python Workspace/tune_bundle_lighting.py IN.unity3d OUT.unity3d --ambient 0.3
    python Workspace/tune_bundle_lighting.py IN.unity3d OUT.unity3d --ambient 0.3 --tint-mul 1.5
    python Workspace/tune_bundle_lighting.py IN.unity3d --show        # report only

IN and OUT must differ; the input is never modified. --tint-mul multiplies the
tint already in IN, so run it once from a fresh export, not repeatedly.
"""
import argparse

import UnityPy


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--ambient", type=float)
    ap.add_argument("--tint-mul", type=float, default=1.0)
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()

    if a.show:
        if a.dst:
            ap.error("--show takes only IN")
    else:
        if not a.dst or a.ambient is None:
            ap.error("need OUT and --ambient (or use --show)")
        if a.dst.replace("\\", "/").lower() == a.src.replace("\\", "/").lower():
            ap.error("OUT must differ from IN")

    env = UnityPy.load(a.src)
    n = 0
    for o in env.objects:
        if o.type.name != "Material":
            continue
        d = o.read_typetree()
        sp = d["m_SavedProperties"]
        floats = sp["m_Floats"]
        idx = next((i for i, (k, _) in enumerate(floats) if k == "_AmbientScale"), None)
        if idx is None:
            continue
        n += 1
        color = next((c for k, c in sp["m_Colors"] if k == "_Color"), None)
        old_amb = floats[idx][1]
        old_tint = color["r"] if color else None
        if a.show:
            print(f"  {d['m_Name']:40s} ambient {old_amb:.2f}  tint {old_tint:.2f}")
            continue
        floats[idx] = ("_AmbientScale", a.ambient)
        if color and a.tint_mul != 1.0:
            for ch in "rgb":
                color[ch] = min(1.0, color[ch] * a.tint_mul)
        o.save_typetree(d)
        print(f"  {d['m_Name']:40s} ambient {old_amb:.2f} -> {a.ambient:.2f}  "
              f"tint {old_tint:.2f} -> {color['r']:.2f}")

    print(f"{n} tree materials {'found' if a.show else 'updated'}")
    if a.show:
        return
    with open(a.dst, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print(f"wrote {a.dst}")


if __name__ == "__main__":
    main()
