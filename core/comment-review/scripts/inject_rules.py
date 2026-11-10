# -*- coding: utf-8 -*-
"""Print the comment section of the host project's coding convention.

Meant for a SessionStart(compact) hook so the rules return to context after
compaction. Prints nothing when the project has no such document.

usage: inject_rules.py --project <dir> [--convention <relative path>] [--section <heading substring>]
"""
import argparse, os, sys

DEFAULT_CONVENTION = "Documents/Development/Conventions/CodingConvention.md"


def section_text(markdown, heading_substring):
    lines = markdown.replace("\r\n", "\n").split("\n")
    start = None
    for i, line in enumerate(lines):
        if line.startswith("## ") and heading_substring in line:
            start = i
            break
    if start is None:
        return ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--convention", default=DEFAULT_CONVENTION)
    p.add_argument("--section", default="주석")
    a = p.parse_args()
    path = os.path.join(a.project, a.convention)
    if not os.path.isfile(path):
        return 0
    text = section_text(open(path, encoding="utf-8").read(), a.section)
    if not text:
        return 0
    sys.stdout.reconfigure(encoding="utf-8")
    print("Comment convention of this project (re-injected after compaction). Source: " + a.convention)
    print()
    print(text)
    print()
    print("Comment review runs through the comment review workflow; do not review comments from memory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
