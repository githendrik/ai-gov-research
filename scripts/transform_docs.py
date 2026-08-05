#!/usr/bin/env python3
"""
transform_docs.py — Build-time transformer for the AI Governance Weekly site.

Reads verbatim source markdown from docs/*.md and writes Hugo-ready markdown
to content/posts/*.md with:
  - YAML frontmatter injected (title, date, draft=false, tags, source)
  - title promoted from the first `# ` line (and that line removed from body)
  - date parsed from the leading YYYY-MM-DD in the filename
  - bracketed citation markers like [68] or [77][93] rewritten as <sup>68</sup> / <sup>77,93</sup>
  - empty YAML fields gracefully omitted

The source /docs/ directory is never modified; this script only writes to
content/posts/. Re-running is idempotent (overwrites prior output).

Usage:
    python3 scripts/transform_docs.py           # one-shot
    python3 scripts/transform_docs.py --watch  # re-run on docs/ change

Designed to run as part of the Vercel build command:
    python3 scripts/transform_docs.py && hugo --minify --gc
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "docs"
OUT_DIR = REPO_ROOT / "content" / "posts"
IMAGES_DIR = REPO_ROOT / "assets" / "images"

# --- Patterns ---------------------------------------------------------------

# Match a leading date in the filename: 2026-08-04-ai-governance.md -> 2026-08-04
FILENAME_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[-_]?")

# Match the first H1 line in the body. Group 1 = the title text.
H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)

# Match a run of consecutive [NN] citation markers at the same position.
# e.g. [68] -> ("68",), [77][93] -> ("77","93"), [10][132] -> ("10","132")
CITATION_RUN_RE = re.compile(r"(?:\[(\d+)\]){1,}")


def parse_date_from_filename(stem: str) -> dt.date | None:
    m = FILENAME_DATE_RE.match(stem)
    if not m:
        return None
    try:
        return dt.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def extract_title(body: str) -> tuple[str | None, str]:
    m = H1_RE.search(body)
    if not m:
        return None, body
    title = m.group(1).strip()
    # Remove that exact H1 line from the body so the theme's own title (rendered
    # from frontmatter) doesn't duplicate it.
    new_body = body[: m.start()] + body[m.end() + 1 :]
    # Trim leading blank lines left behind by removing the H1.
    new_body = new_body.lstrip("\n")
    return title, new_body


def rewrite_citations(body: str) -> str:
    def _to_sup(m: re.Match) -> str:
        nums = [g for g in m.groups() if g is not None]
        if not nums:
            return m.group(0)
        joined = ",".join(nums)
        return f"<sup>{joined}</sup>"

    # Two-pass: first collapse adjacent [N][N] blocks, then convert each to <sup>.
    # We match a maximal run of [NN] groups and emit a single <sup>...</sup>.
    return CITATION_RUN_RE.sub(_to_sup, body)


def build_frontmatter(
    title: str | None,
    date: dt.date | None,
    stem: str,
    extra_tags: list[str] | None = None,
) -> str:
    lines = ["---"]
    if title:
        safe_title = title.replace('"', '\\"')
        lines.append(f'title: "{safe_title}"')
    if date:
        lines.append(f"date: {date.isoformat()}")
    lines.append("draft: false")
    lines.append(f"slug: {stem}")
    tags = ["governance"] + (extra_tags or [])
    if tags:
        lines.append("tags: [{}]".format(", ".join(tags)))
    lines.append(f"source: {stem}.md")
    # Hero image: check for matching PNG in assets/images/
    image_path = IMAGES_DIR / f"{stem}.png"
    if image_path.exists():
        lines.append(f"image: /images/{stem}.png")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def transform_file(src: Path, out_dir: Path) -> str:
    stem = src.stem
    date = parse_date_from_filename(stem)
    raw = src.read_text(encoding="utf-8")
    title, body = extract_title(raw)
    body = rewrite_citations(body)
    fm = build_frontmatter(title or stem, date, stem)
    transformed = fm + body
    if not transformed.endswith("\n"):
        transformed += "\n"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / src.name
    out_path.write_text(transformed, encoding="utf-8")
    return out_path.name


def run_once() -> int:
    if not SRC_DIR.is_dir():
        print(f"error: source dir {SRC_DIR} not found", file=sys.stderr)
        return 1
    out_files: list[str] = []
    for src in sorted(SRC_DIR.glob("*.md")):
        if src.name.startswith("."):
            continue
        name = transform_file(src, OUT_DIR)
        out_files.append(name)
        print(f"  transformed: {src.name} -> content/posts/{name}")
    if not out_files:
        print("warning: no markdown files found in docs/", file=sys.stderr)
    return 0


def run_watch(poll_seconds: float = 2.0) -> int:
    import time

    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class _Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith(".md"):
                    run_once()

        observer = Observer()
        observer.schedule(_Handler(), str(SRC_DIR), recursive=False)
        observer.start()
        print(f"watching {SRC_DIR} for changes (Ctrl-C to stop)...")
        try:
            while True:
                time.sleep(poll_seconds)
        except KeyboardInterrupt:
            pass
        observer.stop()
        observer.join()
        return 0
    except ImportError:
        print(
            "warning: 'watchdog' not installed; falling back to polling",
            file=sys.stderr,
        )
        last_mtimes: dict[Path, float] = {}
        run_once()
        try:
            while True:
                time.sleep(poll_seconds)
                changed = False
                for src in SRC_DIR.glob("*.md"):
                    mtime = src.stat().st_mtime
                    if last_mtimes.get(src) != mtime:
                        last_mtimes[src] = mtime
                        changed = True
                if changed:
                    run_once()
        except KeyboardInterrupt:
            return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if __doc__ else "")
    ap.add_argument("--watch", action="store_true", help="re-run on docs/ changes")
    args = ap.parse_args(argv)
    if args.watch:
        return run_watch()
    return run_once()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
