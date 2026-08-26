#!/usr/bin/env python3
"""
Render preview.png — the image Omarchy shows in its theme picker.

It is a mock of the real thing rather than a palette chart: the wallpaper, the
Waybar cluster, an active window wearing the Bavarian blue border, and an
inactive one wearing machined grey. That composition is what actually has to
be judged, because it is what the user will be looking at all day.

Run:  python3 bin/make-preview.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import palette as p  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
W, H = 1920, 1080
BAR_H = 34

FONT_DIR = Path("/mnt/skills/examples/canvas-design/canvas-fonts")
FALLBACK = Path("/usr/share/fonts/truetype/dejavu")


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (FONT_DIR / name, FALLBACK / "DejaVuSansMono.ttf"):
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


MONO = lambda s: font("JetBrainsMono-Regular.ttf", s)      # noqa: E731
MONO_B = lambda s: font("JetBrainsMono-Bold.ttf", s)       # noqa: E731
SANS = lambda s: font("InstrumentSans-Regular.ttf", s)     # noqa: E731


def rgba(hex_colour: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    r, g, b = p.rgb(hex_colour)
    return (r, g, b, round(alpha * 255))


def panel(size: tuple[int, int], fill: str, alpha: float,
          border: str | None = None, radius: int = 2) -> Image.Image:
    """A window: translucent body, 2px border, the same 2px radius Hyprland uses."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        [(0, 0), (size[0] - 1, size[1] - 1)], radius=radius,
        fill=rgba(fill, alpha),
        outline=rgba(border) if border else None,
        width=2 if border else 0,
    )
    return layer


def waybar(draw: ImageDraw.ImageDraw, base: Image.Image) -> None:
    """The instrument cluster: neutral by default, accent only where it means something."""
    bar = Image.new("RGBA", (W, BAR_H), rgba(p.GRAPHITE, 0.93))
    base.alpha_composite(bar, (0, 0))
    draw.line([(0, BAR_H), (W, BAR_H)], fill=rgba(p.MACHINED), width=1)

    f = MONO(14)
    fb = MONO_B(14)

    # Left: the Omarchy mark, then workspaces.
    draw.rounded_rectangle([(18, 12), (30, 24)], radius=2, outline=rgba(p.SILVER), width=2)

    x = 52
    for i, label in enumerate(["1", "2", "3", "4", "5"], start=1):
        active = i == 2
        occupied = i in (1, 2, 3)
        colour = p.BAVARIAN if active else (p.SILVER if occupied else p.ALUMINIUM)
        draw.text((x, 9), label, font=fb if active else f, fill=rgba(colour))
        if active:
            # Active carries an underline as well as the accent, so the current
            # workspace survives without colour vision.
            draw.line([(x - 3, BAR_H - 3), (x + 11, BAR_H - 3)], fill=rgba(p.BAVARIAN), width=2)
        x += 26

    # Centre: clock, in tabular figures.
    clock = "Wednesday 21:04"
    cw = draw.textlength(clock, font=f)
    draw.text(((W - cw) / 2, 9), clock, font=f, fill=rgba(p.ALPINE))

    # Right: telemetry. A hairline pods the cluster off, exactly as the CSS does.
    right = W - 30
    draw.line([(W - 300, 7), (W - 300, BAR_H - 7)], fill=rgba(p.MACHINED), width=1)

    # Battery — neutral, because it is simply discharging.
    right -= 42
    draw.rounded_rectangle([(right, 12), (right + 26, 23)], radius=2, outline=rgba(p.SILVER), width=1)
    draw.rectangle([(right + 27, 15), (right + 29, 20)], fill=rgba(p.SILVER))
    draw.rectangle([(right + 2, 14), (right + 20, 21)], fill=rgba(p.SILVER))

    # CPU — neutral at rest.
    right -= 78
    draw.rounded_rectangle([(right, 12), (right + 12, 24)], radius=1, outline=rgba(p.SILVER), width=1)
    for k in range(3):
        draw.line([(right + 3 + k * 4, 9), (right + 3 + k * 4, 12)], fill=rgba(p.SILVER))
        draw.line([(right + 3 + k * 4, 24), (right + 3 + k * 4, 27)], fill=rgba(p.SILVER))
    draw.text((right + 20, 9), "14%", font=MONO(13), fill=rgba(p.SILVER))

    # Ethernet — the one occasional state that earns the ambient cyan.
    right -= 62
    draw.rounded_rectangle([(right, 13), (right + 20, 23)], radius=2, outline=rgba(p.AMBIENT), width=1)
    draw.line([(right + 10, 23), (right + 10, 27)], fill=rgba(p.AMBIENT))
    draw.line([(right + 4, 27), (right + 16, 27)], fill=rgba(p.AMBIENT))


def terminal(base: Image.Image) -> None:
    """The active window. Bavarian blue border, carbon body, real ANSI output."""
    x0, y0, w, h = 96, 128, 1020, 432
    win = panel((w, h), p.CARBON, 0.94, p.BAVARIAN)
    d = ImageDraw.Draw(win)

    f, fb = MONO(15), MONO_B(15)
    lh = 24
    y = 20

    d.text((20, y), "~/omarchy-theme-bavarian", font=f, fill=rgba(p.ALUMINIUM)); y += lh + 4
    d.text((20, y), "❯", font=fb, fill=rgba(p.BAVARIAN))
    d.text((44, y), "python3 bin/validate-contrast.py", font=f, fill=rgba(p.TEXT)); y += lh + 10

    # Measured live from the palette, so the preview can never advertise a
    # contrast figure the theme no longer has.
    for label, fg, bg in [
        ("terminal foreground on carbon", p.TEXT, p.CARBON),
        ("bavarian blue on graphite", p.BAVARIAN, p.GRAPHITE),
        ("motorsport red on graphite", p.MOTORSPORT, p.GRAPHITE),
        ("aluminium on carbon (muted)", p.ALUMINIUM, p.CARBON),
    ]:
        d.text((20, y), "  [PASS]", font=f, fill=rgba(p.VERDE))
        d.text((110, y), label, font=f, fill=rgba(p.SILVER))
        d.text((470, y), f"{p.contrast_ratio(fg, bg):5.2f}:1", font=f, fill=rgba(p.TEXT))
        y += lh
    y += 6
    d.text((20, y), "  [WARN]", font=f, fill=rgba(p.AMBER))
    d.text((110, y), "protanopia: ambient / silver close", font=f, fill=rgba(p.SILVER))
    y += lh + 18

    # A short piece of the theme's own source, so the syntax colours are real.
    d.text((20, y), "# Level 5 — Exceptional. Rare enough to mean something.", font=f,
           fill=rgba(p.ANSI_BRIGHT_BLACK)); y += lh
    for name, value in [("AMBER", p.AMBER), ("MOTORSPORT", p.MOTORSPORT), ("VERDE", p.VERDE)]:
        d.text((20, y), name, font=f, fill=rgba(p.TEXT))
        d.text((20 + 11 * len(name) + 8, y), "=", font=f, fill=rgba(p.SILVER))
        d.text((20 + 11 * len(name) + 24, y), f'"{value}"', font=f, fill=rgba(p.VERDE))
        y += lh
    y += 22

    # The 16 ANSI colours, normal over bright — the row that decides whether a
    # terminal is actually comfortable to live in.
    d.text((20, y), "ANSI", font=MONO(12), fill=rgba(p.ALUMINIUM))
    sw, sh, gap = 52, 20, 6
    for row in range(2):
        for col in range(8):
            cx = 76 + col * (sw + gap)
            cy = y + row * (sh + gap)
            d.rectangle([(cx, cy), (cx + sw, cy + sh)], fill=rgba(p.ansi(row * 8 + col)))

    base.alpha_composite(win, (x0, y0))


def telemetry(base: Image.Image) -> None:
    """The inactive window: machined border, and the btop graph gradients."""
    x0, y0, w, h = 1180, 196, 640, 430
    win = panel((w, h), p.GRAPHITE, 0.90, p.MACHINED)
    d = ImageDraw.Draw(win)

    d.text((20, 18), "btop", font=MONO_B(14), fill=rgba(p.ALPINE))
    d.text((70, 19), "performance telemetry", font=MONO(13), fill=rgba(p.ALUMINIUM))
    d.line([(20, 46), (w - 20, 46)], fill=rgba(p.MACHINED), width=1)

    rows = [
        ("cpu", 0.34, [p.FOCUS, p.AMBIENT, p.AMBER]),
        ("mem", 0.61, [p.BAVARIAN, p.BAVARIAN, p.FOCUS]),
        ("used", 0.78, [p.AMBER, p.MOTORSPORT, p.MOTORSPORT_LIFT]),
        ("net", 0.22, [p.FOCUS, p.FOCUS, p.AMBIENT_LIFT]),
    ]
    y = 72
    for label, level, ramp in rows:
        d.text((20, y), label, font=MONO(13), fill=rgba(p.SILVER))
        bx0, bx1 = 74, w - 24
        d.rectangle([(bx0, y + 4), (bx1, y + 14)], fill=rgba(p.SLATE))
        span = int((bx1 - bx0) * level)
        # Each bar is drawn across its own gradient, the way btop fills a graph.
        for i in range(span):
            t = i / max(1, bx1 - bx0)
            if t < 0.5:
                a, b, tt = ramp[0], ramp[1], t * 2
            else:
                a, b, tt = ramp[1], ramp[2], (t - 0.5) * 2
            ar, ag, ab = p.rgb(a)
            br, bg, bb = p.rgb(b)
            col = (round(ar + (br - ar) * tt), round(ag + (bg - ag) * tt), round(ab + (bb - ab) * tt), 255)
            d.line([(bx0 + i, y + 4), (bx0 + i, y + 14)], fill=col)
        y += 34

    # A sampled graph, so the window shows a shape and not only bars.
    y += 10
    d.line([(20, y), (w - 20, y)], fill=rgba(p.MACHINED), width=1)
    y += 16
    import math
    pts = []
    for i in range(w - 60):
        t = i / (w - 60)
        v = (math.sin(t * 9) * 0.28 + math.sin(t * 23 + 1.3) * 0.16 + math.sin(t * 3) * 0.3 + 0.5)
        pts.append((30 + i, y + 112 - v * 112))
    d.line(pts, fill=rgba(p.AMBIENT), width=2, joint="curve")
    d.line([(30, y + 112), (w - 30, y + 112)], fill=rgba(p.MACHINED), width=1)

    y += 140
    d.text((20, y), "notifications", font=MONO(12), fill=rgba(p.ALUMINIUM))
    y += 22
    for urgency, colour in (("normal", p.BAVARIAN), ("critical", p.MOTORSPORT)):
        d.rectangle([(20, y), (21, y + 26)], fill=rgba(colour))
        d.text((34, y + 2), urgency, font=MONO(13), fill=rgba(p.ALPINE))
        d.text((110, y + 2), "border carries the urgency", font=MONO(12), fill=rgba(p.SILVER))
        y += 34

    base.alpha_composite(win, (x0, y0))


def main() -> None:
    source = ROOT / "backgrounds" / "01-alpina-e30-c2.jpg"
    if not source.exists():
        print("Run bin/make-backgrounds.py first.", file=sys.stderr)
        sys.exit(1)

    base = Image.open(source).convert("RGBA").resize((W, H), Image.LANCZOS)
    draw = ImageDraw.Draw(base)

    telemetry(base)   # behind
    terminal(base)    # in front, because it is the focused window
    waybar(draw, base)

    out = ROOT / "preview.png"
    base.convert("RGB").save(out, optimize=True)
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
