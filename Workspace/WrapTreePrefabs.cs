// Editor script ~ drop at Assets/Editor/WrapTreePrefabs.cs
//
// Menu: Tools → Kitsune → Wrap Tree Prefabs With Unique Roots
//
// Creates NEW prefab files (KitsuneTreeWrappers/<unique>.prefab) that
// each contain a wrapper GameObject with our unique name, with the
// original Asset Store prefab dragged in as a child. The new files have
// unique names ~ Unity auto-syncs root GameObject name to FILE name, so
// we use NEW filenames to escape the FBX-name collision.
//
// Original Asset Store prefabs are left untouched. Bundle should be
// re-pointed at the new wrapper paths.

using System.IO;
using UnityEditor;
using UnityEngine;

public static class WrapTreePrefabs
{
    private const string OutDir = "Assets/KitsuneTreeWrappers";

    // sourcePath, newName, collider radius, collider height, collider centerY, wrapper localScale
    // The Asset Store pack's "_2" / "_S" variants are still full-sized trees, just slightly
    // less imposing than the "_1" / "_L" versions. To make them read as saplings in-game,
    // we apply a localScale shrink at wrap time (~0.35) so they end up ankle-to-knee height.
    // Collider radius/height/center are pre-scaled values ~ they describe the FINAL world
    // size after Unity applies the wrapper's localScale, so collider matches what you see.
    private static readonly (string sourcePath, string newName, float radius, float height, float centerY, float scale)[] Targets =
    {
        // ============================================================
        // Mature trees (large variants from the Asset Store pack).
        // These are what biome decoration spawns and what the seed
        // block grows into via PlantGrowing.Next.
        // Trunk-sized collider ~ matches MultiBlockDim 1x1 base and
        // keeps HP-bar attached to the right block when chopping.
        // ============================================================
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_flower_roadside_1.prefab", "treeKitsuneSakuraRoot",          0.4f, 6.5f, 3.25f, 1f),
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_leaf_roadside_1.prefab",   "treeKitsuneSakuraLeafRoot",      0.4f, 6.5f, 3.25f, 1f),
        ("Assets/RoadsideTrees/Prefabs/Keyaki_L.prefab",                        "treeKitsuneKeyakiRoot",          0.4f, 11f,  5.5f,  1f),

        // ============================================================
        // Phase B mature trees ~ one variant each, no Sml/Med Asset Store
        // versions in this pack. Pink + White Dogwood map to bloom + leaf
        // variants (matching the sakura two-state pattern). Plane_tree
        // is actually the ginkgo (Asset Store mistranslation).
        // ============================================================
        ("Assets/RoadsideTrees/Prefabs/Dogwood_pink.prefab",                    "treeKitsuneDogwoodRoot",         0.4f, 6f,   3f,    1f),
        ("Assets/RoadsideTrees/Prefabs/Dogwood_white.prefab",                   "treeKitsuneDogwoodLeafRoot",     0.4f, 6f,   3f,    1f),
        ("Assets/RoadsideTrees/Prefabs/Plane_tree_roadside.prefab",             "treeKitsunePlaneTreeRoot",       0.5f, 10f,  5f,    1f),
        // Azalea_wide parked ~ flat-bush mesh fights with 7DTD voxel rendering
        // ("Assets/RoadsideTrees/Prefabs/Azalea_wide.prefab",                  "treeKitsuneAzaleaRoot",          0.6f, 2.5f, 1.25f, 1f),

        // ============================================================
        // Small variants ~ wrapped at 0.35 localScale to read as saplings.
        // Collider params describe the FINAL (post-scale) size in world meters.
        // Hitbox radius bumped to ~0.5m wide so melee aim isn't a needle-thread.
        // ============================================================
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_flower_roadside_2.prefab", "treeKitsuneSakuraSmallRoot",     0.5f, 2.2f, 1.1f,  0.35f),
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_leaf_roadside_2.prefab",   "treeKitsuneSakuraLeafSmallRoot", 0.5f, 2.2f, 1.1f,  0.35f),
        ("Assets/RoadsideTrees/Prefabs/Keyaki_S.prefab",                        "treeKitsuneKeyakiSmallRoot",     0.6f, 2.8f, 1.4f,  0.35f),

        // ============================================================
        // Phase B small variants ~ pack has no _S/_2 for these, so we
        // reuse the same mature prefab at 0.35 scale for the seed-stage
        // visual. Same trick as sakura, just without an Asset-Store-
        // dedicated small-variant mesh.
        // ============================================================
        ("Assets/RoadsideTrees/Prefabs/Dogwood_pink.prefab",                    "treeKitsuneDogwoodSmallRoot",    0.5f, 2.1f, 1.05f, 0.35f),
        ("Assets/RoadsideTrees/Prefabs/Plane_tree_roadside.prefab",             "treeKitsunePlaneTreeSmallRoot",  0.5f, 3.5f, 1.75f, 0.35f),
        // ("Assets/RoadsideTrees/Prefabs/Azalea_wide.prefab",                  "treeKitsuneAzaleaSmallRoot",     0.4f, 0.4f, 0.2f,  0.35f),
    };

    [MenuItem("Tools/Kitsune/Wrap Tree Prefabs With Unique Roots")]
    public static void Wrap()
    {
        if (!AssetDatabase.IsValidFolder(OutDir))
            AssetDatabase.CreateFolder("Assets", "KitsuneTreeWrappers");

        foreach (var (sourcePath, newName, radius, height, centerY, scale) in Targets)
        {
            var sourcePrefab = AssetDatabase.LoadAssetAtPath<GameObject>(sourcePath);
            if (sourcePrefab == null)
            {
                Debug.LogWarning($"[KitsuneFlora] Source prefab not found: {sourcePath}");
                continue;
            }

            // Build the wrapper GameObject in memory.
            var wrapper = new GameObject(newName);
            try
            {
                // Instantiate the source as a child of the wrapper. Then
                // strip the wrapper-of-wrapper by hoisting children up.
                var inner = (GameObject)PrefabUtility.InstantiatePrefab(sourcePrefab);
                inner.transform.SetParent(wrapper.transform, false);

                // Scale the inner child instead of the wrapper, so the
                // BoxCollider on the wrapper stays at world-meter scale
                // (the radius/height values describe final visible size).
                if (scale != 1f)
                    inner.transform.localScale = Vector3.one * scale;

                // Strip ALL colliders from the inner asset ~ Asset Store tree
                // prefabs ship with their own trunk capsules/boxes, and those
                // overlap our wider wrapper collider causing HP-bar flicker
                // (raycast bounces between them). Only the wrapper's collider
                // should exist on the saved prefab.
                foreach (var c in inner.GetComponentsInChildren<Collider>(true))
                    Object.DestroyImmediate(c);

                // Add BoxCollider on the wrapper root.
                var box = wrapper.AddComponent<BoxCollider>();
                box.center = new Vector3(0f, centerY, 0f);
                box.size = new Vector3(radius * 2f, height, radius * 2f);
                box.isTrigger = false;

                // Save wrapper as a brand-new prefab file with unique name.
                var outPath = $"{OutDir}/{newName}.prefab";
                PrefabUtility.SaveAsPrefabAsset(wrapper, outPath);
                Debug.Log($"[KitsuneFlora] Created wrapper prefab: {outPath} (scale={scale})");
            }
            finally
            {
                Object.DestroyImmediate(wrapper);
            }
        }
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log($"[KitsuneFlora] Done. Wrappers created in {OutDir}/. " +
                  "Update the Bundle asset's Objects list to point at these new prefabs, then re-export.");
    }
}
