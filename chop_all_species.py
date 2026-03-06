"""Run chop_thumbnails for every species screenshot."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from chop_thumbnails import chop

BASE = Path(__file__).parent / "SpeciesScreenShots"

SPECIES = {
    "Beech": {
        "png": BASE / "Beech.png",
        "out": BASE / "Beech",
        "names": [
            "SM_European_Beech_NN_01a", "SM_European_Beech_NN_01b",
            "SM_European_Beech_NN_01c", "SM_European_Beech_NN_01d",
            "SM_European_Beech_NN_01e", "SM_European_Beech_NN_01f",
            "SM_European_Beech_NN_01g", "SM_European_Beech_NN_01h",
            "SM_European_Beech_NN_01i", "SM_European_Beech_NN_01j",
            "SM_European_Beech_NN_01k", "SM_European_Beech_NN_01l",
            "SM_European_Beech_NN_01m", "SM_European_Beech_NN_01n",
        ],
    },
    "DeadTrees": {
        "png": BASE / "DeadTrees.png",
        "out": BASE / "DeadTrees",
        "names": [
            "SM_Dead_Tree_NN_72a", "SM_Dead_Tree_NN_72b",
            "SM_Dead_Tree_NN_72c", "SM_Dead_Tree_NN_72d",
            "SM_Dead_Tree_NN_72e", "SM_Dead_Tree_NN_72f",
            "SM_Dead_Tree_NN_72g", "SM_Dead_Tree_NN_72h",
            "SM_Dead_Tree_NN_72i", "SM_Dead_Tree_NN_72j",
            "SM_Dead_Tree_NN_72k", "SM_Dead_Tree_NN_72l",
        ],
    },
    "Oaks": {
        "png": BASE / "Oaks.png",
        "out": BASE / "Oaks",
        "names": [
            "SM_Tree_Set_NN_03a", "SM_Tree_Set_NN_03b",
            "SM_Tree_Set_NN_03c", "SM_Tree_Set_NN_03d",
            "SM_Tree_Set_NN_03e", "SM_Tree_Set_NN_03f",
            "SM_Tree_Set_NN_03g", "SM_Tree_Set_NN_03h",
            "SM_Tree_Set_NN_03i", "SM_Tree_Set_NN_03j",
            "SM_Tree_Set_NN_03k",
        ],
    },
    "Spruce": {
        "png": BASE / "Spruce.png",
        "out": BASE / "Spruce",
        # Row 1: first 4 slots are InterchangeSceneImportAsset — skip them
        "names": [
            None, None, None, None,
            "SM_Spruce_Tree_NN_01a",
            "SM_Spruce_Tree_NN_01b", "SM_Spruce_Tree_NN_01c",
            "SM_Spruce_Tree_NN_01d", "SM_Spruce_Tree_NN_01e",
            "SM_Spruce_Tree_NN_01f",
            "SM_Spruce_Tree_NN_01g", "SM_Spruce_Tree_NN_01h",
            "SM_Spruce_Tree_NN_01i", "SM_Spruce_Tree_NN_01j",
            "SM_Spruce_Tree_NN_01k",
            "Spruce_tree_001_B", "Spruce_tree_001_C",
            "Spruce_tree_001_D", "Spruce_tree_001_E",
            "Spruce_tree_001_F",
        ],
    },
}

for species, cfg in SPECIES.items():
    print(f"\n{'='*50}")
    print(f"  {species}")
    print(f"{'='*50}")
    chop(str(cfg["png"]), str(cfg["out"]), names=cfg["names"])
