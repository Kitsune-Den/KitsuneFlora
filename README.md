# KitsuneFlora

Standalone 7DTD V2.6 mod adding Japanese-themed trees: cherry blossom (sakura), sakura with leaves, and keyaki (Japanese zelkova).

## Status

**WIP — paused 2026-05-10.** Bundle pipeline + XML scaffolding complete; trees render correctly in-world but currently fail terrain registration (walk-through, un-hittable). Engine-side issue, see "Next session" below.

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

## Known issue: trees aren't solid in V2.6

Symptom: trees render fine but the player walks through them and can't chop them. Log shows `[MultiBlockManager][Alignment] SetTerrainAlignmentDirty failed; no terrain-aligned block has been registered`.

What we tried (all failed):
- XML `Path="solid"` + `Collide="movement,melee,..."` (explicit + inherited)
- `Material="MtreeWoodLarge"` override
- Bundle-side colliders (CapsuleCollider, BoxCollider, on root and on `CollisionObject0` child to mirror vanilla pattern)
- `Shape="ModelEntity"` override (vanilla painting block shape)
- `extends="treeMaster"` (and not re-stating Path/Collide so inheritance flows clean)

Reference mod **Gyancher Trees (Nexus 966)** — 2020-era custom-tree mod that worked in V1.x — doesn't even register in V2.6's gimme list. Suggests V2.6 changed something fundamental about block registration for mod-side bundle prefabs.

## Next session attack plan

1. Decompile `Assembly-CSharp.dll` with ILSpy/dnSpy. Search for:
   - `BlockModelTree` — class likely registered to handle ModelTree blocks
   - `MultiBlockManager.SetTerrainAlignmentDirty` — emits the warning we're seeing
   - `TerrainAlignedBlocks` registration code
2. Find what `#@modfolder:` bundle paths require to register as terrain-aligned that vanilla `@:` paths don't need.
3. Likely outcomes:
   - Find a specific XML property we missed (e.g. `ModelType`, custom Class)
   - Need a Harmony patch in a tiny DLL that registers our blocks with the terrain-alignment system
   - Confirm V2.6 doesn't support custom-mesh block bundles at all (and switch strategy — maybe use entity-class with a placement script like vehicles do)

## Author / License

Author: Ada (adainthelab@gmail.com)
Repo: standalone, may eventually be folded into KitsuneCompanion.
