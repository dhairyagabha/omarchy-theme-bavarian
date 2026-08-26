#!/usr/bin/env python3
"""
Generate the Bavarian abstract wallpaper set.

Six 4K backgrounds built from the theme palette: carbon weave, ambient cabin
light, a long-exposure night road, an instrument arc, a Bavarian ridge line,
and dark machined aluminium.

Two rules govern every composition:

  1. The wallpaper is background. Mean luminance stays low and local contrast
     stays gentle, so text and window borders on top of it always win.
  2. Nothing bright sits where the UI lives. Highlights are pushed to the
     lower and outer thirds, away from Waybar along the top edge and Walker in
     the centre of the screen.

Everything is composed in linear light and dithered before it is quantised to
8-bit. On near-black images that dither is the difference between smooth
gradients and visible banding.

Run:  python3 bin/make-backgrounds.py
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette as p  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "backgrounds"

W, H = 3840, 2160
RNG = np.random.default_rng(1965)  # the year ALPINA started building BMWs


# ---------------------------------------------------------------------------
# Colour helpers — everything is mixed in linear light, never in sRGB
# ---------------------------------------------------------------------------
def to_linear(hex_colour: str) -> np.ndarray:
    srgb = np.array(p.rgb(hex_colour), dtype=np.float64) / 255.0
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def encode(rgb_linear: np.ndarray) -> Image.Image:
    """Linear float -> dithered 8-bit sRGB."""
    x = np.clip(rgb_linear, 0.0, 1.0)
    srgb = np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)
    # Triangular dither at just under one 8-bit step. Without this, a slow
    # gradient across near-black posterises into visible bands.
    noise = (RNG.random(srgb.shape) - RNG.random(srgb.shape)) * (0.75 / 255.0)
    return Image.fromarray(
        np.clip((srgb + noise) * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB"
    )


def grid() -> tuple[np.ndarray, np.ndarray]:
    """Normalised coordinates; x in [0,1], y in [0,1]."""
    return np.meshgrid(np.linspace(0, 1, W), np.linspace(0, 1, H))


def field(colour: str, amount: np.ndarray) -> np.ndarray:
    """Multiply a colour by a scalar field -> an (H, W, 3) linear image."""
    return amount[..., None] * to_linear(colour)[None, None, :]


def smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def radial(cx: float, cy: float, radius: float, power: float = 2.0) -> np.ndarray:
    """A soft round falloff centred on (cx, cy) in normalised coordinates."""
    x, y = grid()
    # Correct for aspect so circles stay circular on a 16:9 canvas.
    d = np.sqrt(((x - cx) * (W / H)) ** 2 + (y - cy) ** 2)
    return np.clip(1.0 - d / radius, 0.0, 1.0) ** power


def vignette(strength: float = 0.55, radius: float = 1.15) -> np.ndarray:
    x, y = grid()
    d = np.sqrt(((x - 0.5) * (W / H)) ** 2 + (y - 0.5) ** 2) / radius
    return 1.0 - strength * smoothstep(0.25, 1.0, d)


def value_noise(cells_x: int, cells_y: int, octaves: int = 4) -> np.ndarray:
    """Cheap fractal value noise, bilinearly upsampled. Range roughly [0,1]."""
    total = np.zeros((H, W))
    amplitude, weight = 1.0, 0.0
    for octave in range(octaves):
        cx, cy = cells_x * 2**octave, cells_y * 2**octave
        coarse = RNG.random((cy + 1, cx + 1))
        layer = np.array(
            Image.fromarray((coarse * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
        ) / 255.0
        total += layer * amplitude
        weight += amplitude
        amplitude *= 0.5
    return total / weight


def ui_safe(img: np.ndarray) -> np.ndarray:
    """
    Pull the top edge down so Waybar always sits on a settled, dark ground.

    Waybar is translucent and only 26px tall; a bright or busy strip behind it
    is the single fastest way to make a desktop look cheap.
    """
    _, y = grid()
    band = 1.0 - 0.45 * (1.0 - smoothstep(0.0, 0.055, y))
    return img * band[..., None]


def finish(img: np.ndarray, name: str, ceiling: float = 0.16) -> None:
    """Apply the shared house treatment, verify it, and write the file."""
    img = ui_safe(img * vignette()[..., None])

    # Hard ceiling on overall brightness. This is what keeps the set feeling
    # like a background rather than a photograph someone left on the screen.
    mean = img.mean()
    if mean > ceiling:
        img *= ceiling / mean

    out = encode(img)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    # JPEG at high quality with no chroma subsampling. These images are mostly
    # dark and mostly smooth, which is where 4:2:0 shows its worst colour
    # bleeding; 4:4:4 avoids it, and the dither already applied hides the
    # blocking that near-black JPEG would otherwise reveal.
    out.save(path, quality=93, subsampling=0, optimize=True, progressive=True)

    grey = np.asarray(out.convert("L"), dtype=np.float64) / 255.0
    top = grey[: int(H * 0.03)].mean()
    centre = grey[int(H * 0.3): int(H * 0.7), int(W * 0.25): int(W * 0.75)].mean()
    print(
        f"  {name:<26} mean {grey.mean():.3f}  waybar band {top:.3f}  "
        f"walker area {centre:.3f}  ({path.stat().st_size // 1024} KB)"
    )


# ---------------------------------------------------------------------------
# 1. Carbon weave — the trim insert on an ALPINA dashboard
# ---------------------------------------------------------------------------
def carbon_weave() -> None:
    px, py = np.meshgrid(np.arange(W), np.arange(H))
    cell = 26  # one fibre bundle

    # 2x2 twill: alternating blocks run warp or weft.
    warp = ((px // cell) + (py // cell)) % 2 == 0

    # Across a bundle the fibres catch light in a soft arc; along it they show
    # fine striation. Swapping the two axes per block is what reads as woven.
    across = np.where(warp, (py % cell) / cell, (px % cell) / cell)
    along = np.where(warp, px, py)
    bundle = np.sin(across * np.pi) ** 0.7
    striation = 0.5 + 0.5 * np.sin(along * 0.9)
    weave = bundle * (0.82 + 0.18 * striation)

    # Blocks running one way sit fractionally deeper than the other.
    weave *= np.where(warp, 1.0, 0.88)

    img = field(p.GRAPHITE, 0.10 + 0.28 * weave)

    # A cold key light from the upper left, and a Bavarian blue bounce from
    # the lower right. Both are barely there — this is a dark carbon panel.
    img += field("#9FB4CC", 0.10 * radial(0.18, 0.10, 1.25, 2.6) * weave)
    img += field(p.BAVARIAN, 0.055 * radial(0.86, 0.92, 1.05, 2.2) * weave)
    img += field(p.CARBON, np.full((H, W), 0.30))

    finish(img, "02-carbon-weave.jpg", ceiling=0.055)


# ---------------------------------------------------------------------------
# 2. Ambient — the cabin light strip at night
# ---------------------------------------------------------------------------
def ambient_light() -> None:
    x, y = grid()
    img = field(p.CARBON, np.full((H, W), 0.55))

    # One long, soft light bar sweeping across the lower third, the way an
    # ambient strip runs along a door card. Highlights sit low and left, well
    # clear of both Waybar and Walker.
    bar = np.exp(-(((y - 0.78) / 0.080) ** 2))
    sweep = smoothstep(-0.15, 0.42, x) * (1.0 - smoothstep(0.48, 1.05, x))
    img += field(p.BAVARIAN, 0.26 * bar * sweep)
    img += field(p.FOCUS, 0.085 * np.exp(-(((y - 0.78) / 0.024) ** 2)) * sweep)

    # A wide, very low glow so the bar has something to sit in.
    img += field(p.ALPINA, 0.24 * radial(0.28, 0.86, 1.5, 1.7))
    img += field(p.AMBIENT, 0.022 * radial(0.82, 0.58, 0.80, 2.4))

    # Fine grain keeps large flat areas from looking synthetic.
    img *= (0.97 + 0.06 * value_noise(6, 4, 3))[..., None]

    finish(img, "03-ambient-light.jpg", ceiling=0.055)


# ---------------------------------------------------------------------------
# 3. Midnight run — long exposure, autobahn at night
# ---------------------------------------------------------------------------
def midnight_run() -> None:
    x, y = grid()
    img = field(p.CARBON, np.full((H, W), 0.60))

    # Sky darkens upward; a cold horizon glow sits just above the road.
    img += field(p.ALPINA, 0.28 * (1.0 - smoothstep(0.30, 0.62, y)) * 0.5)
    img += field(p.BAVARIAN, 0.10 * np.exp(-(((y - 0.60) / 0.045) ** 2)))

    # Light trails. Each is a horizontal streak with a soft vertical profile
    # and an eased fade along its length — a long exposure, not a laser.
    for _ in range(11):
        ty = RNG.uniform(0.62, 0.93)
        thickness = RNG.uniform(0.0018, 0.0075)
        x0 = RNG.uniform(-0.25, 0.55)
        length = RNG.uniform(0.35, 0.95)
        # Trails nearer the bottom read as nearer the camera: brighter, thicker.
        depth = smoothstep(0.60, 0.95, ty)
        strength = RNG.uniform(0.07, 0.20) * (0.35 + 0.65 * depth)
        colour = p.FOCUS if RNG.random() < 0.72 else p.MOTORSPORT
        if colour == p.MOTORSPORT:
            strength *= 0.30  # tail lights stay embers, never a red wash

        profile = np.exp(-(((y - ty) / (thickness * (1 + 2 * depth))) ** 2))
        run = smoothstep(x0, x0 + 0.12, x) * (1.0 - smoothstep(x0 + length - 0.30, x0 + length, x))
        img += field(colour, strength * profile * run)

    # Wet asphalt: a broad dark sheen with a faint vertical smear of the trails.
    road = smoothstep(0.58, 0.72, y)
    img += field(p.GRAPHITE, 0.18 * road)
    img += field(p.BAVARIAN, 0.030 * road * (0.4 + 0.6 * value_noise(10, 3, 3)))

    finish(img, "04-midnight-run.jpg", ceiling=0.050)


# ---------------------------------------------------------------------------
# 4. Instrument arc — a gauge sweep, drawn as precisely as a real one
# ---------------------------------------------------------------------------
def instrument_arc() -> None:
    x, y = grid()
    img = field(p.CARBON, np.full((H, W), 0.62))

    # The gauge is centred off-canvas to the lower right, so the sweep enters
    # the frame as an arc rather than sitting in the middle like a target.
    cx, cy = 0.80, 0.86
    ax = (x - cx) * (W / H)
    ay = y - cy
    r = np.sqrt(ax**2 + ay**2)
    theta = np.arctan2(-ay, ax)  # 0 = east, pi/2 = north

    radius = 0.62
    # Only the upper-left sweep of the dial is inside the frame. The window is
    # feathered rather than clipped: a hard angular cut leaves a straight edge
    # across the glow, which immediately reads as a rendering mistake.
    # The window closes at 172 degrees, safely short of the +/-180 wrap in
    # atan2. Running past it made theta jump sign along the horizontal through
    # the hub, which stamped a hard straight edge across the glow.
    lo, hi = np.deg2rad(96), np.deg2rad(172)

    def sector(feather_deg: float) -> np.ndarray:
        f = np.deg2rad(feather_deg)
        return smoothstep(lo, lo + f, theta) * (1.0 - smoothstep(hi - f, hi, theta))

    # The line and ticks want crisp ends; the wash needs a much softer one, or
    # the sector boundary reads as a drawn edge rather than as light.
    live = sector(10)
    live_wash = sector(34)

    # The dial line itself: thin, even, and slightly brighter as it sweeps up.
    line = np.exp(-(((r - radius) / 0.0022) ** 2)) * live
    ramp = smoothstep(lo, hi, theta)
    img += field(p.BAVARIAN, 0.55 * line * (0.30 + 0.70 * ramp))

    # A faint inner wash, as though the dial face is lit from behind.
    wash = smoothstep(radius, radius - 0.34, r) * live_wash
    img += field(p.ALPINA, 0.20 * wash * (0.2 + 0.8 * ramp))

    # Ticks. Majors every 10 degrees, minors every 2 — the rhythm is what
    # makes it read as an instrument rather than as decoration.
    deg = np.rad2deg(theta)
    for step, length, weight, colour in (
        (2.0, 0.022, 0.16, p.SILVER),
        (10.0, 0.055, 0.42, p.ALPINE),
    ):
        phase = np.abs(((deg / step) % 1.0) - 0.5) * 2.0  # 1 at a tick
        tick = smoothstep(0.985, 1.0, phase)
        band = smoothstep(radius, radius + 0.004, r) * (1.0 - smoothstep(radius + length, radius + length + 0.004, r))
        img += field(colour, weight * tick * band * live * (0.25 + 0.75 * ramp))

    # The needle: one decisive line, at a plausible reading.
    needle_angle = np.deg2rad(152)
    delta = np.abs(theta - needle_angle)
    needle = (
        np.exp(-((delta / 0.0055) ** 2))
        * smoothstep(radius + 0.01, radius - 0.05, r)  # stops at the dial line
        * smoothstep(0.06, 0.16, r)                    # fades out of the hub
        * live                                         # never leaves the sector
    )
    img += field(p.MOTORSPORT, 0.30 * needle)

    # Hub glow, so the needle has an origin even though it is off-frame.
    img += field(p.BAVARIAN, 0.045 * radial(cx, cy, 0.38, 2.6))

    finish(img, "05-instrument-arc.jpg", ceiling=0.042)


# ---------------------------------------------------------------------------
# 5. Bavarian ridge — the Alps at last light
# ---------------------------------------------------------------------------
def bavarian_ridge() -> None:
    x, y = grid()
    img = field(p.CARBON, np.full((H, W), 0.55))

    # Sky: carbon overhead easing into deep ALPINA blue at the horizon.
    sky = smoothstep(0.0, 0.78, y)
    img += field(p.ALPINA, 0.30 * sky**2)
    img += field(p.BAVARIAN, 0.11 * np.exp(-(((y - 0.70) / 0.10) ** 2)))
    img += field(p.AMBIENT, 0.028 * np.exp(-(((y - 0.695) / 0.030) ** 2)))

    # Four ridge lines. Each nearer layer is darker and rougher, which is what
    # produces aerial perspective without any actual haze simulation.
    # Few, broad peaks. The earlier version stacked high harmonics and the
    # result read as a treeline rather than as mountains — real ridges are
    # dominated by one long wavelength with only slight detail on top.
    layers = [
        (0.645, 0.085, 1.3, 0.36, "#22303F"),
        (0.690, 0.068, 1.9, 0.28, "#1A2632"),
        (0.740, 0.052, 2.7, 0.22, "#131C26"),
        (0.805, 0.040, 3.6, 0.16, "#0C131B"),
    ]
    xs = np.linspace(0, 1, W)
    for base, amp, freq, weight, colour in layers:
        # Irrational frequency ratios so the profile never visibly repeats,
        # with the detail harmonics kept small.
        profile = (
            np.sin(xs * freq * 2 * np.pi + RNG.uniform(0, 6.28)) * 0.70
            + np.sin(xs * freq * 2.3 * 2 * np.pi + RNG.uniform(0, 6.28)) * 0.22
            + np.sin(xs * freq * 5.1 * 2 * np.pi + RNG.uniform(0, 6.28)) * 0.08
        )
        ridge = base - amp * profile
        mask = smoothstep(-0.0015, 0.0015, y - ridge[None, :])
        img *= 1.0 - 0.55 * mask[..., None]  # the ridge occludes what is behind
        img += field(colour, weight * mask)

    finish(img, "06-bavarian-ridge.jpg", ceiling=0.048)


# ---------------------------------------------------------------------------
# 6. Machined — dark anodised aluminium, brushed
# ---------------------------------------------------------------------------
def machined() -> None:
    x, y = grid()

    # Brushed metal is noise smeared along one axis. Averaging a stack of
    # x-shifted copies of the same noise is a cheap, convincing box blur.
    base = RNG.random((H, W))
    grain = np.zeros_like(base)
    taps = 48
    for shift in range(taps):
        grain += np.roll(base, shift - taps // 2, axis=1)
    grain /= taps
    grain = (grain - grain.min()) / (grain.max() - grain.min())

    # Fine turned lines on top of the brush.
    lines = 0.5 + 0.5 * np.sin(y * H * 0.55 + grain * 6.0)

    # Dark anodised, not polished. The first pass came out closer to brushed
    # stainless, which is far too bright to sit under a UI built on restraint.
    surface = 0.06 + 0.20 * grain * (0.80 + 0.20 * lines)
    img = field(p.MACHINED, surface)

    # A narrow specular sweep, kept low and to one side so it never lands
    # behind Waybar or Walker.
    sweep = np.exp(-((((x * 0.85 + y * 0.55) - 0.92) / 0.20) ** 2))
    img += field("#8496AA", 0.055 * sweep * (0.55 + 0.45 * grain))
    img += field(p.BAVARIAN, 0.035 * radial(0.20, 0.86, 1.0, 2.2))
    img += field(p.CARBON, np.full((H, W), 0.42))

    finish(img, "07-machined.jpg", ceiling=0.018)


def main() -> None:
    print(f"Rendering Bavarian backgrounds at {W}x{H}\n")
    carbon_weave()
    ambient_light()
    midnight_run()
    instrument_arc()
    bavarian_ridge()
    machined()
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
