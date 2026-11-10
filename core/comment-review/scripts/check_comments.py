# -*- coding: utf-8 -*-
"""Deterministic checks over extracted comments.

Reads items.json from extract_comments.py and the host project's vocabulary.json.
Emits findings with severity "auto" (safe to apply mechanically) or "flag"
(attach to the item for the reviewer). Also attaches findings into a copy of
items.json so the reviewer sees them.

Checks
- vocabulary: entries that have a "pattern" (regex over the comment text)          -> flag
- field-inline-comment: a // comment above a field (should be /// <summary>)       -> auto
- summary-period: a summary must end with "."                                      -> auto
- no-period: // comments and Tooltip text must not end with "."                    -> auto
- method-first-sentence: a method summary opens with a 합니다체 sentence
  or is "X Implementation."                                                        -> flag
- noun-first-sentence: any other summary, // comment or Tooltip opens with a noun phrase -> flag
- missing-class-summary: a class in a changed file without a summary
  (constant groups excluded)                                                       -> flag

usage: check_comments.py --project <dir> --items items.json [--vocabulary <relative path>] --out findings.json
"""
import argparse, json, os, re, sys

DEFAULT_VOCAB = "Documents/Development/Conventions/Comments/vocabulary.json"
CLASS_DECL = re.compile(r"^\s*(public|internal|private|protected)?\s*(static |abstract |sealed |partial )*class\s+\w+")
TAGS = re.compile(r"</?para>")


def vocabulary_rules(vocab):
    rules = []
    for e in vocab.get("entries", []):
        if not e.get("pattern"):
            continue
        rules.append({"regex": re.compile(e["pattern"]), "avoid": e["avoid"], "use": e.get("use"), "when": e.get("when", "")})
    return rules


def is_constant_group(file, decl):
    """A nested static class inside a constants container. Its summary is optional."""
    return file.endswith("Constants.cs") and "static class" in decl and "partial" not in decl


def plain_lines(text):
    return [l.strip() for l in TAGS.sub("", text).splitlines() if l.strip()]


def first_sentence(line):
    m = re.match(r"(.+?[.])(\s|$)", line)
    return m.group(1) if m else line


def check_item(it, rules):
    out = []
    text = it["text"]
    lines = plain_lines(text)
    if not lines:
        return out
    first, last = first_sentence(lines[0]), lines[-1]
    for r in rules:
        m = r["regex"].search(text)
        if m:
            out.append({"rule": "vocabulary", "severity": "flag", "match": m.group(0), "avoid": r["avoid"], "use": r["use"], "when": r["when"]})
    if it["kind"] == "inline" and it["member"] == "field":
        out.append({"rule": "field-inline-comment", "severity": "auto", "fix": "convert to /// <summary>"})
    if it["kind"] == "summary":
        if not last.endswith("."):
            out.append({"rule": "summary-period", "severity": "auto", "fix": "append '.'"})
        sentence = first.rstrip(".")
        if it["member"] == "method":
            if not (sentence.endswith("니다") or sentence.endswith(" Implementation")):
                out.append({"rule": "method-first-sentence", "severity": "flag", "expected": "합니다체 or 'X Implementation.'"})
        elif sentence.endswith("니다"):
            out.append({"rule": "noun-first-sentence", "severity": "flag", "expected": "noun phrase"})
    if it["kind"] in ("inline", "tooltip"):
        if last.endswith("."):
            out.append({"rule": "no-period", "severity": "auto", "fix": "drop trailing '.'"})
        if first.rstrip(".").endswith("다"):
            out.append({"rule": "noun-first-sentence", "severity": "flag", "expected": "noun phrase"})
    return out


def missing_class_summaries(project, files):
    out = []
    for rel in files:
        path = os.path.join(project, rel)
        if not os.path.isfile(path):
            continue
        lines = open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n")
        for i, line in enumerate(lines):
            if CLASS_DECL.match(line):
                if is_constant_group(rel, line):
                    continue
                k = i - 1
                while k >= 0 and lines[k].strip().startswith("["):
                    k -= 1
                if k < 0 or "</summary>" not in lines[k]:
                    out.append({"rule": "missing-class-summary", "severity": "flag", "file": rel, "line": i + 1, "decl": line.strip()[:100]})
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--items", required=True)
    p.add_argument("--vocabulary", default=DEFAULT_VOCAB)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    data = json.load(open(a.items, encoding="utf-8"))
    vocab_path = os.path.join(a.project, a.vocabulary)
    vocab = json.load(open(vocab_path, encoding="utf-8")) if os.path.isfile(vocab_path) else {"entries": []}
    rules = vocabulary_rules(vocab)

    findings = []
    for it in data["items"]:
        fs = check_item(it, rules)
        it["findings"] = fs
        for f in fs:
            findings.append(dict(f, item=it["id"], file=it["file"], line=it["line"]))
    findings += missing_class_summaries(a.project, data["files"])

    json.dump(data, open(a.items, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"findings": findings}, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    auto = sum(1 for f in findings if f["severity"] == "auto")
    flag = len(findings) - auto
    print(f"{auto} auto, {flag} flag -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
