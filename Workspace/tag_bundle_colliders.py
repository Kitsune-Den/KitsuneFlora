"""Dev tool: tag every Kitsune wrapper-root collider as T_Block in the built bundle.

Why this exists
---------------
7 Days to Die only treats a melee hit on a Shape="ModelEntity" block as a BLOCK
hit when the collider that was struck carries the game's "T_Block" tag
(Voxel.raycastNew -> GameUtils.FindMasterBlockForEntityModelBlock). The engine
never assigns that tag itself; vanilla prefabs ship with it. A bundle exported
from a Unity project that doesn't share the game's tag table comes out
"Untagged", so the punch lands on the collider, is classed as a non-block hit,
and nothing happens: boxwood / painted fern / planted grove seeds can't be hit.

(Real trees are unaffected either way: BlockModelTree re-tags its colliders
T_Deco at runtime.)

Unity serializes a custom tag as 20000 + its index in the PLAYER's tag table,
so the number below must match the game build, not the mod's Unity project.
It is read from the game's own data file when --game is given.

Usage:
    python Workspace/tag_bundle_colliders.py IN.unity3d OUT.unity3d
    python Workspace/tag_bundle_colliders.py IN.unity3d OUT.unity3d --game "G:/.../7 Days To Die"
    python Workspace/tag_bundle_colliders.py IN.unity3d --check      # report only

IN and OUT must differ; the input is never modified.
"""
import sys

import UnityPy

T_BLOCK_DEFAULT = 20004  # "T_Block" in 7DTD V2.6 through V3.4 (tags[4])


def game_tag_id(game_dir, name="T_Block"):
    env = UnityPy.load(f"{game_dir}/7DaysToDie_Data/data.unity3d")
    for o in env.objects:
        if o.type.name == "TagManager":
            tags = o.read_typetree()["tags"]
            return 20000 + tags.index(name)
    raise SystemExit("TagManager not found in game data")


def main():
    args = sys.argv[1:]
    check = "--check" in args
    if check:
        args.remove("--check")
    tag_id = T_BLOCK_DEFAULT
    if "--game" in args:
        i = args.index("--game")
        tag_id = game_tag_id(args[i + 1])
        del args[i:i + 2]
    if len(args) != (1 if check else 2):
        raise SystemExit(__doc__)
    src = args[0]
    dst = None if check else args[1]
    if dst and dst.replace("\\", "/").lower() == src.replace("\\", "/").lower():
        raise SystemExit("OUT must differ from IN")

    env = UnityPy.load(src)
    colliders_by_go = set()
    for o in env.objects:
        if o.type.name.endswith("Collider"):
            go = o.read_typetree().get("m_GameObject", {}).get("m_PathID", 0)
            colliders_by_go.add(go)

    changed = already = 0
    for o in env.objects:
        if o.type.name != "GameObject" or o.path_id not in colliders_by_go:
            continue
        d = o.read_typetree()
        name = d.get("m_Name", "")
        if not name.startswith("treeKitsune"):
            continue
        if d.get("m_Tag") == tag_id:
            already += 1
            print(f"  ok       {name}")
            continue
        print(f"  {'UNTAGGED' if check else 'tagging '} {name}  (m_Tag {d.get('m_Tag')} -> {tag_id})")
        changed += 1
        if not check:
            d["m_Tag"] = tag_id
            o.save_typetree(d)

    print(f"T_Block id {tag_id}: {already} already tagged, {changed} {'need tagging' if check else 'tagged'}")
    if check:
        sys.exit(1 if changed else 0)
    with open(dst, "wb") as f:
        f.write(env.file.save(packer="lz4"))
    print(f"wrote {dst}")


if __name__ == "__main__":
    main()
