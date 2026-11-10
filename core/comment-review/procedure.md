# Comment review procedure

Tool-agnostic. Any adapter (a skill in an agent runtime, a script, a human) follows the same steps. Rules about *what a good comment looks like* are never written here; they live in the host project's convention documents (see `README.en.md` in this directory, "What the host project provides").

## Inputs

- A diff: working tree against a base ref (default `HEAD`), or a commit range.
- Host documents: the comment section of the coding convention, `vocabulary.json`, `decisions.json`.

## Steps

1. **Extract every new or changed comment mechanically** from the diff with `scripts/extract_comments.py`. Never build the list from memory. The list covers XML summaries, inline `//` comments and `[Tooltip]` strings, with the previous text when the comment existed before.
2. **Run deterministic checks** with `scripts/check_comments.py`. Findings marked `auto` are applied without asking (for example a `//` comment above a field becomes a `/// <summary>`). Findings marked `flag` are attached to the item they concern so the reviewer sees them.
3. **Classify and propose** (reviewer step, in a fresh context): for each item decide
   - `prec` (precedent applied): the text follows a documented pattern or an existing example. Name the precedent in `note`.
   - `judge` (judgment needed): new wording, a vocabulary choice, a sentence the convention does not settle.
   Every item, of either kind, gets options `a` (the text as written), `b` (a real alternative; more than one is fine as `b`, `c`), `d` (delete), and one recommendation. An item without a real alternative is a process failure.
4. **Present for review** (adapter step): judgment items first, precedent items collapsed, each with the previous text (or "new"), the code context, the options and a place for a note. How the items are shown and where the choices are stored is up to the adapter; it must be able to read the choices back.
5. **Apply and verify**: apply the chosen texts, then verify each by searching the file. Report only what the search confirms.
6. **Record** the round with `scripts/record_decisions.py`: metrics (`auto`, `asked`, `overturned`) and every item where the choice differed from `a` or carried a comment. When the same judgment appears in two rounds, promote it to `vocabulary.json` or to the convention document.

## Item format

| Field | Meaning |
|---|---|
| `kind` | `judge` or `prec` |
| `prev` | The comment text before this change, or `null` when the comment is new |
| `options[a]` | Exactly the text now in the code |
| `options[b..]` | Alternatives that differ in substance, not punctuation |
| `options[d]` | Delete |
| `rec` | The recommended key |
| `note` | For `prec`: which precedent. For `judge`: why it needs a decision |

## Metrics

- `auto`: findings applied without asking
- `asked`: items shown to the reviewer
- `overturned`: items where the chosen key differs from `rec`

The goal is `asked` falling while `overturned` stays low. `overturned` rising means the recommendations drift from the house style and the reviewer prompt or the convention needs work.
