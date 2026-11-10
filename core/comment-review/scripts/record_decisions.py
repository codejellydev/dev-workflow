# -*- coding: utf-8 -*-
"""Append a review round to the host project's decisions.json.

Takes the reviewer spec, the extracted items and the user's answers, computes the
metrics and records every item whose choice differed from "a" or carried a comment.
A round is identified by its date only; nothing from a task tracker is recorded.

usage: record_decisions.py --project <dir> --spec spec.json --items items.json --answers answers.json [--tool <name>] [--auto <n>] [--decisions <relative path>]
answers.json: {"<item id>": {"choice": "b", "comment": "..."}}
"""
import argparse, datetime, json, os, sys

DEFAULT_DECISIONS = "Documents/Development/Conventions/Comments/decisions.json"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--items", required=True)
    p.add_argument("--answers", required=True)
    p.add_argument("--tool", default="dev-workflow")
    p.add_argument("--auto", type=int, default=0)
    p.add_argument("--decisions", default=DEFAULT_DECISIONS)
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    spec = json.load(open(a.spec, encoding="utf-8"))
    comment_kind = {it["id"]: it["kind"] for it in json.load(open(a.items, encoding="utf-8"))["items"]}
    answers = json.load(open(a.answers, encoding="utf-8"))
    path = os.path.join(a.project, a.decisions)
    raw = open(path, encoding="utf-8", newline="").read() if os.path.isfile(path) else ""
    newline = "\r\n" if "\r\n" in raw else "\n"
    doc = json.loads(raw) if raw else {"rounds": []}

    items, asked, overturned = [], 0, 0
    for it in spec["items"]:
        ans = answers.get(str(it["id"])) or {}
        choice = ans.get("choice") or "a"
        comment = (ans.get("comment") or "").strip()
        if it["kind"] == "judge":
            asked += 1
        if choice != it["rec"]:
            overturned += 1
        if choice == "a" and not comment:
            continue
        chosen = None if choice == "d" else next((o["text"] for o in it["options"] if o["k"] == choice), None)
        items.append({"kind": comment_kind.get(it["id"], "summary"), "original": it["options"][0]["text"], "chosen": chosen,
                      "reason": comment or ("삭제" if choice == "d" else ""), "promoted": False})

    doc.setdefault("rounds", []).append({"date": datetime.date.today().isoformat(), "tool": a.tool,
                                         "auto": a.auto, "asked": asked, "overturned": overturned, "items": items})
    text = json.dumps(doc, ensure_ascii=False, indent=2).replace("\n", newline) + newline
    open(path, "w", encoding="utf-8", newline="").write(text)
    print(json.dumps({"auto": a.auto, "asked": asked, "overturned": overturned, "recorded": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
