#!/usr/bin/env python3
"""
Fetch freely-licensed ALPINA photography from Wikimedia Commons.

Only files under a free licence (public domain, CC0, CC BY, CC BY-SA) are
accepted, and every one that is kept is recorded in backgrounds/CREDITS.md
with its author, licence and source URL. Attribution is not optional for the
CC BY-SA files, so the credits file is part of the deliverable, not a nicety.

The raw download is not the wallpaper. Photographs of cars are lit to sell
cars: bright, saturated, high-contrast, with the subject dead centre. Left
alone they fight the UI. bin/grade-wallpaper.py does the cinematic treatment
that turns them into backgrounds.

Run:  python3 bin/fetch-wallpapers.py
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "backgrounds" / ".raw"

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = (
    "omarchy-theme-bavarian/1.0 "
    "(https://github.com/dhairyagabha/omarchy-theme-bavarian)"
)

# Licences we are willing to ship. Anything else is skipped, however good the
# photograph is.
FREE_LICENCES = re.compile(
    r"^(cc0|cc[- ]by([- ]sa)?([- ][\d.]+)?|public domain|pd|no restrictions)",
    re.IGNORECASE,
)

SEARCHES = [
    "Alpina B7",
    "Alpina B5",
    "Alpina XB7",
    "BMW Alpina B4",
    "BMW Alpina B3",
    "Alpina D5",
    "Alpina B6",
]

MIN_WIDTH = 2400
MIN_ASPECT = 1.45  # landscape enough to crop to 16:9 without losing the car
TARGET_WIDTH = 3840  # the render width we ask Commons for


def api(params: dict, attempts: int = 5) -> dict:
    """Call the Commons API with polite backoff on rate limiting."""
    params = {**params, "format": "json"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    delay = 2.0
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # noqa: BLE001 - retry anything transient
            if attempt == attempts:
                print(f"    ! giving up: {exc}", file=sys.stderr)
                return {}
            print(f"    . retry {attempt}/{attempts} in {delay:.0f}s ({exc})")
            time.sleep(delay)
            delay *= 2
    return {}


def strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", value or "")).strip()


def search(term: str, limit: int = 20) -> list[str]:
    data = api({
        "action": "query", "list": "search", "srsearch": term,
        "srnamespace": "6", "srlimit": str(limit),
    })
    return [r["title"] for r in data.get("query", {}).get("search", [])]


def image_info(titles: list[str]) -> list[dict]:
    """Resolve titles to URL, dimensions and licence metadata."""
    out = []
    for i in range(0, len(titles), 10):  # keep each request small
        data = api({
            "action": "query", "prop": "imageinfo",
            "iiprop": "url|size|extmetadata",
            "titles": "|".join(titles[i:i + 10]),
        })
        for page in data.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [{}])[0]
            if not info.get("url"):
                continue
            meta = info.get("extmetadata", {})
            out.append({
                "title": page["title"],
                "url": info["url"],
                "descriptionurl": info.get("descriptionurl", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "licence": strip_html(meta.get("LicenseShortName", {}).get("value", "")),
                "artist": strip_html(meta.get("Artist", {}).get("value", "")),
            })
        time.sleep(1.0)  # be a good API citizen
    return out


def acceptable(item: dict) -> tuple[bool, str]:
    if not FREE_LICENCES.match(item["licence"]):
        return False, f"licence {item['licence'] or 'unknown'!r}"
    if item["width"] < MIN_WIDTH:
        return False, f"too small ({item['width']}px)"
    if not item["height"] or item["width"] / item["height"] < MIN_ASPECT:
        return False, f"not landscape enough ({item['width']}x{item['height']})"
    return True, ""


def slug(title: str) -> str:
    name = title.removeprefix("File:").rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def download(item: dict, dest: Path) -> bool:
    """
    Pull a scaled render rather than the original.

    Commons rate-limits bulk fetches of full-resolution originals and asks
    clients to use the thumbnail sizes instead. We only ever need 4K, and the
    originals run to 30MB+, so Special:FilePath with an explicit width is both
    the polite route and the one that gives us the file we actually want.
    """
    filename = urllib.parse.quote(item["title"].removeprefix("File:").replace(" ", "_"))
    url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{filename}?width={TARGET_WIDTH}"
    delay = 3.0
    for attempt in range(1, 4):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            if len(data) < 50_000:  # an error page, not a photograph
                raise ValueError(f"suspiciously small response ({len(data)} bytes)")
            dest.write_bytes(data)
            return True
        except Exception as exc:  # noqa: BLE001
            if attempt == 3:
                print(f"    ! download failed: {exc}", file=sys.stderr)
                return False
            print(f"    . retry {attempt}/3 in {delay:.0f}s")
            time.sleep(delay)
            delay *= 2
    return False


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    seen: dict[str, dict] = {}
    for term in SEARCHES:
        print(f"searching: {term}")
        titles = search(term)
        for item in image_info(titles):
            seen.setdefault(item["title"], item)
        time.sleep(1.0)

    print(f"\n{len(seen)} candidates found\n")

    kept = []
    for item in sorted(seen.values(), key=lambda i: -i["width"]):
        ok, why = acceptable(item)
        name = item["title"].removeprefix("File:")[:58]
        if not ok:
            print(f"  skip  {name:<60} {why}")
            continue
        dest = RAW / f"{slug(item['title'])}.jpg"
        if dest.exists():
            print(f"  have  {name:<60} {item['width']}x{item['height']}")
            kept.append({**item, "path": dest})
            continue
        print(f"  get   {name:<60} {item['width']}x{item['height']}  {item['licence']}")
        if download(item, dest):
            kept.append({**item, "path": dest})
        else:
            dest.unlink(missing_ok=True)  # never leave a half-written file behind
        time.sleep(1.0)

    manifest = RAW / "manifest.json"
    manifest.write_text(json.dumps(
        [{k: (str(v) if k == "path" else v) for k, v in i.items()} for i in kept],
        indent=2,
    ))
    print(f"\nkept {len(kept)} images -> {RAW}")
    print(f"manifest -> {manifest}")
    print("\nNext: python3 bin/grade-wallpaper.py")


if __name__ == "__main__":
    main()
