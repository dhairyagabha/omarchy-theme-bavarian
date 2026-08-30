# Wallpaper credits and licensing

Two different licences apply inside this directory. Please keep them straight
if you redistribute anything.

## Hero image — licence NOT verified, please read

`01-alpina-e30-c2.jpg` — BMW E30 ALPINA C2 2.7

Supplied by the repository owner and processed by `bin/grade-wallpaper.py`
(panning amplified, desaturated, cooled, graded and vignetted). The car is
shown as photographed, number plate included.

**Its copyright status has not been established.** The source has the look of
commissioned motoring-press photography, which is normally all-rights-reserved,
and no author or licence travelled with it. Nothing here grants any right to
it, and grading a photograph does not create one.

Before this repository is made public, or the theme is submitted to the Omarchy
extra-themes list, please do one of:

- confirm you own the image, or hold a licence that permits redistribution;
- identify the photographer and obtain permission, then record it here;
- replace it with an image you can license, using the same recipe:
  `python3 bin/grade-wallpaper.py your-photo.jpg --out backgrounds/`

If none of those apply, delete `01-alpina-e30-c2.jpg` and the `alpina-e30-c2`
entry in `bin/grade-wallpaper.py`. The theme is designed to survive that: the
remaining eight backgrounds are either original or properly licensed.

## Original artwork — MIT

`02-carbon-weave.jpg` · `03-ambient-light.jpg` · `04-midnight-run.jpg`
`05-instrument-arc.jpg` · `06-bavarian-ridge.jpg` · `07-machined.jpg`

Generated procedurally by `bin/make-backgrounds.py` from the theme palette.
They contain no third-party material and are covered by this repository's MIT
licence. Re-render them at any time with:

```bash
python3 bin/make-backgrounds.py
```

## Photography — CC BY-SA 4.0

`08-alpina-tail-light.jpg` · `09-alpina-b5-touring.jpg`

These are **adaptations** of photographs from Wikimedia Commons. They have been
cropped, desaturated, colour-graded, darkened and vignetted by
`bin/grade-wallpaper.py`.

The source photographs are licensed CC BY-SA 4.0, which is a copyleft licence.
That has two consequences you must respect:

1. **Attribution is required.** The credits below must travel with the images.
2. **ShareAlike applies to the adaptations.** These two files, and any further
   derivative you make of them, remain under CC BY-SA 4.0 — they are *not*
   covered by this repository's MIT licence.

| File | Source photograph | Author | Licence |
|---|---|---|---|
| `08-alpina-tail-light.jpg` | [Alpina B7, IAA 2017, Frankfurt (1Y7A3123)](https://commons.wikimedia.org/wiki/File:Alpina_B7,_IAA_2017,_Frankfurt_(1Y7A3123).jpg) | Matti Blume | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| `09-alpina-b5-touring.jpg` | [Alpina, GIMS 2018, Le Grand-Saconnex (1X7A1256)](https://commons.wikimedia.org/wiki/File:Alpina,_GIMS_2018,_Le_Grand-Saconnex_(1X7A1256).jpg) | Matti Blume | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |

## Trademarks

BMW, the BMW roundel, and ALPINA are trademarks of their respective owners.
This is an unofficial, fan-made theme. It is not affiliated with, endorsed by,
or connected to BMW AG or ALPINA Burkard Bovensiepen GmbH + Co. KG. No logo or
wordmark is reproduced anywhere in the theme's UI — the reference is carried by
colour, proportion and behaviour, which is also what the design brief asked
for.

## Adding your own

The best wallpapers for this theme are your own licensed photographs, graded
to match:

```bash
python3 bin/grade-wallpaper.py ~/Pictures/my-alpina.jpg --out backgrounds/
python3 bin/grade-wallpaper.py photo.jpg --crop 0.1,0.05,0.9,0.95 --blur 2.5
```

If you add photography you did not take, record its author and licence here
before you push.
