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

using System.Collections.Generic;
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

        // ============================================================
        // FreeJapaneseGarden pack (Waldemarst). 14 wrappers.
        // Bamboo + Black Pine ship real Small/Mid/Big meshes — true
        // 3-stage growth chains (no scale-hack). All scale=1; the size
        // IS the mesh. Collider values are first-pass estimates.
        // ============================================================

        // -- Bamboo _01 set: the plantable 3-stage growth chain --
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Small_Green_01.prefab",      "treeKitsuneBambooSmallRoot",     0.3f,  1.5f, 0.75f, 1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Mid_Green_01.prefab",        "treeKitsuneBambooMidRoot",       0.35f, 3f,   1.5f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_01.prefab",        "treeKitsuneBambooRoot",          0.4f,  5f,   2.5f,  1f),

        // -- Bamboo _02 set: wild-grove decoration variety (no growth) --
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Small_Green_02.prefab",      "treeKitsuneBambooWildSmallRoot", 0.3f,  1.5f, 0.75f, 1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Mid_Green_02.prefab",        "treeKitsuneBambooWildMidRoot",   0.35f, 3f,   1.5f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/Bamboo/Tree_Bamboo_Big_Green_02.prefab",        "treeKitsuneBambooWildBigRoot",   0.4f,  5f,   2.5f,  1f),

        // -- Black Pine: one set, 3-stage growth chain --
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Small_Green_01.prefab","treeKitsuneBlackPineSmallRoot",  0.4f,  1f,   0.5f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Mid_Green_01.prefab",  "treeKitsuneBlackPineMidRoot",    0.6f,  2.5f, 1.25f, 1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees/BlackPine/Tree_BlackPine_Big_Green_01.prefab",  "treeKitsuneBlackPineRoot",       1f,    5f,   2.5f,  1f),

        // -- Boxwood: 3 variety variants, all "Boxwood Shrub" --
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_01.prefab",       "treeKitsuneBoxwoodRoot",         0.5f,  1f,   0.5f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_02.prefab",       "treeKitsuneBoxwoodRootB",        0.5f,  1f,   0.5f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_03.prefab",       "treeKitsuneBoxwoodRootC",        0.5f,  1f,   0.5f,  1f),

        // -- Boxwood seed-stage: same trick as the painted fern. The pack has
        // no small boxwood mesh, so reuse the _01 shrub at 0.5 localScale ~ a
        // young shrub that reads as boxwood, not the vanilla oak sprout it
        // borrowed before. Collider params are pre-scaled (final world size).
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/Boxwood/Plant_Boxwood_Spring_01.prefab",       "treeKitsuneBoxwoodSmallRoot",    0.5f,  0.5f, 0.25f, 0.5f),

        // -- Painted Fern: 2 variety variants, both "Painted Fern" --
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/PaintedFern/Plant_PaintedFern_Spring_01.prefab","treeKitsunePaintedFernRoot",     0.4f,  0.6f, 0.3f,  1f),
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/PaintedFern/Plant_PaintedFern_Spring_02.prefab","treeKitsunePaintedFernRootB",    0.4f,  0.6f, 0.3f,  1f),

        // -- Painted Fern seed-stage: the FreeJapaneseGarden pack ships no
        // small fern mesh, so reuse the _01 fern at 0.5 localScale ~ a young
        // frond that clearly reads as a FERN. Before this, the fern seed
        // borrowed the vanilla oak sprout and was visually identical to the
        // boxwood seed. Collider params are pre-scaled (final world size).
        ("Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Plants/PaintedFern/Plant_PaintedFern_Spring_01.prefab","treeKitsunePaintedFernSmallRoot",0.4f,  0.3f, 0.15f, 0.5f),
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

                // Fully unpack the prefab instance so `inner` becomes plain
                // GameObjects. DestroyImmediate on a component still bound to
                // a connected prefab instance is unreliable ~ Unity treats it
                // as an override and some components (notably the FJG
                // BroccoTreeController wind script) survive into the saved
                // asset. After a complete unpack every strip below is
                // unconditional and the saved wrapper is fully self-contained.
                PrefabUtility.UnpackPrefabInstance(inner, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);

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

                // Strip ALL MonoBehaviour scripts from the inner asset.
                // FreeJapaneseGarden prefabs ship a Broccoli.Controller.
                // BroccoTreeController wind script; that DLL isn't present in
                // 7DTD, so the bundled component deserializes as a "missing
                // script" and spams NullReferenceExceptions every frame.
                // Built-in components (MeshRenderer, MeshFilter, LODGroup)
                // are NOT MonoBehaviours, so rendering + LODs survive.
                foreach (var mb in inner.GetComponentsInChildren<MonoBehaviour>(true))
                    if (mb != null) Object.DestroyImmediate(mb);

                // Belt-and-suspenders: sweep any component whose script truly
                // cannot be resolved (missing-script) on every GameObject.
                foreach (var t in inner.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.RemoveMonoBehavioursWithMissingScript(t.gameObject);

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

    // ============================================================
    // Strip wind-controller scripts from the SOURCE prefabs.
    // ============================================================
    // The FreeJapaneseGarden trees are Broccoli-generated: their LOD
    // meshes are saved as sub-assets INSIDE each source .prefab file,
    // right alongside a BroccoTreeController wind-script component.
    // OCB builds the bundle with BuildAssetBundleOptions.CompleteAssets,
    // so depending on one of those embedded meshes drags the ENTIRE
    // source prefab into the bundle ~ BroccoTreeController and all ~
    // no matter how clean the wrapper is (the wrapper only references
    // the mesh; CompleteAssets pulls the whole owning asset). 7DTD has
    // no Broccoli runtime, so every bundled controller spams
    // missing-script NullReferenceExceptions.
    //
    // The only real fix is to strip the scripts from the source
    // prefabs themselves. Run this once; it's idempotent. Wrappers do
    // NOT need rebuilding afterward (mesh GUIDs/fileIDs are untouched)
    // ~ just re-export the bundle.
    [MenuItem("Tools/Kitsune/Strip Scripts From Source Prefabs")]
    public static void StripSourceScripts()
    {
        var seen = new HashSet<string>();
        int total = 0;
        foreach (var (sourcePath, _, _, _, _, _) in Targets)
        {
            if (!seen.Add(sourcePath)) continue;

            var contents = PrefabUtility.LoadPrefabContents(sourcePath);
            if (contents == null)
            {
                Debug.LogWarning($"[KitsuneFlora] Source prefab not found: {sourcePath}");
                continue;
            }
            try
            {
                int n = 0;
                foreach (var mb in contents.GetComponentsInChildren<MonoBehaviour>(true))
                    if (mb != null) { Object.DestroyImmediate(mb); n++; }
                foreach (var t in contents.GetComponentsInChildren<Transform>(true))
                    GameObjectUtility.RemoveMonoBehavioursWithMissingScript(t.gameObject);

                if (n > 0)
                {
                    PrefabUtility.SaveAsPrefabAsset(contents, sourcePath);
                    total += n;
                    Debug.Log($"[KitsuneFlora] Stripped {n} script(s) from {sourcePath}");
                }
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(contents);
            }
        }
        AssetDatabase.SaveAssets();
        AssetDatabase.Refresh();
        Debug.Log($"[KitsuneFlora] Done. Stripped {total} MonoBehaviour(s) from source " +
                  "prefabs. Re-export the bundle ~ no re-wrap needed.");
    }
}
