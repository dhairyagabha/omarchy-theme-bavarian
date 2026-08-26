#!/usr/bin/env python3
"""
Fetch freely-licensed BMW photography from Wikimedia Commons.

Only files under a free licence (public domain, CC0, CC BY, CC BY-SA) are
accepted, and every one that is kept is recorded in backgrounds/CREDITS.md with
its author, licence and source URL. Attribution is not optional for the CC BY-SA
files, so the credits file is part of the deliverable, not a nicety.

Works in two phases, because most car photography on Commons is show-floor and
forecourt snapshots and downloading it all at full resolution is both slow and
rude to the API:

    python3 bin/fetch-wallpapers.py proofs
        Search, filter by licence and dimensions, then pull a small proof of
        every candidate into backgrounds/.proofs/.

    python3 bin/rank-photos.py
        Score the proofs on how well they would work as a dark background.

    python3 bin/fetch-wallpapers.py full <stem> [<stem> ...]
        Pull 4K renders of the ones actually worth keeping into
        backgrounds/.raw/, ready for bin/grade-wallpaper.py.

The raw download is never the wallpaper. Photographs of cars are lit to sell
cars: bright, saturated, high-contrast, subject dead centre. Left alone they
fight the UI. bin/grade-wallpaper.py does the cinematic treatment.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROOFS = ROOT / "backgrounds" / ".proofs"
RAW = ROOT / "backgrounds" / ".raw"
MANIFEST = PROOFS / "manifest.json"

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "omarchy-theme-bavarian/1.0 "
    "(https://github.com/dhairyagabha/omarchy-theme-bavarian)"
)

FREE_LICENCES = re.compile(
    r"^(cc0|cc[- ]by([- ]sa)?([- ][\d.]+)?|public domain|pd|no restrictions)",
    re.IGNORECASE,
)

# Weighted toward the contexts that actually produce dark, composed frames:
# motor-show stands, the BMW Welt and Museum, motorsport, and the halo cars
# that tend to get photographed properly rather than snapped in a car park.
SEARCHES = [
    "BMW M1",
    "BMW 3.0 CSL",
    "BMW M3 E30",
    "BMW M4",
    "BMW M5",
    "BMW M2",
    "BMW M8",
    "BMW i8",
    "BMW 8 Series",
    "BMW Z8",
    "BMW 507",
    "BMW Welt",
    "BMW Museum",
    "BMW concept car",
    "BMW Vision",
    "BMW Motorsport racing",
    "BMW 2002 turbo",
    "BMW iX",
    "Alpina B7",
    "Alpina XB7",
]

MIN_WIDTH = 2400
MIN_ASPECT = 1.45   # landscape enough to crop to 16:9 without losing the car
PROOF_WIDTH = 720   # enough to judge composition and tone, cheap to fetch
FULL_WIDTH = 3840


def api(params: dict, attempts: int = 5) -> dict:
    """Call the Commons API with polite backoff on rate limiting."""
    url = f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
    delay = 3.0
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            if attempt == attempts:
                print(f"    ! giving up: {exc}", file=sys.stderr)
                return {}
            print(f"    . retry {attempt}/{attempts} in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    return {}


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value or "")).strip()


def slug(title: str) -> str:
    name = title.removeprefix("File:").rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def search(term: str, limit: int = 30) -> list[dict]:
    """
    One request per search term.

    Using search as a *generator* lets the same call return imageinfo for every
    hit, instead of a search call followed by a batch of metadata calls. That is
    roughly a third of the requests, which matters: Commons rate-limits hard
    enough that the naive version could not finish the term list.
    """
    data = api({
        "action": "query",
        "generator": "search", "gsrsearch": term,
        "gsrnamespace": "6", "gsrlimit": str(limit),
        "prop": "imageinfo", "iiprop": "url|size|extmetadata",
    })
    out = []
    for page in data.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if not info.get("url"):
            continue
        meta = info.get("extmetadata", {})
        out.append({
            "title": page["title"],
            "stem": slug(page["title"]),
            "descriptionurl": info.get("descriptionurl", ""),
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "licence": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
            "artist": strip_html(meta.get("Artist", {}).get("value", "")),
        })
    return out


def acceptable(item: dict) -> tuple[bool, str]:
    if not FREE_LICENCES.match(item["licence"]):
        return False, f"licence {item['licence'] or 'unknown'!r}"
    if item["width"] < MIN_WIDTH:
        return False, f"too small ({item['width']}px)"
    if not item["height"] or item["width"] / item["height"] < MIN_ASPECT:
        return False, f"not landscape ({item['width']}x{item['height']})"
    return True, ""


def download(item: dict, dest: Path, width: int) -> bool:
    """
    Pull a scaled render rather than the original.

    Commons rate-limits bulk fetches of full-resolution originals and asks
    clients to use thumbnail sizes instead. We never need more than 4K and the
    originals run past 30MB, so this is both the polite route and the one that
    gives us the file we actually want.
    """
    filename = urllib.parse.quote(item["title"].removeprefix("File:").replace(" ", "_"))
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width={width}"
    delay = 3.0
    for attempt in range(1, 4):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if len(data) < 15_000:  # an error page, not a photograph
                raise ValueError(f"suspiciously small response ({len(data)} bytes)")
            dest.write_bytes(data)
            return True
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                print(f"    ! download failed: {exc}", file=sys.stderr)
                return False
            time.sleep(delay)
            delay *= 2
    return False


def phase_proofs() -> None:
    """
    Search, filter and pull proofs term by term.

    The manifest is rewritten after every term and existing proofs are skipped,
    so a run that dies partway through — which is the normal outcome when the
    API starts throttling — can simply be run again.
    """
    PROOFS.mkdir(parents=True, exist_ok=True)

    kept: dict[str, dict] = {}
    if MANIFEST.exists():
        kept = {i["stem"]: i for i in json.loads(MANIFEST.read_text())}
        print(f"resuming with {len(kept)} candidates already recorded\n")

    for term in SEARCHES:
        hits = search(term)
        added = 0
        for item in hits:
            if item["stem"] in kept:
                continue
            ok, _ = acceptable(item)
            if not ok:
                continue
            dest = PROOFS / f"{item['stem']}.jpg"
            if not dest.exists():
                if not download(item, dest, PROOF_WIDTH):
                    dest.unlink(missing_ok=True)
                    continue
                time.sleep(0.4)
            kept[item["stem"]] = item
            added += 1
        print(f"  {term:<26} {len(hits):>3} hits  {added:>2} new")
        MANIFEST.write_text(json.dumps(list(kept.values()), indent=2))
        time.sleep(1.0)

    print(f"\n{len(kept)} proofs -> {PROOFS}")
    print("Next: python3 bin/rank-photos.py")


def phase_full(stems: list[str]) -> None:
    if not MANIFEST.exists():
        print("No manifest. Run: python3 bin/fetch-wallpapers.py proofs", file=sys.stderr)
        sys.exit(1)
    index = {i["stem"]: i for i in json.loads(MANIFEST.read_text())}
    RAW.mkdir(parents=True, exist_ok=True)

    for stem in stems:
        item = index.get(stem)
        if not item:
            print(f"  ! {stem} is not in the manifest", file=sys.stderr)
            continue
        dest = RAW / f"{stem}.jpg"
        if dest.exists():
            print(f"  have  {stem}")
            continue
        if download(item, dest, FULL_WIDTH):
            print(f"  got   {stem:<58} ({dest.stat().st_size // 1024} KB)")
        else:
            dest.unlink(missing_ok=True)
        time.sleep(0.8)


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "proofs":
        phase_proofs()
    elif args and args[0] == "full":
        phase_full(args[1:])
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
