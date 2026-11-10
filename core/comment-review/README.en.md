# Comment review

[한국어](README.md)

A workflow that reviews new or changed code comments against the host project's convention.

In a long session, review quality erodes. Items get skipped, settled questions are asked again, and "applied" is reported from memory. Each step below removes one of those failure points.

## Steps

1. **Extract.** A script lists every new or changed comment in the diff. Nothing is collected from memory.
2. **Check.** A script applies the mechanical rules and fixes what needs no judgment.
3. **Propose.** A reviewer with a fresh context reads the host project's convention, vocabulary and past decisions. Each comment gets the current text, at least one real alternative, a delete option and a recommendation.
4. **Review.** The adapter shows each item with its previous text and the surrounding code. The user picks an option or leaves a note.
5. **Apply.** The choices are written to the files, and each one is verified by searching for the new text.
6. **Record.** The round is appended to the host project's decision file with three counts: fixed automatically, asked, and chosen against the recommendation.

The aim is for "asked" to fall over time while "chosen against the recommendation" stays low.

## Contents

| File | Role |
|---|---|
| `procedure.md` | The definition of the steps. Adapters follow it as written |
| `reviewer-prompt.md` | The instructions for the reviewer in step 3 |
| `scripts/extract_comments.py` | Step 1. Extracts comments from the diff |
| `scripts/check_comments.py` | Step 2. Checks the mechanical rules |
| `scripts/record_decisions.py` | Step 6. Records the round |
| `scripts/inject_rules.py` | Prints the comment section of the convention, to put the rules back after the context is compacted |

## What the host project provides

| File | Role |
|---|---|
| `Documents/Development/Conventions/CodingConvention.md` | The coding convention. The comment section is the `##` heading that contains `주석` |
| `Documents/Development/Conventions/Comments/vocabulary.json` | Words to use and words to avoid |
| `Documents/Development/Conventions/Comments/decisions.json` | Past review rounds |

`vocabulary.json` is a list of entries. An entry with a `pattern` is checked by script; one without is left to the reviewer.

```json
{
  "entries": [
    { "use": "return", "avoid": ["give back"], "pattern": "gives? back|gave back" },
    { "use": "fetch", "avoid": ["get"], "when": "remote data" }
  ]
}
```

`decisions.json` starts as `{ "rounds": [] }`. The record step appends to it.

Also needed: git, and Python 3 on `PATH` as `python` (tested with 3.14).

## Limitations

- Only C# is parsed: XML summaries, `//` comments and `[Tooltip]` strings.
- `scripts/check_comments.py` hardcodes a few checks instead of reading them from the host project. A summary ends with a period, while `//` comments and Tooltip text do not. A method summary opens with a Korean 합니다체 sentence or is `X Implementation.`, and other summaries open with a noun phrase. A nested static class in a file named `*Constants.cs` may go without a summary.
- The paths in the table above are the scripts' defaults. The scripts take other paths as arguments, but there is no way yet to configure them per project.

A project with different rules has to edit the script until these checks move into a file on the host project's side.
