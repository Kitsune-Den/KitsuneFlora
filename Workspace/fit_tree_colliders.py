"""Dev tool: fit the tree colliders in a built bundle to their trunks.

Why this exists
---------------
Trees and planted tree seeds are tree-class blocks: they extend treeMaster /
treeMasterGrowing, so their shape is DistantDecoTree. When the model spawns,
the game re-tags every collider T_Deco and moves it to the tree collision layer
(BlockShapeDistantDecoTree.OnBlockEntityTransformAfterActivated). That makes the
collider solid to players no matter what `Collide` says in blocks.xml, and it is
also what the crosshair hits.

The wrapper boxes used to be far wider than the trunks: saplings carried a box
about 1 m wide and up to 3.5 m tall (an invisible wall around a freshly planted
seed), a cherry tree a 0.8 m box around a 0.4 m trunk, a dogwood a 0.8 m box
around a 0.15 m trunk. Trees can be placed at 45 degrees, so a box corner
sticks out further still, and tools aim with a small sphere cast on top of
that. The result: you bumped into air and could "hit" a tree while aiming well
beside it. This sets each box to roughly the trunk.

Boxwood, ferns and planted bamboo are crop-class blocks (cropsGrowingMaster),
where `Collide="melee"` works, so they are not touched. Bamboo clumps are about
as wide as their boxes already.

The same sizes are saved in the Unity project's wrapper prefabs and in
WrapTreePrefabs.cs, so a plain rebuild already has them; this tool patches a
bundle built before that, and --check guards against the big boxes coming back.

Usage:
    python Workspace/fit_tree_colliders.py IN.unity3d OUT.unity3d
    python Workspace/fit_tree_colliders.py IN.unity3d --check     # report only

IN and OUT must differ; the input is never modified.
"""
import sys

import UnityPy

# wrapper root name -> (width, height, depth[, centre x, centre z]) in metres.
# The box sits on the ground; centre x/z default to 0 (the middle of the block).
TREE_BOXES = {
    # saplings and the mid black pine
    "treeKitsuneSakuraSmallRoot": (0.3, 2.2, 0.3),
    "treeKitsuneSakuraLeafSmallRoot": (0.3, 2.2, 0.3),
    "treeKitsuneKeyakiSmallRoot": (0.3, 2.5, 0.3),
    "treeKitsuneDogwoodSmallRoot": (0.3, 1.5, 0.3),
    "treeKitsunePlaneTreeSmallRoot": (0.3, 2.6, 0.3),
    "treeKitsuneBlackPineSmallRoot": (0.3, 1.0, 0.3),
    "treeKitsuneBlackPineMidRoot": (0.4, 2.5, 0.4),
    # mature trees; trunk width measured 0.2 m to 1.8 m above the ground
    # The cherry trunk leans: between 0.9 m and 1.8 m up it spans x -0.31..0.04,
    # z -0.08..0.34, so the box is centred on that, not on the block.
    "treeKitsuneSakuraRoot": (0.4, 6.5, 0.4, -0.13, 0.13),
    "treeKitsuneSakuraLeafRoot": (0.4, 6.5, 0.4, -0.13, 0.13),
    "treeKitsuneDogwoodRoot": (0.3, 4.4, 0.3),       # trunk 0.15-0.2
    "treeKitsuneDogwoodLeafRoot": (0.3, 4.4, 0.3),
    "treeKitsuneKeyakiRoot": (0.55, 11.0, 0.55),     # trunk 0.45-0.6
    "treeKitsunePlaneTreeRoot": (0.4, 7.0, 0.4),     # trunk 0.3-0.4
    "treeKitsuneBlackPineRoot": (1.0, 5.0, 1.0),     # trunk 0.8-1.0 at the base
}


def main():
    args = sys.argv[1:]
    check = "--check" in args
    if check:
        args.remove("--check")
    if len(args) != (1 if check else 2):
        raise SystemExit(__doc__)
    src = args[0]
    dst = None if check else args[1]
    if dst and dst.replace("\\", "/").lower() == src.replace("\\", "/").lower():
        raise SystemExit("OUT must differ from IN")

    env = UnityPy.load(src)
    names = {o.path_id: o.read_typetree().get("m_Name", "")
             for o in env.objects if o.type.name == "GameObject"}

    seen = set()
    changed = 0
    for o in env.objects:
        if o.type.name != "BoxCollider":
            continue
        d = o.read_typetree()
        name = names.get(d["m_GameObject"]["m_PathID"], "")
        want = TREE_BOXES.get(name)
        if want is None:
            continue
        seen.add(name)
        size, center = d["m_Size"], d["m_Center"]
        have = (size["x"], size["y"], size["z"])
        cx, cz = (want[3], want[4]) if len(want) == 5 else (0.0, 0.0)
        want = want[:3]
        ok = (all(abs(h - w) < 1e-4 for h, w in zip(have, want))
              and abs(center["x"] - cx) < 1e-4 and abs(center["y"] - want[1] / 2) < 1e-4
              and abs(center["z"] - cz) < 1e-4)
        if ok:
            print(f"  ok        {name}")
            continue
        changed += 1
        fmt = lambda t: " x ".join(f"{v:g}" for v in t)
        print(f"  {'MISFIT  ' if check else 'fitting  '} {name}  ({fmt(have)} -> {fmt(want)})")
        if not check:
            size["x"], size["y"], size["z"] = want
            center["x"], center["y"], center["z"] = cx, want[1] / 2, cz
            o.save_typetree(d)

    missing = sorted(set(TREE_BOXES) - seen)
    for name in missing:
        print(f"  MISSING   {name}")
    print(f"{len(seen) - changed} already fitted, {changed} {'need fitting' if check else 'fitted'}")
    if check:
        sys.exit(1 if changed or missing else 0)
    if missing:
        raise SystemExit("some tree wrappers were not found; nothing written")
    with open(dst, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
