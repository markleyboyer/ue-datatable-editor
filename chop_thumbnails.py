"""
chop_thumbnails.py
------------------
Chops an Unreal Engine content-browser screenshot into individual
thumbnail PNGs, one per card, named after the labels provided.

Usage:
    py chop_thumbnails.py <screenshot.png> [output_dir]

Output dir defaults to a subfolder named after the screenshot file.
"""

import sys
from pathlib import Path
from PIL import Image
import numpy as np


# ── Names in reading order (left→right, top→bottom) ────────────────────────
# Edit this list to match what's in each screenshot.
NAMES = [
    "SM_Ash_Tree_NN_01a",
    "SM_Ash_Tree_NN_01b",
    "SM_Ash_Tree_NN_01c",
    "SM_Ash_Tree_NN_01d",
    "SM_Ash_Tree_NN_01e",
    "SM_Ash_Tree_NN_01f",
    "SM_Ash_Tree_NN_01g",
    "SM_Ash_Tree_NN_01h",
    "SM_Ash_Tree_NN_01i",
    "SM_Ash_Tree_NN_01j",
]

MIN_CARD_PX = 40   # ignore spans narrower than this (borders, gaps)
SEP_THRESH  = 30   # variance below this → separator column/row


def find_card_spans(var, min_card_px=MIN_CARD_PX, thresh=SEP_THRESH):
    """Return list of (start, end) pixel ranges that are card content."""
    in_sep = True
    spans = []
    start = 0
    for i, v in enumerate(var):
        if in_sep and v >= thresh:
            in_sep = False
            start = i
        elif not in_sep and v < thresh:
            in_sep = True
            if i - start >= min_card_px:
                spans.append((start, i))
    if not in_sep and len(var) - start >= min_card_px:
        spans.append((start, len(var)))
    return spans


def chop(screenshot_path: str, output_dir: str | None = None, names=NAMES):
    src = Path(screenshot_path)
    if not src.exists():
        sys.exit(f"File not found: {src}")

    out = Path(output_dir) if output_dir else src.parent / src.stem
    out.mkdir(parents=True, exist_ok=True)

    img  = Image.open(src).convert("RGBA")
    arr  = np.array(img)[:, :, :3].astype(float)

    col_var = arr.var(axis=0).mean(axis=1)   # variance per x-column
    row_var = arr.var(axis=1).mean(axis=1)   # variance per y-row

    xcards = find_card_spans(col_var)
    ycards = find_card_spans(row_var)

    print(f"Image: {img.width}×{img.height}")
    print(f"Detected {len(xcards)} column(s) × {len(ycards)} row(s) "
          f"= {len(xcards)*len(ycards)} card(s)")

    saved = 0
    pos   = 0   # grid position index (advances for every slot, including skips)
    for (y0, y1) in ycards:
        for (x0, x1) in xcards:
            if pos >= len(names):
                break
            name = names[pos]
            pos += 1

            if name is None:   # None in the names list = skip this grid slot
                continue

            card = img.crop((x0, y0, x1, y1))

            # Auto-detect where the text-label strip begins:
            # Scan top-down from the lower third; label rows are bright (>80).
            card_arr   = np.array(card)[:, :, :3].astype(float)
            row_bright = card_arr.mean(axis=(1, 2))
            label_start = card.height
            for ry in range(card.height // 3, card.height):
                if row_bright[ry] > 80:
                    label_start = ry
                    break
            preview = card.crop((0, 0, card.width, label_start))

            out_path = out / f"{name}.png"
            preview.save(out_path, optimize=True)
            print(f"  {name}.png  ({preview.width}×{preview.height}px)")
            saved += 1

    print(f"\nDone — {saved} thumbnail(s) written to:\n  {out}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    chop(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
