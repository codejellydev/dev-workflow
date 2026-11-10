# -*- coding: utf-8 -*-
"""Extract every new or changed comment from a git diff of C# files.

Compares the working tree (or a commit range) against a base ref and lists
XML summary blocks, inline // comments and [Tooltip] strings that were added
or whose text changed. The previous text is attached when the comment existed
before, matched by the declaration or code line it belongs to.

usage: extract_comments.py --project <dir> [--base HEAD | --range A..B] [--include <glob>] --out items.json
"""
import argparse, json, os, re, subprocess, sys

SUMMARY_OPEN = "/// <summary>"


def run_git(project, args):
    r = subprocess.run(["git"] + args, cwd=project, capture_output=True)
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def top_level_separator(d):
    """Position and kind of the first "=>" or "=" outside parentheses and brackets, or (None, None)."""
    depth = 0
    for i, c in enumerate(d):
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "=" and depth == 0:
            if d[i:i + 2] == "=>":
                return i, "=>"
            if d[i:i + 2] != "==" and d[i - 1:i] not in ("=", "!", "<", ">"):
                return i, "="
    return None, None


def classify_decl(decl):
    d = decl.strip()
    if re.search(r"\b(class|struct|interface|enum|delegate)\s+\w+", d.split("(")[0]):
        return "type"
    if re.match(r"^[A-Z][A-Za-z0-9_]*\s*(=\s*-?\w+)?,?$", d):
        return "enum-member"
    # The part before a body or an initializer decides the kind: a method's ends with its parameter list.
    index, separator = top_level_separator(d)
    head = (d[:index] if index is not None else d).rstrip(" ;{")
    if not d.startswith("[") and (head.endswith(")") or head.endswith("(") or re.search(r"\)\s*where\b", head)):
        return "method"
    if separator == "=" and "{" not in d[:index]:
        return "field"
    if "{" in d or separator == "=>":
        return "property"
    if re.search(r"\b(const|readonly|private|protected|internal|public)\b", d) and d.endswith(";"):
        return "field"
    return "other"


def norm(s):
    return re.sub(r"\s+", " ", s.strip())


def parse(text):
    """Return a dict key -> item for every comment in a C# source text."""
    lines = text.replace("\r\n", "\n").split("\n")
    items = {}
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s == SUMMARY_OPEN:
            body = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("///") and "</summary>" not in lines[j]:
                body.append(lines[j].strip()[3:].strip())
                j += 1
            k = j + 1
            while k < len(lines) and (lines[k].strip().startswith("///") or lines[k].strip().startswith("[")):
                k += 1
            decl = lines[k].strip() if k < len(lines) else ""
            key = "summary|" + norm(decl)
            items[key] = {"kind": "summary", "member": classify_decl(decl), "decl": decl[:120], "text": "\n".join(body), "line": i + 1}
            i = j
        elif s.startswith("// ") or s == "//":
            nxt_i = i + 1
            while nxt_i < len(lines) and lines[nxt_i].strip().startswith("//"):
                nxt_i += 1
            nxt = lines[nxt_i].strip() if nxt_i < len(lines) else ""
            body = [lines[n].strip()[2:].strip() for n in range(i, nxt_i)]
            member = "field" if (nxt.startswith("[") or (re.match(r"^(private|public|protected|internal)\b", nxt) and nxt.endswith(";"))) else "statement"
            key = "inline|" + norm(nxt) + "|" + str(sum(1 for kk in items if kk.startswith("inline|" + norm(nxt) + "|")))
            items[key] = {"kind": "inline", "member": member, "decl": nxt[:120], "text": "\n".join(body), "line": i + 1}
            i = nxt_i - 1
        m = re.search(r'\[Tooltip\("(.+?)"\)\]', s)
        if m:
            k = i + 1
            while k < len(lines) and lines[k].strip().startswith("["):
                k += 1
            decl = lines[k].strip() if k < len(lines) else ""
            key = "tooltip|" + norm(decl)
            items[key] = {"kind": "tooltip", "member": "field", "decl": decl[:120], "text": m.group(1), "line": i + 1}
        i += 1
    return items


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--base", default="HEAD")
    p.add_argument("--range", dest="rng", default=None, help="A..B instead of working tree vs base")
    p.add_argument("--include", default="*.cs")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if a.rng:
        old_ref, new_ref = a.rng.split("..", 1)
        names = run_git(a.project, ["diff", "--name-only", "--diff-filter=AM", a.rng, "--", a.include]) or ""
    else:
        old_ref, new_ref = a.base, None
        names = run_git(a.project, ["diff", "--name-only", "--diff-filter=AM", a.base, "--", a.include]) or ""
        untracked = run_git(a.project, ["ls-files", "--others", "--exclude-standard", "--", a.include]) or ""
        names = names + "\n" + untracked

    files = sorted(set(n.strip().replace("\\", "/") for n in names.split("\n") if n.strip()))
    items = []
    for rel in files:
        if new_ref:
            new_text = run_git(a.project, ["show", f"{new_ref}:{rel}"])
            if new_text is None:
                continue
        else:
            path = os.path.join(a.project, rel)
            if not os.path.isfile(path):
                continue
            new_text = open(path, encoding="utf-8").read()
        old_text = run_git(a.project, ["show", f"{old_ref}:{rel}"]) or ""
        new_items, old_items = parse(new_text), parse(old_text)
        for key, it in new_items.items():
            prev = old_items.get(key)
            if prev is not None and prev["text"] == it["text"]:
                continue
            items.append({"id": len(items) + 1, "file": rel, "line": it["line"], "kind": it["kind"], "member": it["member"],
                          "decl": it["decl"], "text": it["text"], "prev": prev["text"] if prev else None, "findings": []})

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump({"base": a.rng or a.base, "files": files, "items": items}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{len(items)} comment(s) in {len(files)} file(s) -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
