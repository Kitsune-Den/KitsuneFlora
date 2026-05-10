// Editor script — drop at Assets/Editor/RenamePrefabRoots.cs
//
// Menu: Tools → Kitsune → Rename Tree Prefab Roots
//
// Asset Store FBX-based prefabs share their root GameObject name with
// the FBX they're derived from. When OCB bundles the prefab, it ALSO
// pulls in the FBX's auto-generated GameObject — so the bundle ends up
// with TWO same-named root GameObjects: one empty (FBX) + one with our
// LODGroup/BoxCollider (the actual prefab). 7DTD's bundle loader picks
// the FBX one (empty) → walk-through.
//
// Fix: rename the prefab's root GameObject to a unique name. The .prefab
// filename stays the same; only the inner root name changes. Then update
// blocks.xml to reference the new root name.

using UnityEditor;
using UnityEngine;

public static class RenamePrefabRoots
{
    private static readonly (string path, string newRootName)[] Targets =
    {
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_flower_roadside_1.prefab", "treeKitsuneSakuraRoot"),
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_leaf_roadside_1.prefab",   "treeKitsuneSakuraLeafRoot"),
        ("Assets/RoadsideTrees/Prefabs/Keyaki_L.prefab",                        "treeKitsuneKeyakiRoot"),
    };

    [MenuItem("Tools/Kitsune/Rename Tree Prefab Roots")]
    public static void Rename()
    {
        foreach (var (path, newName) in Targets)
        {
            var go = PrefabUtility.LoadPrefabContents(path);
            if (go == null)
            {
                Debug.LogWarning($"[KitsuneFlora] Prefab not found: {path}");
                continue;
            }
            try
            {
                var oldName = go.name;
                go.name = newName;
                PrefabUtility.SaveAsPrefabAsset(go, path);
                Debug.Log($"[KitsuneFlora] Renamed root: '{oldName}' -> '{newName}' in {path}");
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(go);
            }
        }
        Debug.Log("[KitsuneFlora] Done. Re-export the bundle.");
    }
}
