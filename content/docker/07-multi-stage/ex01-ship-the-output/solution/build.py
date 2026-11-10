"""Builds the site into site/. Like real build tools, it leaves a big cache behind."""

from pathlib import Path

pages = sorted(Path("pages").glob("*.txt"))
items = "".join(f"<li>{p.stem}: {p.read_text().strip()}</li>" for p in pages)
Path("site").mkdir(exist_ok=True)
Path("site/index.html").write_text(f"<h1>Field notes</h1><ul>{items}</ul>\n")

cache = Path("build-cache")
cache.mkdir(exist_ok=True)
(cache / "objects.bin").write_bytes(b"0" * 20_000_000)
print(f"built {len(pages)} pages")
