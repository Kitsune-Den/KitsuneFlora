// Editor script — drop at Assets/Editor/AddTreeColliders.cs
//
// Menu: Tools → Kitsune → Add Tree Colliders
//
// Asset Store trees ship with visual-only LODGroup prefabs (no colliders),
// so 7DTD's hit detection has nothing to chop. This script adds a
// CapsuleCollider to each tree prefab's root, sized for the trunk so
// the player can hit it with axes etc.
//
// Run after importing/importing-changes to RoadsideTrees, then re-export
// the bundle.

using UnityEditor;
using UnityEngine;

public static class AddTreeColliders
{
    // Per-prefab capsule sizing. Center is local position; radius is trunk
    // thickness; height covers trunk to bottom of canopy.
    private static readonly (string path, float radiusY, float radius, float height, float centerY)[] Trees =
    {
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_flower_roadside_1.prefab", 0f, 0.4f, 6.5f, 3.25f),
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_leaf_roadside_1.prefab",   0f, 0.4f, 6.5f, 3.25f),
        ("Assets/RoadsideTrees/Prefabs/Keyaki_L.prefab",                        0f, 0.6f, 11f,  5.5f),
    };

    [MenuItem("Tools/Kitsune/Add Tree Colliders")]
    public static void AddColliders()
    {
        int added = 0, replaced = 0, missing = 0;
        foreach (var (path, _, radius, height, centerY) in Trees)
        {
            var go = PrefabUtility.LoadPrefabContents(path);
            if (go == null)
            {
                Debug.LogWarning($"[KitsuneFlora] Prefab not found: {path}");
                missing++;
                continue;
            }

            try
            {
                // Remove the CollisionObject0 child + any root colliders from
                // previous runs to make this idempotent.
                var oldChild = go.transform.Find("CollisionObject0");
                if (oldChild != null) Object.DestroyImmediate(oldChild.gameObject);
                foreach (var oldCol in go.GetComponents<Collider>())
                    Object.DestroyImmediate(oldCol);

                // Per War3zuk FarmLife pattern (verified working in V2.6):
                // BoxCollider goes DIRECTLY ON THE PREFAB ROOT GameObject,
                // NOT in a CollisionObject0 child. Vanilla trees' nested
                // collider pattern doesn't apply to mod-side bundles.
                var box = go.AddComponent<BoxCollider>();
                box.center = new Vector3(0f, centerY, 0f);
                box.size = new Vector3(radius * 2f, height, radius * 2f);
                box.isTrigger = false;
                added++;

                PrefabUtility.SaveAsPrefabAsset(go, path);
                Debug.Log($"[KitsuneFlora] Root BoxCollider on {System.IO.Path.GetFileNameWithoutExtension(path)}: " +
                          $"radius={radius} height={height} centerY={centerY}");
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(go);
            }
        }
        Debug.Log($"[KitsuneFlora] Done. Added={added}, Replaced={replaced}, Missing={missing}. " +
                  "Re-export the bundle.");
    }
}
