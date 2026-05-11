"""
KitsuneFlora ~ cross-reference validation tests.

Catches the failure modes that don't show up until you load the world:
- Block ID typos (block X references block Y that doesn't exist)
- Missing icon PNG for a block's CustomIcon
- Missing localization entries
- Stale blocknames in biomes.xml / loot.xml / traders.xml after rename

Run from the repo root:
    pytest -v tests/

Or just:
    python -m pytest -v
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

# ---------- paths --------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_ROOT = REPO_ROOT / "KitsuneFlora"
CONFIG_DIR = MOD_ROOT / "Config"
ICONS_DIR = MOD_ROOT / "UIAtlases" / "ItemIconAtlas"

BLOCKS_XML = CONFIG_DIR / "blocks.xml"
BIOMES_XML = CONFIG_DIR / "biomes.xml"
LOOT_XML = CONFIG_DIR / "loot.xml"
TRADERS_XML = CONFIG_DIR / "traders.xml"
LOCALIZATION_TXT = CONFIG_DIR / "Localization.txt"

# Block defs we define but that aren't player-facing (templates that other
# blocks extend). They don't need icons, localization, or biome entries.
TEMPLATE_BLOCKS = {"treeKitsuneMaster"}


# ---------- fixtures -----------------------------------------------------

@pytest.fixture(scope="session")
def blocks_root() -> ET.Element:
    return ET.parse(BLOCKS_XML).getroot()


@pytest.fixture(scope="session")
def block_names(blocks_root: ET.Element) -> set[str]:
    """All <block name="..."> values defined in this mod."""
    return {b.get("name") for b in blocks_root.iter("block") if b.get("name")}


@pytest.fixture(scope="session")
def concrete_blocks(block_names: set[str]) -> set[str]:
    """Blocks that actually ship as player-facing (excludes XML templates)."""
    return block_names - TEMPLATE_BLOCKS


@pytest.fixture(scope="session")
def localization_keys() -> set[str]:
    """First column of Localization.txt ~ every key defined."""
    keys: set[str] = set()
    with LOCALIZATION_TXT.open(encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if row and row[0]:
                keys.add(row[0])
    return keys


# ---------- parse helpers ------------------------------------------------

def block_props(block: ET.Element) -> dict[str, str]:
    """{name: value} of <property name=... value=.../> on a <block>."""
    out: dict[str, str] = {}
    for p in block.findall("property"):
        n = p.get("name")
        v = p.get("value")
        if n is not None and v is not None:
            out[n] = v
    return out


def blocknames_referenced_in(xml_path: Path) -> set[str]:
    """Pull every blockname=... attribute and <item name=.../> child from an XML file."""
    root = ET.parse(xml_path).getroot()
    refs: set[str] = set()
    for el in root.iter():
        bn = el.get("blockname")
        if bn:
            refs.add(bn)
        if el.tag == "item":
            n = el.get("name")
            if n:
                refs.add(n)
    return refs


# ---------- the actual tests ---------------------------------------------

def test_blocks_xml_parses():
    """blocks.xml is valid XML."""
    ET.parse(BLOCKS_XML)  # raises on parse error


@pytest.mark.parametrize("xml_path", [BIOMES_XML, LOOT_XML, TRADERS_XML])
def test_modlet_xml_parses(xml_path: Path):
    """biomes / loot / traders modlet XMLs are valid XML."""
    ET.parse(xml_path)


def test_every_destroy_drop_references_existing_block(blocks_root, block_names):
    """A mature tree drops a seed on Destroy ~ that seed must exist."""
    missing: list[tuple[str, str]] = []
    for block in blocks_root.iter("block"):
        owner = block.get("name", "?")
        for drop in block.findall("drop"):
            if drop.get("event") == "Destroy":
                target = drop.get("name", "")
                # resourceWood, resource*, etc. are vanilla ~ only check
                # tree* / treePlanted* refs which should be ours.
                if target.startswith(("treeKitsune", "treePlantedKitsune")):
                    if target not in block_names:
                        missing.append((owner, target))
    assert not missing, (
        "These Destroy drops point at non-existent blocks:\n"
        + "\n".join(f"  {o} drops {t}" for o, t in missing)
    )


def test_every_plantgrowing_next_references_existing_block(blocks_root, block_names):
    """A seed's PlantGrowing.Next must be a real block."""
    missing: list[tuple[str, str]] = []
    for block in blocks_root.iter("block"):
        owner = block.get("name", "?")
        props = block_props(block)
        target = props.get("PlantGrowing.Next")
        if target and target not in block_names:
            missing.append((owner, target))
    assert not missing, (
        "These PlantGrowing.Next values point at non-existent blocks:\n"
        + "\n".join(f"  {o} grows into {t}" for o, t in missing)
    )


def test_every_custom_icon_has_png(blocks_root):
    """Every CustomIcon value must have a matching PNG in ItemIconAtlas."""
    missing: list[tuple[str, str]] = []
    for block in blocks_root.iter("block"):
        owner = block.get("name", "?")
        props = block_props(block)
        icon = props.get("CustomIcon")
        if icon:
            png = ICONS_DIR / f"{icon}.png"
            if not png.exists():
                missing.append((owner, icon))
    assert not missing, (
        "These CustomIcon values have no matching PNG in ItemIconAtlas/:\n"
        + "\n".join(f"  {o} → {i}.png" for o, i in missing)
    )


def test_no_orphan_icons_in_atlas(concrete_blocks, blocks_root):
    """ItemIconAtlas should only contain icons referenced by a block."""
    # Build the set of icons that are referenced ~ CustomIcon values for
    # mature blocks, plus the block-name-matching PNG for seed blocks (since
    # they inherit CustomIcon via `param1` and the file is named after the
    # block itself).
    referenced: set[str] = set()
    for block in blocks_root.iter("block"):
        name = block.get("name", "")
        if name in TEMPLATE_BLOCKS:
            continue
        props = block_props(block)
        icon = props.get("CustomIcon", name)  # seeds fall back to block name
        referenced.add(f"{icon}.png")
        # seeds inherit param1="CustomIcon" pattern ~ the icon file is also
        # named after the block itself
        if name.startswith("treePlanted"):
            referenced.add(f"{name}.png")

    on_disk = {p.name for p in ICONS_DIR.glob("*.png")}
    orphans = on_disk - referenced
    assert not orphans, (
        "ItemIconAtlas/ contains PNGs not referenced by any block "
        "(move to Workspace/IconSources/ instead):\n"
        + "\n".join(f"  {f}" for f in sorted(orphans))
    )


@pytest.mark.parametrize("suffix", ["", "Desc"])
def test_every_concrete_block_has_localization(concrete_blocks, localization_keys, suffix):
    """Every concrete block needs a name entry AND a Desc entry in Localization.txt."""
    missing = [b + suffix for b in concrete_blocks if (b + suffix) not in localization_keys]
    label = "name" if not suffix else "Desc"
    assert not missing, (
        f"These blocks have no Localization.txt {label} entry:\n"
        + "\n".join(f"  {k}" for k in sorted(missing))
    )


def test_biomes_xml_blocknames_exist(block_names):
    """Every blockname referenced in biomes.xml must exist in blocks.xml."""
    refs = blocknames_referenced_in(BIOMES_XML)
    ours = {r for r in refs if r.startswith("treeKitsune")}
    missing = ours - block_names
    assert not missing, (
        "biomes.xml references blocks that don't exist:\n"
        + "\n".join(f"  {b}" for b in sorted(missing))
    )


def test_loot_xml_blocknames_exist(block_names):
    """Every blockname referenced in loot.xml must exist in blocks.xml."""
    refs = blocknames_referenced_in(LOOT_XML)
    ours = {r for r in refs if r.startswith(("treeKitsune", "treePlantedKitsune"))}
    missing = ours - block_names
    assert not missing, (
        "loot.xml references blocks that don't exist:\n"
        + "\n".join(f"  {b}" for b in sorted(missing))
    )


def test_traders_xml_blocknames_exist(block_names):
    """Every blockname referenced in traders.xml must exist in blocks.xml."""
    refs = blocknames_referenced_in(TRADERS_XML)
    ours = {r for r in refs if r.startswith(("treeKitsune", "treePlantedKitsune"))}
    missing = ours - block_names
    assert not missing, (
        "traders.xml references blocks that don't exist:\n"
        + "\n".join(f"  {b}" for b in sorted(missing))
    )


def test_modinfo_version_matches_readme():
    """ModInfo Version and README status line should agree on version."""
    modinfo = (MOD_ROOT / "ModInfo.xml").read_text(encoding="utf-8")
    version_match = re.search(r'<Version value="([\d.]+)"', modinfo)
    assert version_match, "ModInfo.xml has no <Version value=...>"
    modinfo_version = version_match.group(1)

    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    # Status line: "🌸 v0.3 WORKING ~ 2026-05-11."
    readme_match = re.search(r"v([\d.]+)\s+WORKING", readme)
    assert readme_match, "README.md has no 'vX.Y WORKING' status line"
    readme_version = readme_match.group(1)

    # ModInfo is 3-part (0.3.0), README is 2-part shorthand (0.3) ~ compare prefixes.
    assert modinfo_version.startswith(readme_version), (
        f"ModInfo version {modinfo_version} doesn't match README status {readme_version}"
    )
