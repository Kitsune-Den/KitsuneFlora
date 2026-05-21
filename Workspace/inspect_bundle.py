"""Dev tool: verify each Kitsune wrapper root points at the mesh it should.

Walks the bundle hierarchy from each wrapper-root GameObject down to its
MeshFilter / SkinnedMeshRenderer meshes and MeshRenderer materials, so you can
confirm e.g. treeKitsunePaintedFernRoot actually contains FERN meshes and not
boxwood ones.

Usage:
    python Workspace/inspect_bundle.py                  # every treeKitsune*Root
    python Workspace/inspect_bundle.py PaintedFern Bamboo   # name-substring filter
    python Workspace/inspect_bundle.py --bundle path/to/X.unity3d

Defaults to the repo's exported bundle.
"""
import sys
import UnityPy

DEFAULT_BUNDLE = r"C:\Users\darab\IdeaProjects\KitsuneFlora\KitsuneFlora\Resources\Bundles\KitsuneFlora.unity3d"

args = sys.argv[1:]
BUNDLE = DEFAULT_BUNDLE
if "--bundle" in args:
    i = args.index("--bundle")
    BUNDLE = args[i + 1]
    del args[i:i + 2]
FILTERS = args  # remaining args are name substrings; empty == all wrapper roots

env = UnityPy.load(BUNDLE)

trees = {}          # path_id -> (type_name, dict)
for o in env.objects:
    try:
        trees[o.path_id] = (o.type.name, o.read_typetree())
    except Exception:
        pass

def pid(ptr):
    return ptr.get("m_PathID", 0) if isinstance(ptr, dict) else 0

# index helpers
go_by_pid = {p: d for p, (t, d) in trees.items() if t == "GameObject"}
transforms = {p: d for p, (t, d) in trees.items() if t in ("Transform", "RectTransform")}

# Transform path_id -> owning GameObject path_id
tf_to_go = {p: pid(d.get("m_GameObject", {})) for p, d in transforms.items()}
# GameObject path_id -> its Transform path_id
go_to_tf = {}
for p, d in transforms.items():
    go_to_tf[pid(d.get("m_GameObject", {}))] = p

def go_name(go_pid):
    return go_by_pid.get(go_pid, {}).get("m_Name", "?")

def components_of(go_pid):
    d = go_by_pid.get(go_pid, {})
    comps = []
    for c in d.get("m_Component", []):
        cp = pid(c.get("component", c) if isinstance(c, dict) else c)
        if cp in trees:
            comps.append((trees[cp][0], trees[cp][1]))
    return comps

def mesh_name(mesh_pid):
    if mesh_pid in trees and trees[mesh_pid][0] == "Mesh":
        return trees[mesh_pid][1].get("m_Name", "?")
    return f"<external pid={mesh_pid}>" if mesh_pid else None

def mat_name(mat_pid):
    if mat_pid in trees and trees[mat_pid][0] == "Material":
        return trees[mat_pid][1].get("m_Name", "?")
    return f"<external pid={mat_pid}>" if mat_pid else None

def walk(go_pid, depth, seen):
    if go_pid in seen:
        return
    seen.add(go_pid)
    indent = "  " * depth
    meshes, mats = [], []
    for tname, cd in components_of(go_pid):
        if tname in ("MeshFilter", "SkinnedMeshRenderer"):
            m = mesh_name(pid(cd.get("m_Mesh", {})))
            if m:
                meshes.append(m)
        if tname in ("MeshRenderer", "SkinnedMeshRenderer"):
            for mp in cd.get("m_Materials", []):
                mn = mat_name(pid(mp))
                if mn:
                    mats.append(mn)
    tag = ""
    if meshes:
        tag += f"  mesh=[{', '.join(meshes)}]"
    if mats:
        tag += f"  mat=[{', '.join(mats)}]"
    print(f"{indent}- {go_name(go_pid)}{tag}")
    tf = go_to_tf.get(go_pid)
    if tf:
        for child in transforms.get(tf, {}).get("m_Children", []):
            ctf = pid(child)
            cgo = tf_to_go.get(ctf)
            if cgo:
                walk(cgo, depth + 1, seen)

# wrapper roots = top-level GameObjects whose name looks like a Kitsune wrapper
roots = sorted({
    d["m_Name"] for d in go_by_pid.values()
    if d.get("m_Name", "").startswith("treeKitsune") and "Root" in d.get("m_Name", "")
})
if FILTERS:
    roots = [r for r in roots if any(f.lower() in r.lower() for f in FILTERS)]

if not roots:
    print(f"No matching wrapper roots in {BUNDLE}")
    sys.exit(1)

print(f"Bundle: {BUNDLE}\nMatched {len(roots)} wrapper root(s)")
for root in roots:
    matches = [p for p, d in go_by_pid.items() if d.get("m_Name") == root]
    print(f"\n=== {root}  ({len(matches)} GameObject(s) with this name) ===")
    for p in matches:
        walk(p, 0, set())
