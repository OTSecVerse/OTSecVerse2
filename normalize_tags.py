#!/usr/bin/env python3
"""
normalize_tags.py

Usage:
  python3 normalize_tags.py --dry-run
  python3 normalize_tags.py --apply
"""

import re
import sys
import argparse
from pathlib import Path
import yaml

# Patterns matching variants we want to unify:
VARIANT_RE = re.compile(r'^(online[\s\-_]?privacy)$', re.IGNORECASE)

# Canonical tag
CANONICAL = "online-privacy"

# File globs to check
GLOBS = ["_posts/**/*.md", "_posts/**/*.markdown", "**/*.md", "**/*.markdown"]

EXCLUDE_DIRS = {".git", "_site", ".jekyll-cache", "node_modules"}

def should_skip(path: Path):
    return any(part in EXCLUDE_DIRS for part in path.parts)

def load_front_matter(text: str):
    if not text.startswith("---"):
        return None, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text

    yaml_text = parts[1]
    body = parts[2]

    try:
        front = yaml.safe_load(yaml_text)
    except Exception:
        return None, text

    if not isinstance(front, dict):
        return None, text

    return front, body

def normalize_tags(tags_list):
    changed = False
    final = []

    for t in tags_list:
        if isinstance(t, str) and VARIANT_RE.match(t.strip()):
            final.append(CANONICAL)
            changed = True
        else:
            final.append(t)

    # remove duplicates
    final = list(dict.fromkeys(final))
    return final, changed

def process_file(p: Path):
    text = p.read_text(encoding='utf-8', errors='ignore')
    front, body = load_front_matter(text)

    if not front:
        return None

    tags = front.get("tags")
    if not tags or not isinstance(tags, list):
        return None

    new_tags, changed = normalize_tags(tags)
    if not changed:
        return None

    front["tags"] = new_tags

    # rebuild YAML
    new_yaml = yaml.safe_dump(front, sort_keys=False).strip()
    new_text = f"---\n{new_yaml}\n---\n{body.lstrip()}"

    return new_text, text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        args.dry_run = True  

    all_files = []
    for g in GLOBS:
        all_files.extend(Path(".").glob(g))

    changes = []

    for p in all_files:
        if not p.is_file() or should_skip(p):
            continue
        result = process_file(p)
        if result:
            changes.append((p, result[0], result[1]))

    if not changes:
        print("No files with tag variants found.")
        return 0

    for p, new, old in changes:
        print(f"Will update: {p}")

    if args.dry_run:
        print("\nDry-run only. Run with --apply to perform changes.")
        return 0

    # Apply
    for p, new, old in changes:
        bak = p.with_suffix(p.suffix + ".bak")
        bak.write_text(old, encoding="utf-8")
        p.write_text(new, encoding="utf-8")
        print(f"Updated {p} (backup: {bak})")

    print("\nDone.")
    return 0

if __name__ == "__main__":
    main()
