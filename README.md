# KitsuneFlora

Standalone 7DTD V2.6 mod adding Japanese-themed trees: cherry blossom (sakura), sakura with leaves, and keyaki (Japanese zelkova).

## Status

**🌸 WORKING 2026-05-10.** Trees are solid, chop-able, drop wood + sapling, plant via sapling block. First documented V2.6 working pattern for custom-mesh blocks via mod bundle.

## Layout

```
KitsuneFlora/
├── ModInfo.xml
├── Config/
│   ├── blocks.xml          6 block defs: 3 mature trees + 3 saplings
│   └── Localization.txt    English display names
├── Resources/
│   └── Bundles/
│       └── KitsuneFlora.unity3d   ← gitignored, rebuilt from Unity
└── UIAtlases/
    └── ItemIconAtlas/      Vanilla oak placeholder icons (replace later)
```

Asset source: [Roadside Trees](https://assetstore.unity.com) Unity Asset Store package, imported into the shared `RedFoxAnimated` Unity project.

## Block roster

| Block | Sapling | Bundle ref |
|---|---|---|
| `treeKitsuneSakura` | `treePlantedKitsuneSakura1m` | `?CherryBlossom_flower_roadside_1.prefab` |
| `treeKitsuneSakuraLeaf` | `treePlantedKitsuneSakuraLeaf1m` | `?CherryBlossom_leaf_roadside_1.prefab` |
| `treeKitsuneKeyaki` | `treePlantedKitsuneKeyaki1m` | `?Keyaki_L.prefab` |

## The bug nobody else online has documented

Asset Store FBX-derived prefabs (Roadside Trees, etc.) share their **root GameObject name** with the FBX file. When OCB UnityAssetExporter bundles the prefab, the FBX's auto-generated GameObject of the same name comes along as a dependency. The bundle ends up with **TWO root GameObjects with the same name**:

- The FBX's auto-GameObject — Transform only, no LODGroup, no collider (registered first)
- The actual prefab — Transform + LODGroup + BoxCollider (the real one)

When 7DTD's bundle loader resolves `#@modfolder:Bundle.unity3d?PrefabName`, it picks the FIRST GameObject with that name — the empty FBX wrapper. No collider → walk-through, no LODGroup → mesh missing in some draws.

## The fix

Wrap each prefab in a **NEW outer GameObject** with a unique filename (e.g. `treeKitsuneSakuraRoot.prefab`) that doesn't collide with the FBX's auto-name. The new outer becomes the bundle root for that asset. Procedure:

1. Editor script (`Workspace/WrapTreePrefabs.cs`) creates wrapper prefabs in `Assets/KitsuneTreeWrappers/` containing the original prefab as a child + a new `BoxCollider` on the wrapper root.
2. Update the OCB Bundle asset's Objects list to point at the new wrapper prefabs.
3. Update `blocks.xml` Model references to use the wrapper's unique name (`?treeKitsuneSakuraRoot` etc.).
4. Re-export bundle.

Verification with UnityPy: bundle's top-level GameObjects should include `treeKitsuneSakuraRoot` (Transform + BoxCollider) and `treeKitsuneSakuraLeafRoot`/`treeKitsuneKeyakiRoot` similarly. The old FBX-named GameObjects may still be present but are no longer referenced by XML.

## Other XML lessons learned along the way (all kept in current config)

- Two-step XML pattern (template extending `treeMaster` with vanilla path → tree extending template with mod-bundle path) is the correct V2.6 inheritance flow per War3zuk FarmLife (Nexus 2108).
- `Material="MtreeWoodLarge"` explicit override.
- No re-stated `Path` or `Collide` (let inheritance handle).
- Bundle-side BoxCollider on the wrapper root.
- No `.prefab` extension on bundle asset names (`?treeKitsuneSakuraRoot` not `?treeKitsuneSakuraRoot.prefab`).

## Author / License

Author: Ada (adainthelab@gmail.com)
Repo: standalone, may eventually be folded into KitsuneCompanion.
