#!/usr/bin/env python3
"""
Accessibility gate for the Bavarian palette.

Checks three things the design brief insists on and that are easy to get wrong
by eye alone:

  1. Text contrast — every colour that is ever rendered as text clears a WCAG
     ratio against the surface it is rendered on.
  2. Separation — semantically distinct colours are actually distinguishable
     from one another, not merely different hex values.
  3. Colour-blind safety — that separation survives protanopia, deuteranopia
     and tritanopia, since state must never be carried by hue alone.

Run:  python3 bin/validate-contrast.py
Exits non-zero if any check fails, so it can gate a commit.
"""

import sys
from itertools import combinations

import palette as p

# ---------------------------------------------------------------------------
# Colour science helpers
# ---------------------------------------------------------------------------

# Viénot, Brettel & Mollon (1999) dichromat simulation, applied to linear RGB.
DICHROMAT_MATRICES = {
    "protanopia": (
        (0.11238, 0.88762, 0.00000),
        (0.11238, 0.88762, 0.00000),
        (0.00401, -0.00401, 1.00000),
    ),
    "deuteranopia": (
        (0.29275, 0.70725, 0.00000),
        (0.29275, 0.70725, 0.00000),
        (-0.02234, 0.02234, 1.00000),
    ),
    "tritanopia": (
        (1.00000, 0.14461, -0.14461),
        (0.00000, 1.00000, 0.00000),
        (0.00000, 0.15594, 0.84406),
    ),
}


def _to_linear(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4


def _from_linear(v: float) -> int:
    v = min(1.0, max(0.0, v))
    s = 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
    return round(min(1.0, max(0.0, s)) * 255)


def simulate(hex_colour: str, kind: str) -> str:
    """Simulate how `hex_colour` appears to a dichromat viewer."""
    lin = [_to_linear(c) for c in p.rgb(hex_colour)]
    m = DICHROMAT_MATRICES[kind]
    out = [sum(m[row][i] * lin[i] for i in range(3)) for row in range(3)]
    return "#{:02x}{:02x}{:02x}".format(*(_from_linear(v) for v in out))


def _to_lab(hex_colour: str) -> tuple[float, float, float]:
    r, g, b = (_to_linear(c) for c in p.rgb(hex_colour))
    # linear sRGB -> XYZ (D65)
    x = (0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(a: str, b: str) -> float:
    """CIE76 colour difference. ~2.3 is the just-noticeable threshold."""
    la, aa, ba = _to_lab(a)
    lb, ab, bb = _to_lab(b)
    return ((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2) ** 0.5


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

failures: list[str] = []
warnings: list[str] = []


def check(label: str, actual: float, floor: float, unit: str = ":1") -> None:
    ok = actual >= floor
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label:<46} {actual:6.2f}{unit}  (min {floor}{unit})")
    if not ok:
        failures.append(f"{label}: {actual:.2f}{unit} < {floor}{unit}")


print("\nBAVARIAN — palette validation\n" + "=" * 72)

# --- 1. Body text -----------------------------------------------------------
print("\n1. Body text contrast")
check("terminal foreground on carbon", p.contrast_ratio(p.TEXT, p.CARBON), 7.0)
check("alpine white on carbon", p.contrast_ratio(p.ALPINE, p.CARBON), 7.0)
check("silver on graphite (secondary)", p.contrast_ratio(p.SILVER, p.GRAPHITE), 4.5)
check("aluminium on carbon (muted)", p.contrast_ratio(p.ALUMINIUM, p.CARBON), 3.0)
check("selection fg on selection bg", p.contrast_ratio(p.ALPINE, p.ALPINA), 4.5)
check("alpine on graphite (waybar)", p.contrast_ratio(p.ALPINE, p.GRAPHITE), 7.0)
check("alpine on slate (tooltip)", p.contrast_ratio(p.ALPINE, p.SLATE), 7.0)

# --- 2. ANSI colours as text ------------------------------------------------
# color0 is a background swatch, never body text, so it is exempt from the
# text floor; every other ANSI entry must be readable on the terminal ground.
print("\n2. ANSI colours as text on carbon")
for i in range(16):
    value = p.ansi(i)
    name = p.ANSI_NAMES[i]
    ratio = p.contrast_ratio(value, p.CARBON)
    if i == 0:
        print(f"  [ -- ] {name:<20} {value}  {ratio:5.2f}:1  (background swatch, exempt)")
        continue
    floor = 3.0 if i == 8 else 4.5  # bright-black is the comment colour
    check(f"{name:<20} {value}", ratio, floor)

# --- 3. Accent legibility ---------------------------------------------------
print("\n3. Accent legibility")
check("bavarian blue on carbon", p.contrast_ratio(p.BAVARIAN, p.CARBON), 4.5)
check("bavarian blue on graphite", p.contrast_ratio(p.BAVARIAN, p.GRAPHITE), 4.5)
check("focus blue on graphite", p.contrast_ratio(p.FOCUS, p.GRAPHITE), 4.5)
check("ambient cyan on graphite", p.contrast_ratio(p.AMBIENT, p.GRAPHITE), 4.5)
check("amber on graphite (warning)", p.contrast_ratio(p.AMBER, p.GRAPHITE), 4.5)
check("motorsport red on graphite (critical)", p.contrast_ratio(p.MOTORSPORT, p.GRAPHITE), 4.5)
check("machined divider on graphite", p.contrast_ratio(p.MACHINED, p.GRAPHITE), 1.15, "")

# --- 4. Restraint -----------------------------------------------------------
# The brief's hard rule: neon is branding, not decoration. Nothing in the
# palette may be both highly saturated and highly luminous, which is what
# produces glare and eye fatigue over a long session.
print("\n4. Restraint (no colour may be both loud and bright)")
loudest = []
for name, value in p.COLORS_TOML.items():
    r, g, b = p.rgb(value)
    mx, mn = max(r, g, b), min(r, g, b)
    saturation = 0 if mx == 0 else (mx - mn) / mx
    luminance = p.relative_luminance(value)
    loudest.append((saturation * luminance, name, value, saturation, luminance))
loudest.sort(reverse=True)
for score, name, value, sat, lum in loudest[:5]:
    status = "PASS" if score < 0.32 else "FAIL"
    print(f"  [{status}] {name:<22} {value}  sat {sat:.2f}  lum {lum:.2f}  index {score:.3f}")
    if score >= 0.32:
        failures.append(f"{name} is too saturated and too bright (index {score:.3f})")

# --- 5. Colour-blind separation --------------------------------------------
# Only the colours that actually encode *state* need to survive this. Body
# text and structure are separated by luminance, not hue.
print("\n5. Colour-blind separation of state colours")
state_colours = {
    "bavarian (active)": p.BAVARIAN,
    "ambient (connected)": p.AMBIENT,
    "amber (warning)": p.AMBER,
    "motorsport (critical)": p.MOTORSPORT,
    "verde (success)": p.VERDE,
    "silver (neutral)": p.SILVER,
}
JND = 12.0  # comfortably above the ~2.3 just-noticeable threshold
for kind in ("normal", *DICHROMAT_MATRICES):
    worst_pair, worst = None, 1e9
    for (an, av), (bn, bv) in combinations(state_colours.items(), 2):
        if kind != "normal":
            av, bv = simulate(av, kind), simulate(bv, kind)
        d = delta_e(av, bv)
        if d < worst:
            worst, worst_pair = d, (an, bn)
    mark = "PASS" if worst >= JND else "WARN"
    print(f"  [{mark}] {kind:<14} closest pair {worst_pair[0]} / {worst_pair[1]}  ΔE {worst:.1f}")
    if worst < JND:
        warnings.append(
            f"under {kind}, {worst_pair[0]} and {worst_pair[1]} are close (ΔE {worst:.1f}) "
            "— these states must also differ by icon, position or weight"
        )

# ---------------------------------------------------------------------------
print("\n" + "=" * 72)
if warnings:
    print("\nWarnings:")
    for w in warnings:
        print(f"  ! {w}")
if failures:
    print(f"\n{len(failures)} check(s) FAILED:")
    for f in failures:
        print(f"  x {f}")
    sys.exit(1)
print("\nAll contrast and separation checks passed.\n")
