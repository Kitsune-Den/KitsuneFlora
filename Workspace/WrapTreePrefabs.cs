// Editor script — drop at Assets/Editor/WrapTreePrefabs.cs
//
// Menu: Tools → Kitsune → Wrap Tree Prefabs With Unique Roots
//
// Creates NEW prefab files (KitsuneTreeWrappers/<unique>.prefab) that
// each contain a wrapper GameObject with our unique name, with the
// original Asset Store prefab dragged in as a child. The new files have
// unique names — Unity auto-syncs root GameObject name to FILE name, so
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

    private static readonly (string sourcePath, string newName, float radius, float height, float centerY)[] Targets =
    {
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_flower_roadside_1.prefab", "treeKitsuneSakuraRoot",     0.4f, 6.5f, 3.25f),
        ("Assets/RoadsideTrees/Prefabs/CherryBlossom_leaf_roadside_1.prefab",   "treeKitsuneSakuraLeafRoot", 0.4f, 6.5f, 3.25f),
        ("Assets/RoadsideTrees/Prefabs/Keyaki_L.prefab",                        "treeKitsuneKeyakiRoot",     0.6f, 11f,  5.5f),
    };

    [MenuItem("Tools/Kitsune/Wrap Tree Prefabs With Unique Roots")]
    public static void Wrap()
    {
        if (!AssetDatabase.IsValidFolder(OutDir))
            AssetDatabase.CreateFolder("Assets", "KitsuneTreeWrappers");

        foreach (var (sourcePath, newName, radius, height, centerY) in Targets)
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

                // Add BoxCollider on the wrapper root.
                var box = wrapper.AddComponent<BoxCollider>();
                box.center = new Vector3(0f, centerY, 0f);
                box.size = new Vector3(radius * 2f, height, radius * 2f);
                box.isTrigger = false;

                // Save wrapper as a brand-new prefab file with unique name.
                var outPath = $"{OutDir}/{newName}.prefab";
                PrefabUtility.SaveAsPrefabAsset(wrapper, outPath);
                Debug.Log($"[KitsuneFlora] Created wrapper prefab: {outPath}");
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
