#!/usr/bin/env python3
"""
Score candidate photographs on how well they would work as a dark wallpaper.

Most car photography on Commons is a show floor, a grass field or a dealer
forecourt. Those share measurable properties that make them bad backgrounds,
and it is much cheaper to reject them arithmetically than by eye:

  blowout   blown sky, white studio floor, bright spotlights — the thing most
            likely to end up sitting behind Waybar
  green     grass and trees, the signature of a car-meet field shot
  skylight  a bright top third, which is exactly where the UI lives
  clutter   busy edges around the frame border: crowds, railings, other cars
  colour    high overall saturation, which fights a palette this specific
  darkness  low mean luminance, which is what we actually want

The score is a weighted sum; it ranks, it does not decide. Run it, then look
at the contact sheet it writes and pick with your eyes.

Run:  python3 bin/rank-photos.py [--top 24]
"""

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PROOFS = ROOT / "backgrounds" / ".proofs"
SHEET = PROOFS / "ranked.png"

FONT = Path("/mnt/skills/examples/canvas-design/canvas-fonts/JetBrainsMono-Regular.ttf")


def measure(path: Path) -> dict | None:
    try:
        im = Image.open(path).convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    a = np.asarray(im, dtype=np.float64) / 255.0
    if a.size == 0:
        return None

    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)

    h, w = luma.shape
    top = luma[: h // 3]

    # Grass: green clearly dominant over both other channels, and not dark.
    green = float(np.mean((g > r * 1.12) & (g > b * 1.12) & (luma > 0.12)))

    # Clutter measured only around the border. The subject is normally central
    # and is supposed to have edges; crowds and railings at the margin are what
    # actually ruin a background.
    gy = np.abs(np.diff(luma, axis=0))[:, :-1]
    gx = np.abs(np.diff(luma, axis=1))[:-1, :]
    edges = np.hypot(gx, gy)
    mask = np.ones_like(edges, dtype=bool)
    mask[int(h * 0.18): int(h * 0.82), int(w * 0.18): int(w * 0.82)] = False

    return {
        "darkness": float(1.0 - luma.mean()),
        "blowout": float(np.mean(luma > 0.85)),
        "green": green,
        "skylight": float(np.mean(top > 0.72)),
        "clutter": float(edges[mask].mean()),
        "colour": float(sat.mean()),
    }


def score(m: dict) -> float:
    return (
        2.2 * m["darkness"]
        - 3.2 * m["blowout"]
        - 3.6 * m["green"]
        - 2.0 * m["skylight"]
        - 3.0 * m["clutter"]
        - 0.9 * m["colour"]
    )


def contact_sheet(rows: list[dict], top: int) -> None:
    cols = 4
    tw, th, pad, cap = 440, 248, 8, 26
    picks = rows[:top]
    n = len(picks)
    grid_rows = math.ceil(n / cols)
    sheet = Image.new(
        "RGB",
        (cols * (tw + pad) + pad, grid_rows * (th + cap + pad) + pad),
        (8, 10, 14),
    )
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(str(FONT), 13) if FONT.exists() else ImageFont.load_default()

    for i, row in enumerate(picks):
        im = Image.open(PROOFS / f"{row['stem']}.jpg").convert("RGB")
        im.thumbnail((tw, th))
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + cap + pad)
        sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        d.text(
            (x + 2, y + th + 4),
            f"{i:>2} {row['stem'][:40]}  {row['score']:+.2f}",
            font=font, fill=(200, 210, 222),
        )

    sheet.save(SHEET)
    print(f"\ncontact sheet -> {SHEET}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=24)
    args = ap.parse_args()

    if not any(PROOFS.glob("*.jpg")):
        raise SystemExit("No proofs. Run: python3 bin/fetch-wallpapers.py proofs")

    # Ranking only needs pixels. The manifest carries licence and author, which
    # matter when a photograph is actually kept, not when it is being scored —
    # so a missing or partial manifest degrades rather than stopping the run.
    manifest = PROOFS / "manifest.json"
    index = {}
    if manifest.exists():
        index = {i["stem"]: i for i in json.loads(manifest.read_text())}
    else:
        print("note: no manifest yet — licence column will be unknown\n")

    rows = []
    for path in sorted(PROOFS.glob("*.jpg")):
        m = measure(path)
        if not m:
            continue
        item = index.get(path.stem, {})
        rows.append({"stem": path.stem, "score": score(m), "licence": item.get("licence", "?"), **m})

    rows.sort(key=lambda r: -r["score"])

    print(f"{len(rows)} candidates scored\n")
    print(f"{'#':>3} {'stem':<44} {'score':>6} {'dark':>5} {'blow':>5} "
          f"{'green':>5} {'sky':>5} {'clut':>5} {'col':>5}")
    for i, r in enumerate(rows[: args.top]):
        print(f"{i:>3} {r['stem'][:44]:<44} {r['score']:+6.2f} {r['darkness']:5.2f} "
              f"{r['blowout']:5.3f} {r['green']:5.2f} {r['skylight']:5.2f} "
              f"{r['clutter']:5.3f} {r['colour']:5.2f}")

    contact_sheet(rows, args.top)
    print("\nThen: python3 bin/fetch-wallpapers.py full <stem> [<stem> ...]")


if __name__ == "__main__":
    main()
