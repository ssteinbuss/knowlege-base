#!/usr/bin/env python3
"""
Concatenate and rewrite summary files into docs/SUMMARY.md for mkdocs-literate-nav.

Rules:
- Order: rulebook -> ram5 -> handbook
- Insert H2 headings between summaries
- Rewrite links so they point to:
  external/rulebook/...   (for rulebook)
  external/ram5/...
  external/handbook/...
- Preserve anchor fragments (#...).
- Preserve external URLs (http/https/mailto) unchanged.
- Handle relative forms: "foo.md", "./foo.md", "../bar/baz.md".
Algorithm:
- For each link (path[#frag]?), compute normalized path relative to that source root.
- New link = f"external/{section}/{normalized_relpath}" + (anchor if any).
- Only rewrite links that are relative (no scheme and not starting with '#').
- Write a final SUMMARY.md with top-level sections: Home, Knowledge (with three subsections), About.
"""
import os
import posixpath
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
OUT_FILE = DOCS_DIR / "SUMMARY.md"

ORDER = ["rulebook", "ram5", "handbook"]
TITLE_MAP = {
    "rulebook": "Rulebook",
    "ram5": "RAM 5",
    "handbook": "Organizational Handbook",
}

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

def is_external(link: str) -> bool:
    return link.startswith("http://") or link.startswith("https://") or link.startswith("mailto:")

def rewrite(link: str, src_root: Path, section: str) -> str:
    # Preserve external and anchor-only links
    if is_external(link) or link.startswith("#"):
        return link
    # Split anchor
    if "#" in link:
        path_part, anchor = link.split("#", 1)
        anchor = "#" + anchor
    else:
        path_part, anchor = link, ""

    # Normalize relative path against src_root
    # Use POSIX separators for MkDocs links
    abs_path = (src_root / path_part).resolve()
    try:
        rel_in_source = abs_path.relative_to(src_root.resolve())
    except ValueError:
        # If it escapes src_root via .., keep as-is (best-effort)
        return link

    # Build new path
    new_path = posixpath.join("external", section, *rel_in_source.parts)
    return new_path + anchor

def process_summary(section: str, src_root: Path, summary_path: Path) -> str:
    lines = summary_path.read_text(encoding="utf-8").splitlines()
    out_lines = []
    for line in lines:
        def repl(m):
            text, url = m.group(1), m.group(2)
            new_url = rewrite(url, src_root, section)
            return f"[{text}]({new_url})"
        out_lines.append(LINK_RE.sub(repl, line))
    return "\n".join(out_lines).strip() + "\n"

def main():
    # Parse args triplets: key|src_root|summary_path
    args = sys.argv[1:]
    triplets = {}
    for a in args:
        key, src_dir, summ = a.split("|", 2)
        triplets[key] = (Path(src_dir), Path(summ))

    # Compose OUTPUT
    parts = []
    parts.append("# Home\n")
    parts.append("- [Home](index.md)\n")

    parts.append("\n# Knowledge\n")
    for key in ORDER:
        if key not in triplets:
            # still include empty header for deterministic nav
            parts.append(f"\n## {TITLE_MAP[key]}\n\n- *(content not available)*\n")
            continue
        src_root, summ = triplets[key]
        parts.append(f"\n## {TITLE_MAP[key]}\n\n")
        parts.append(process_summary(key, src_root, summ))

    parts.append("\n# About\n")
    parts.append("- [About](about.md)\n")

    OUT_FILE.write_text("".join(parts), encoding="utf-8")
    print(f"[INFO] Wrote merged SUMMARY to {OUT_FILE}")

if __name__ == "__main__":
    main()