# Bavarian

An Omarchy theme built on carbon black, alpine white and Bavarian blue.

The reference points are BMW's understated confidence and ALPINA's
craftsmanship — dark interiors, machined trim, instrument clusters, ambient
cabin lighting at night — kept inside Omarchy's own minimal, keyboard-first,
developer-facing identity. It is meant to look expensive without ever asking
for attention.

![Bavarian](preview.png)

Power without aggression. Luxury without excess. Technology without sterility.

---

## Install

```bash
omarchy-theme-install https://github.com/dhairyagabha/omarchy-theme-bavarian
```

Or from the Omarchy menu: **Style → Theme → Install** and paste the repository
URL. To install by hand:

```bash
git clone https://github.com/dhairyagabha/omarchy-theme-bavarian \
  ~/.config/omarchy/themes/bavarian
```

Then pick it with `Super + Ctrl + Shift + Space`.

---

## The design system

Five levels. The rarer the level, the more meaning it carries. Every colour in
the theme has a job; nothing is here because it looked good.

### Level 1 — Structure

The overwhelming majority of every surface.

| Token | Hex | Job |
|---|---|---|
| `CARBON` | `#05070A` | Deepest ground: terminal, lock screen, launcher base |
| `GRAPHITE` | `#0A0E14` | Chrome: Waybar, Walker, notification bodies |
| `SLATE` | `#111721` | Raised surfaces: tooltips, popovers, selected rows |
| `MACHINED` | `#1B2430` | Hairline dividers, inactive borders — aluminium trim |

### Level 2 — Content

A six-rung grey ramp. Hierarchy comes from weight and position first, colour
last.

| Token | Hex | Job |
|---|---|---|
| `ALPINE` | `#E6EAF0` | Primary text, highest emphasis |
| `TEXT` | `#D6DDE6` | Terminal body text |
| `SILVER` | `#A9B4C0` | Secondary text, modules at rest |
| `ALUMINIUM` | `#667380` | Muted, disabled, absent |
| *bright black* | `#576373` | Terminal comments |

Terminal body text is deliberately one step below alpine white. Pure white on
carbon measures about 16:1 — technically excellent and physically tiring across
a working day. `TEXT` holds ~14.7:1 and leaves `ALPINE` free to mean *emphasis*.

### Level 3 — Interaction

Bavarian blue carries focus, selection and active state. This is the only
colour the user should see regularly.

| Token | Hex | Job |
|---|---|---|
| `ALPINA` | `#0A2E6B` | Deep ALPINA blue — selection **background** only |
| `BAVARIAN` | `#2C7FD4` | The accent: active borders, cursor, active modules |
| `FOCUS` | `#5AA9F0` | Focused text, keyboard emphasis, cursor |

### Level 4 — Emphasis

| Token | Hex | Job |
|---|---|---|
| `AMBIENT` | `#4FB8CE` | Subtle cyan: connected, healthy, live |

### Level 5 — Exceptional

Rare enough that seeing one should mean something.

| Token | Hex | Job |
|---|---|---|
| `AMBER` | `#D89A4E` | Warning, elevated load, suppressed state |
| `MOTORSPORT` | `#D2544A` | Critical, error, recording |
| `VERDE` | `#5FA97D` | Success — ALPINA green, deliberately desaturated |
| `VIOLET` | `#A67BC9` | Rare and special states |

### On neon

Neon here is branding, not decoration. It behaves like ambient lighting inside
a car cabin: present in slivers, never in fields. No element is allowed to be
both highly saturated and highly luminous — that combination is what produces
glare, and `bin/validate-contrast.py` fails the build if any token crosses the
line. If the accent colours are the first thing you notice, something is wrong.

---

## How it fits together

`colors.toml` is what Omarchy reads. It holds the 22 values Omarchy propagates
to the terminal, btop, Chromium, Hyprland, Hyprlock, Mako, SwayOSD, Walker and
Waybar. Everything else in the repository is either a refinement layer on top of
that, or the tooling that produced it.

| File | What it does |
|---|---|
| `colors.toml` | The 22 values Omarchy propagates everywhere |
| `hyprland.conf` | Border colours, 2px rounding, shadow, blur, group bar |
| `hyprlock.conf` | The five variables Omarchy's lock screen consumes |
| `waybar.css` | Colour variables **and** the instrument-cluster refinements |
| `walker.css` | The six colour names Omarchy's Walker theme reads |
| `swayosd.css` | Volume/brightness OSD colours |
| `mako.ini` | Notifications, with per-urgency borders and timeouts |
| `btop.theme` | Telemetry, including all eight graph gradients |
| `alacritty.toml`, `ghostty.conf`, `kitty.conf` | Terminal palettes |
| `neovim.lua` | A self-contained colourscheme — no plugin to install |
| `vscode.json`, `chromium.theme`, `icons.theme` | Editor, browser, icon set |
| `backgrounds/` | Eight wallpapers — see below |

**Do not edit the generated files by hand.** They all derive from
`bin/palette.py`, which is the only place a colour is chosen:

```bash
python3 bin/generate-theme.py      # rewrite every config from the palette
python3 bin/validate-contrast.py   # gate it on contrast and colour-blindness
```

### Waybar

Omarchy's `waybar/style.css` `@import`s the theme file *first* and then
declares its own rules, so every override in `waybar.css` is prefixed with
`window#waybar` to out-specify it. That is deliberate, not decorative.

The rule is that most modules are neutral, all of the time, and colour is spent
only on the state that currently means something:

| Module | At rest | Lit |
|---|---|---|
| Workspace | silver / aluminium if empty | **Bavarian blue** + underline when active |
| Clock | alpine white, tabular figures | — |
| CPU | silver | amber → motorsport under load |
| Network | silver on wifi | **ambient cyan** on ethernet; dimmed when disconnected |
| Bluetooth | silver | **ambient cyan** when connected |
| Battery | silver | blue charging · amber < 20% · motorsport < 10% |
| Recording | hidden | motorsport red |
| Idle inhibit / notifications silenced | hidden | amber |

Two decisions worth explaining:

- **Wifi-connected stays neutral.** The brief's example table puts cyan on
  "connected", but connected is the resting state — an accent that is lit
  almost always is decoration, not signal. Cyan goes to *ethernet* and
  *bluetooth connected* instead, both of which are deliberate and occasional.
- **Disconnected is dimmed, not reddened.** It is an absence, not a fault, and
  Waybar already swaps the glyph.

Waybar ships no `states` block on its CPU module, so `#cpu.warning` and
`#cpu.critical` are styled but never triggered until you opt in. Add this to
`~/.config/waybar/config.jsonc`:

```jsonc
"cpu": { "states": { "warning": 70, "critical": 90 } }
```

### Hyprland

Inactive borders are dark graphite; active borders are a short 45° sweep from
Bavarian blue into deep ALPINA blue — the idea is light travelling along a
machined edge, and at a glance it reads as one considered colour rather than as
a gradient effect. Rounding is 2px: the chamfer on a milled edge, present when
you look for it and invisible when you do not. Blur is pulled darker and flatter
than the Omarchy default so translucent surfaces stay *background*.

---

## Wallpapers

Eight backgrounds, all of them dark, all of them designed to sit *under* a UI:

| | |
|---|---|
| `01-carbon-weave` | Carbon fibre twill, the trim insert on a dashboard |
| `02-ambient-light` | The cabin light strip at night |
| `03-midnight-run` | Long exposure, autobahn after dark |
| `04-instrument-arc` | A gauge sweep with real tick rhythm |
| `05-bavarian-ridge` | The Alps at last light |
| `06-machined` | Dark anodised aluminium, brushed |
| `07-alpina-tail-light` | ALPINA B7 detail, IAA 2017 |
| `08-alpina-b5-touring` | ALPINA B5 Bi-Turbo Touring, Geneva 2018 |

Two constraints are enforced by measurement rather than by eye: mean luminance
stays low, and nothing bright is allowed to sit where the UI lives — the top
edge where Waybar runs, or the centre where Walker opens. Both scripts print
those numbers every time they run.

The first six are generated procedurally from the theme palette
(`bin/make-backgrounds.py`) and are original work. The last two are CC BY-SA 4.0
photographs from Wikimedia Commons, cropped and graded to match — see
[`backgrounds/CREDITS.md`](backgrounds/CREDITS.md), which you must keep with
them.

**A note on the photography.** The brief asked for stock imagery of ALPINA cars
in dark, cinematic settings. Freely-licensed ALPINA photography turns out to be
almost entirely car-show floors, grass fields and dealer forecourts — bright,
cluttered, and shot to sell a car rather than to sit behind a terminal. Two
images survived that filter. Rather than pad the set with heavily-cropped
snapshots, the theme leads with abstract work that hits the same brief and
ships the grading tool so you can add your own licensed photography:

```bash
python3 bin/grade-wallpaper.py ~/Pictures/alpina.jpg --out backgrounds/
python3 bin/grade-wallpaper.py photo.jpg --crop 0.1,0.05,0.9,0.95 --blur 2.5
```

The grade desaturates hard, cools the balance, lifts shadows toward ALPINA
blue, pulls contrast back, sets exposure by measurement, vignettes, and settles
the strip Waybar sits on.

---

## Accessibility

`bin/validate-contrast.py` is a gate, not a formality — it failed three times
while this palette was being built, and the values shipped here are the ones
that passed.

It checks four things:

- **Text contrast.** Body text clears 7:1. Every ANSI colour used as text
  clears 4.5:1 on carbon; the comment grey clears 3:1.
- **Restraint.** No token may be both highly saturated and highly luminous.
- **Colour-blind separation.** State colours are simulated under protanopia,
  deuteranopia and tritanopia and measured pairwise.
- **Structural separation.** Dividers stay visible against their surface.

One warning is expected and deliberate: under protanopia, ambient cyan and
neutral silver converge (ΔE 9.3). That is why **no state in this theme is
carried by hue alone.** The active workspace has an underline as well as the
accent. Battery, network and bluetooth all change glyph. Notifications change
border weight and timeout with urgency. Colour is the last signal, never the
only one.

```
$ python3 bin/validate-contrast.py
  [PASS] terminal foreground on carbon             14.74:1  (min 7.0:1)
  [PASS] bavarian blue on graphite                  4.69:1  (min 4.5:1)
  [PASS] motorsport red on graphite (critical)      4.70:1  (min 4.5:1)
  ...
  All contrast and separation checks passed.
```

---

## Tooling

| Script | Purpose |
|---|---|
| `bin/palette.py` | The single source of truth. Change colours here |
| `bin/generate-theme.py` | Renders every config file from the palette |
| `bin/validate-contrast.py` | Contrast, restraint and colour-blindness gate |
| `bin/make-backgrounds.py` | Renders the six abstract wallpapers |
| `bin/fetch-wallpapers.py` | Pulls freely-licensed photography from Commons |
| `bin/grade-wallpaper.py` | Applies the cinematic grade to a photograph |
| `bin/make-preview.py` | Renders `preview.png` |

Requires Python 3.11+, with `pillow` and `numpy` for the image scripts.

---

## Licence

MIT, except the two photographs in `backgrounds/`, which are CC BY-SA 4.0.
See [`LICENSE`](LICENSE) and [`backgrounds/CREDITS.md`](backgrounds/CREDITS.md).

BMW and ALPINA are trademarks of their respective owners. This is an unofficial
theme, not affiliated with or endorsed by either company. No logo or wordmark
appears anywhere in the UI — the reference is carried entirely by colour,
proportion and behaviour.
