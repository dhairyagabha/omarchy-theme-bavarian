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
    # The hero. Supplied by the repository owner; an E30 ALPINA C2 2.7 shot on
    # a panning exposure, which is why it gets the power treatment rather than
    # a straight grade. Rendered at 1440p, not 4K: the source is 1240px wide
    # and inventing three times that many pixels only produces mush.
    "alpina-e30-c2": {
        "out": "01-alpina-e30-c2.jpg",
        "size": (2560, 1440),
        "crop": None,
        # Trim the 16:9 band low in the frame: the overcast sky is the least
        # interesting part and it sits exactly where Waybar goes.
        "anchor": 0.75,
        "focus": (0.50, 0.56),
        "power": {"amount": 0.055, "inner": 0.14, "outer": 0.80},
        "sharpen": 0.6,
        "blur": 0.0,
        "target": 0.020,
        "saturation": 0.30,
        # The number plate, and the bright verge behind the front wing.
        "knockdown": [(0.566, 0.606, 0.738, 0.724, 0.72, 11.0)],
        "note": "BMW E30 ALPINA C2 2.7",
    },
    "alpina-b7-iaa-2017-frankfurt-1y7a3123": {
        "out": "08-alpina-tail-light.jpg",
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
        "out": "09-alpina-b5-touring.jpg",
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


def radial_distance(shape: tuple[int, int], focus: tuple[float, float]) -> np.ndarray:
    """Aspect-corrected distance from a normalised focal point, 0 at the focus."""
    h, w = shape
    y, x = np.meshgrid(np.linspace(0, 1, h), np.linspace(0, 1, w), indexing="ij")
    return np.sqrt(((x - focus[0]) * (w / h)) ** 2 + (y - focus[1]) ** 2)


def power_treatment(
    im: Image.Image,
    focus: tuple[float, float],
    amount: float = 0.055,
    inner: float = 0.16,
    outer: float = 0.85,
    steps: int = 14,
) -> Image.Image:
    """
    Amplify a panning shot: zoom blur everywhere except the subject.

    A press photographer panning with a moving car already produces streaked
    surroundings and a sharp car. Scaling the frame about the car and averaging
    the stack extends exactly that streak, so the effect reads as more of what
    the photograph is already doing rather than as a filter laid over it. The
    subject is held sharp by blending back through a radial mask.
    """
    w, h = im.size
    base = np.asarray(im.convert("RGB"), dtype=np.float64)

    stack = np.zeros_like(base)
    weight = 0.0
    for k in range(steps):
        scale = 1.0 + amount * (k / max(1, steps - 1))
        sw, sh = round(w * scale), round(h * scale)
        # Enlarge about the focal point, then crop back to the original frame.
        left = round((sw - w) * focus[0])
        top = round((sh - h) * focus[1])
        frame = im.resize((sw, sh), Image.LANCZOS).crop((left, top, left + w, top + h))
        # Later (more scaled) samples contribute less, which keeps the streak
        # attached to its source instead of smearing evenly.
        wk = 1.0 - 0.55 * (k / max(1, steps - 1))
        stack += np.asarray(frame.convert("RGB"), dtype=np.float64) * wk
        weight += wk
    stack /= weight

    mask = smoothstep(inner, outer, radial_distance((h, w), focus))[..., None]
    out = base * (1.0 - mask) + stack * mask
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


def soften_regions(
    im: Image.Image,
    regions: list[tuple[float, float, float, float, float, float]],
) -> Image.Image:
    """
    Blur named rectangles before grading.

    Darkening alone cannot retire a number plate: a plate is black characters
    on a retroreflective ground, so lowering the exposure scales both and the
    registration stays perfectly legible. Only blur destroys the letterforms.
    This is a real car and a real registration, so the plate gets blurred and
    then darkened, which also happens to look like a press car.
    """
    blurred_cache: dict[float, Image.Image] = {}
    out = im
    w, h = im.size
    yy, xx = np.meshgrid(np.linspace(0, 1, h), np.linspace(0, 1, w), indexing="ij")

    for x0, y0, x1, y1, _strength, radius in regions:
        if radius <= 0:
            continue
        if radius not in blurred_cache:
            blurred_cache[radius] = im.filter(ImageFilter.GaussianBlur(radius))
        fx, fy = (x1 - x0) * 0.30, (y1 - y0) * 0.30
        mask = (
            smoothstep(x0 - fx, x0 + fx, xx) * (1.0 - smoothstep(x1 - fx, x1 + fx, xx))
            * smoothstep(y0 - fy, y0 + fy, yy) * (1.0 - smoothstep(y1 - fy, y1 + fy, yy))
        )
        alpha = Image.fromarray((np.clip(mask, 0, 1) * 255).astype(np.uint8), "L")
        out = Image.composite(blurred_cache[radius], out, alpha)
    return out


def fit_16_9(
    im: Image.Image,
    crop: tuple[float, float, float, float] | None,
    size: tuple[int, int] = (W, H),
    anchor: float = 0.5,
) -> Image.Image:
    """
    Crop to 16:9 and scale to `size`.

    `anchor` picks which part survives the 16:9 trim (0 = top/left,
    1 = bottom/right). Centre is rarely right for a car photograph: the
    interesting half is usually the car and the road, not the sky above it.
    """
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((
            int(x0 * im.width), int(y0 * im.height),
            int(x1 * im.width), int(y1 * im.height),
        ))
    target = size[0] / size[1]
    if im.width / im.height > target:
        new_w = int(im.height * target)
        left = round((im.width - new_w) * anchor)
        im = im.crop((left, 0, left + new_w, im.height))
    else:
        new_h = int(im.width / target)
        top = round((im.height - new_h) * anchor)
        im = im.crop((0, top, im.width, top + new_h))
    return im.resize(size, Image.LANCZOS)


def grade(
    im: Image.Image,
    blur: float = 0.0,
    target: float = 0.050,
    saturation: float = 0.34,
    focus: tuple[float, float] = (0.5, 0.5),
    sharpen: float = 0.0,
    knockdown: list[tuple[float, float, float, float, float, float]] | None = None,
) -> Image.Image:
    if blur > 0:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    if knockdown:
        im = soften_regions(im, knockdown)
    if sharpen > 0:
        # Upscaled sources go soft. A light unsharp pass puts the edge back on
        # the subject; the periphery is blurred afterwards anyway.
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharpen * 100), threshold=3))

    w, h = im.size
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

    # 5b. Knock down anything retroreflective. A number plate is engineered to
    #     be the brightest thing in any photograph of a car, so after grading it
    #     is invariably the first thing the eye lands on — and it is a real
    #     registration. Feathered so it reads as shadow, not as a patch.
    if knockdown:
        yy, xx = np.meshgrid(np.linspace(0, 1, h), np.linspace(0, 1, w), indexing="ij")
        for x0, y0, x1, y1, strength, _radius in knockdown:
            fx, fy = (x1 - x0) * 0.35, (y1 - y0) * 0.35
            region = (
                smoothstep(x0 - fx, x0 + fx, xx) * (1.0 - smoothstep(x1 - fx, x1 + fx, xx))
                * smoothstep(y0 - fy, y0 + fy, yy) * (1.0 - smoothstep(y1 - fy, y1 + fy, yy))
            )
            img *= (1.0 - strength * region)[..., None]

    # 6. Vignette about the subject rather than the frame, so the fall-off
    #    pushes everything that is not the car into the dark.
    d = radial_distance((h, w), focus) / 1.05
    img *= (1.0 - 0.62 * smoothstep(0.22, 1.0, d))[..., None]

    # 7. Settle the strip Waybar lives on.
    yy = np.linspace(0, 1, h)[:, None]
    img *= (1.0 - 0.45 * (1.0 - smoothstep(0.0, 0.06, yy)))[..., None]

    return encode(img)


def report(path: Path) -> None:
    grey = np.asarray(Image.open(path).convert("L"), dtype=np.float64) / 255.0
    h, w = grey.shape
    top = grey[: int(h * 0.03)].mean()
    centre = grey[int(h * 0.3): int(h * 0.7), int(w * 0.25): int(w * 0.75)].mean()
    print(
        f"  {path.name:<28} {w}x{h}  mean {grey.mean():.3f}  waybar band {top:.3f}  "
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

        size = r.get("size", (W, H))
        focus = r.get("focus", (0.5, 0.5))
        im = fit_16_9(Image.open(src), r["crop"], size, r.get("anchor", 0.5))
        if r.get("power"):
            im = power_treatment(im, focus, **r["power"])

        dest = args.out / r["out"]
        grade(
            im, r["blur"], r["target"], r["saturation"],
            focus=focus, sharpen=r.get("sharpen", 0.0),
            knockdown=r.get("knockdown"),
        ).save(dest, quality=93, subsampling=0, optimize=True, progressive=True)
        report(dest)


if __name__ == "__main__":
    main()
