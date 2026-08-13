"""
The dashboard's static assets.

No build step, no npm, no framework. Three files shipped in the package and served
by the Phase 9 API — which means the dashboard is subject to the same rule as
every other surface: it reads through `/api/v1`, and it cannot reach an engine or
the store even if someone wanted it to. A browser has no other way in.

That constraint is why there is no sample data anywhere in here. A dashboard with
a fixture behind a view renders beautifully while the thing it claims to show is
broken, which is the exact failure this product exists to name.
"""

from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parent

# Only these are servable. A path that is not on this list does not resolve,
# so the asset route cannot be walked into a file read.
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
}


def resolve(path):
    """(bytes, content_type) for a servable path, or None."""
    entry = ASSETS.get(path)
    if not entry:
        return None
    name, content_type = entry
    file_path = ASSET_DIR / name
    if not file_path.is_file():
        return None
    return file_path.read_bytes(), content_type


def available():
    return all((ASSET_DIR / name).is_file() for name, _ in ASSETS.values())
