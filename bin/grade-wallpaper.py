#!/usr/bin/env python3
"""
Turn a photograph into a Bavarian wallpaper.

Car photography is lit to sell cars: bright, saturated, high contrast, subject
dead centre. Those are exactly the properties that make a desktop background
fight the UI sitting on top of it. This applies the theme's house grade —
crop, desaturate, cool the balance, lift the shadows toward ALPINA blue, pull
the contrast back, darken, vignette — and settles the top edge so Waybar
always has a quiet strip to sit on.

Use it on your own licensed ALPINA photography:

    python3 bin/grade-wallpaper.py photo.jpg --out backgrounds/
    python3 bin/grade-wallpaper.py photo.jpg --crop 0.1,0.2,0.9,0.95 --blur 3

--crop takes normalised x0,y0,x1,y1 and is applied before the 16:9 fit, so you
can steer which part of the frame survives. --blur is there for busy
backgrounds; a value of 2-4 pushes clutter behind the UI without turning the
subject to mush.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette as p  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

W, H = 3840, 2160
RNG = np.random.default_rng(1965)

# Recipes for the photographs this theme ships, so the results are
# reproducible rather than hand-tuned once and forgotten.
RECIPES = {
    "alpina-b7-iaa-2017-frankfurt-1y7a3123": {
        "out": "07-alpina-tail-light.jpg",
        # Weighted to the bodywork rather than the lamp. Centred on the light
        # the frame is dominated by red, which contradicts the whole point of
        # the palette: red is the rarest colour and it means something. Here
        # it is a sliver along one edge of a dark metallic panel.
        "crop": (0.34, 0.03, 1.00, 0.80),
        "blur": 0.0,
        "target": 0.016,
        "saturation": 0.26,
        "note": "ALPINA B7 tail light, IAA 2017",
    },
    "alpina-gims-2018-le-grand-saconnex-1x7a1256": {
        "out": "08-alpina-b5-touring.jpg",
        # Crops out the orange car on the left and most of the show-stand
        # crowd along the top; what is left is the car and the dark stand.
        "crop": (0.14, 0.06, 0.845, 0.955),
        "blur": 2.6,
        "target": 0.013,
        "saturation": 0.28,
        "note": "ALPINA B5 Bi-Turbo Touring, Geneva 2018",
    },
}


def to_linear(a: np.ndarray) -> np.ndarray:
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def encode(img: np.ndarray) -> Image.Image:
    x = np.clip(img, 0.0, 1.0)
    srgb = np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)
    noise = (RNG.random(srgb.shape) - RNG.random(srgb.shape)) * (0.75 / 255.0)
    return Image.fromarray(
        np.clip((srgb + noise) * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB"
    )


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def fit_16_9(im: Image.Image, crop: tuple[float, float, float, float] | None) -> Image.Image:
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((
            int(x0 * im.width), int(y0 * im.height),
            int(x1 * im.width), int(y1 * im.height),
        ))
    # Centre-crop whatever is left to 16:9, then scale to 4K.
    target = W / H
    if im.width / im.height > target:
        new_w = int(im.height * target)
        left = (im.width - new_w) // 2
        im = im.crop((left, 0, left + new_w, im.height))
    else:
        new_h = int(im.width / target)
        top = (im.height - new_h) // 2
        im = im.crop((0, top, im.width, top + new_h))
    return im.resize((W, H), Image.LANCZOS)


def grade(
    im: Image.Image,
    blur: float = 0.0,
    target: float = 0.050,
    saturation: float = 0.34,
) -> Image.Image:
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))

    img = to_linear(np.asarray(im.convert("RGB"), dtype=np.float64) / 255.0)
    luma = (img * np.array([0.2126, 0.7152, 0.0722])).sum(axis=2, keepdims=True)

    # 1. Desaturate hard. Whatever colour survives should be the car's, not
    #    the forecourt's, and heavy desaturation is what stops a photograph
    #    from arguing with a palette this specific.
    img = luma + (img - luma) * saturation

    # 2. Cool the balance. Warm streetlight and daylight both read as cheap
    #    against carbon; pulling red down and blue up moves the whole frame
    #    toward the theme's ground.
    img *= np.array([0.86, 0.96, 1.20])

    # 3. Lift the shadows toward deep ALPINA blue, weighted to the darkest
    #    parts, so black areas become blue-black rather than dead black.
    shadow = (1.0 - np.clip(luma / 0.18, 0.0, 1.0)) ** 2
    img += shadow * to_linear(np.array(p.rgb(p.ALPINA)) / 255.0)[None, None, :] * 0.18

    # 4. Pull contrast back around the midpoint. A background should not have
    #    the punch of a photograph — but overdoing this together with the
    #    shadow lift turns the frame milky, which looks cheap rather than calm.
    pivot = img.mean()
    img = pivot + (img - pivot) * 0.90

    # 5. Set the exposure by measurement, not by eye.
    mean = img.mean()
    if mean > 0:
        img *= target / mean

    # 6. Vignette, then settle the strip Waybar lives on.
    x, y = np.meshgrid(np.linspace(0, 1, W), np.linspace(0, 1, H))
    d = np.sqrt(((x - 0.5) * (W / H)) ** 2 + (y - 0.5) ** 2) / 1.10
    img *= (1.0 - 0.58 * smoothstep(0.25, 1.0, d))[..., None]
    img *= (1.0 - 0.45 * (1.0 - smoothstep(0.0, 0.06, y)))[..., None]

    return encode(img)


def report(path: Path) -> None:
    grey = np.asarray(Image.open(path).convert("L"), dtype=np.float64) / 255.0
    top = grey[: int(H * 0.03)].mean()
    centre = grey[int(H * 0.3): int(H * 0.7), int(W * 0.25): int(W * 0.75)].mean()
    print(
        f"  {path.name:<28} mean {grey.mean():.3f}  waybar band {top:.3f}  "
        f"walker area {centre:.3f}  ({path.stat().st_size // 1024} KB)"
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", type=Path, help="images to grade")
    ap.add_argument("--out", type=Path, default=root / "backgrounds")
    ap.add_argument("--crop", help="normalised x0,y0,x1,y1 applied before the 16:9 fit")
    ap.add_argument("--blur", type=float, default=0.0)
    ap.add_argument("--target", type=float, default=0.050, help="mean linear luminance")
    ap.add_argument("--saturation", type=float, default=0.34)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    if args.inputs:
        crop = tuple(float(v) for v in args.crop.split(",")) if args.crop else None
        for src in args.inputs:
            im = fit_16_9(Image.open(src), crop)
            dest = args.out / f"{src.stem}.jpg"
            grade(im, args.blur, args.target, args.saturation).save(
                dest, quality=93, subsampling=0, optimize=True, progressive=True
            )
            report(dest)
        return

    # No arguments: rebuild the photographs this theme ships.
    raw = root / "backgrounds" / ".raw"
    if not raw.exists():
        print("No .raw directory. Run bin/fetch-wallpapers.py first.", file=sys.stderr)
        sys.exit(1)

    print("Grading shipped photographs\n")
    for stem, r in RECIPES.items():
        src = raw / f"{stem}.jpg"
        if not src.exists():
            print(f"  missing {src.name} — skipped", file=sys.stderr)
            continue
        im = fit_16_9(Image.open(src), r["crop"])
        dest = args.out / r["out"]
        grade(im, r["blur"], r["target"], r["saturation"]).save(
            dest, quality=93, subsampling=0, optimize=True, progressive=True
        )
        report(dest)


if __name__ == "__main__":
    main()
