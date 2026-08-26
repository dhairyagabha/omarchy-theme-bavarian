"""
Bavarian — the single source of truth for the theme's colour system.

Every generated config file in this repository derives from the tokens below.
Nothing else in the theme is allowed to invent a colour: if a value is needed,
it is named here first, with the semantic job it does.

The system has five levels. The rarer the level, the louder its meaning.

    L1  Structure   carbon / graphite / slate / machined
    L2  Content     alpine / silver / aluminium
    L3  Interaction alpina / bavarian / focus
    L4  Emphasis    ambient
    L5  Exceptional amber / motorsport / verde / violet

Reference points: BMW Alpinweiss, BMW roundel blue, ALPINA's deep blue and
green detailing, machined aluminium trim, carbon weave, and the amber/red of a
motorsport instrument cluster at night.
"""

# --------------------------------------------------------------------------
# L1 — Structure. The overwhelming majority of every surface.
# --------------------------------------------------------------------------
CARBON = "#05070A"  # deepest ground: terminal, lock screen, launcher base
GRAPHITE = "#0A0E14"  # primary chrome: waybar, walker, notification bodies
SLATE = "#111721"  # raised surface: tooltips, popovers, selected rows
MACHINED = "#1B2430"  # hairline dividers, inactive borders, aluminium trim

# --------------------------------------------------------------------------
# L2 — Content. Alpine white through cool silver to machined grey.
# --------------------------------------------------------------------------
ALPINE = "#E6EAF0"  # primary text, highest-emphasis content
SILVER = "#A9B4C0"  # secondary text, inactive-but-present modules
ALUMINIUM = "#667380"  # muted text, comments, disabled state

# Terminal body text sits one notch below ALPINE. Pure alpine white over
# carbon is ~16:1 — technically excellent, physically tiring across a full
# working day. This keeps ~12:1 and reserves ALPINE for genuine emphasis.
TEXT = "#D6DDE6"

# --------------------------------------------------------------------------
# L3 — Interaction. Bavarian blue carries focus, selection and active state.
# --------------------------------------------------------------------------
ALPINA = "#0A2E6B"  # deep ALPINA blue — selection *background* only
BAVARIAN = "#2C7FD4"  # the accent: active borders, cursor, active modules
FOCUS = "#5AA9F0"  # brighter blue: focused text, keyboard emphasis

# --------------------------------------------------------------------------
# L4 — Emphasis. Ambient cabin lighting. Used in slivers, never in fields.
# --------------------------------------------------------------------------
AMBIENT = "#4FB8CE"  # subtle cyan: connected, healthy, live

# --------------------------------------------------------------------------
# L5 — Exceptional. These should be rare enough to mean something.
# --------------------------------------------------------------------------
AMBER = "#D89A4E"  # warning, elevated load — instrument-cluster amber
MOTORSPORT = "#D2544A"  # critical, error — restrained motorsport red
VERDE = "#5FA97D"  # success — ALPINA green, deliberately desaturated
VIOLET = "#A67BC9"  # rare/special states, seldom seen

# --------------------------------------------------------------------------
# Brighter counterparts. These are the "ambient light" tier: they exist so
# ANSI bright colours and hover states stay distinguishable without any of
# them turning into neon. Each is a lift of its L5/L4 sibling, not a new hue.
# --------------------------------------------------------------------------
AMBER_LIFT = "#EBBA74"
MOTORSPORT_LIFT = "#E06A5F"
VERDE_LIFT = "#7FC79B"
VIOLET_LIFT = "#C49BE0"
AMBIENT_LIFT = "#74D4E8"

# ANSI 0 and 8. Black must stay visible against carbon; bright-black is the
# comment colour and therefore has a real readability floor to clear. It is
# the rung of the grey ramp directly below ALUMINIUM:
#
#   MACHINED -> ANSI_BRIGHT_BLACK -> ALUMINIUM -> SILVER -> TEXT -> ALPINE
#
ANSI_BLACK = "#12171F"
ANSI_BRIGHT_BLACK = "#576373"

# --------------------------------------------------------------------------
# The 22 values Omarchy requires in colors.toml, in its own vocabulary.
# --------------------------------------------------------------------------
COLORS_TOML = {
    "accent": BAVARIAN,
    "cursor": FOCUS,
    "foreground": TEXT,
    "background": CARBON,
    "selection_foreground": ALPINE,
    "selection_background": ALPINA,
    "color0": ANSI_BLACK,
    "color1": MOTORSPORT,
    "color2": VERDE,
    "color3": AMBER,
    "color4": BAVARIAN,
    "color5": VIOLET,
    "color6": AMBIENT,
    "color7": SILVER,
    "color8": ANSI_BRIGHT_BLACK,
    "color9": MOTORSPORT_LIFT,
    "color10": VERDE_LIFT,
    "color11": AMBER_LIFT,
    "color12": FOCUS,
    "color13": VIOLET_LIFT,
    "color14": AMBIENT_LIFT,
    "color15": ALPINE,
}

ANSI_NAMES = [
    "black", "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "bright black", "bright red", "bright green", "bright yellow",
    "bright blue", "bright magenta", "bright cyan", "bright white",
]


def ansi(index: int) -> str:
    """Return the hex value for ANSI colour `index` (0-15)."""
    return COLORS_TOML[f"color{index}"]


def rgb(hex_colour: str) -> tuple[int, int, int]:
    """'#RRGGBB' -> (r, g, b) as 0-255 integers."""
    h = hex_colour.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgba_hypr(hex_colour: str, alpha: float = 1.0) -> str:
    """Hyprland's rgba(RRGGBBAA) literal, used for border and shadow colours."""
    return f"rgba({hex_colour.lstrip('#').lower()}{round(alpha * 255):02x})"


def rgba_css(hex_colour: str, alpha: float) -> str:
    """CSS rgba() literal, used wherever GTK needs real transparency."""
    r, g, b = rgb(hex_colour)
    return f"rgba({r}, {g}, {b}, {alpha:g})"


def rgba_hyprlock(hex_colour: str, alpha: float = 1.0) -> str:
    """hyprlock's rgba(r,g,b,a) literal — decimal channels, no spaces."""
    r, g, b = rgb(hex_colour)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def hex_alpha(hex_colour: str, alpha: float) -> str:
    """'#RRGGBBAA' — the form mako and other wlroots tools expect."""
    return f"{hex_colour.upper()}{round(alpha * 255):02X}"


def relative_luminance(hex_colour: str) -> float:
    """WCAG 2.1 relative luminance."""

    def channel(value: int) -> float:
        srgb = value / 255
        return srgb / 12.92 if srgb <= 0.04045 else ((srgb + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb(hex_colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2.1 contrast ratio between two colours, always >= 1."""
    a, b = relative_luminance(foreground), relative_luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)
