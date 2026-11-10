---
name: comment-review
description: Review the comments added or changed in the current diff against the project's comment convention. Extracts every comment mechanically, applies deterministic fixes, has a fresh-context reviewer classify the rest, and presents a review page where the user picks a/b/d per item. Use only when the user asks for a comment review.
disable-model-invocation: true
---

# Comment review

Procedure: `${CLAUDE_PLUGIN_ROOT}/core/comment-review/procedure.md`. Follow it in this order. Do not skip the extraction or the recording step, and never build the item list from memory.

## Paths

- Project: `${CLAUDE_PROJECT_DIR}`
- Convention: `${CLAUDE_PROJECT_DIR}/Documents/Development/Conventions/CodingConvention.md` (the comment section is the `##` heading that contains "주석"; give that heading to the reviewer)
- Vocabulary: `${CLAUDE_PROJECT_DIR}/Documents/Development/Conventions/Comments/vocabulary.json`
- Decisions: `${CLAUDE_PROJECT_DIR}/Documents/Development/Conventions/Comments/decisions.json`
- Workflow scripts: `${CLAUDE_PLUGIN_ROOT}/core/comment-review/scripts/`
- Review page script: `${CLAUDE_PLUGIN_ROOT}/claude/scripts/review_page.py`
- Run directory: `${CLAUDE_PLUGIN_DATA}/comment-review/<round-id>/` (create it; it survives plugin updates)

Round id is `$1` if given, otherwise today's date (`YYYY-MM-DD`), with a numeric suffix when that run directory already exists. It only names the run directory and the review page; it is not written into the project. Base ref is `$2` if given, otherwise `HEAD` (working tree, staged and unstaged, against HEAD).

## Steps

1. **Extract**
   `python "${CLAUDE_PLUGIN_ROOT}/core/comment-review/scripts/extract_comments.py" --project "${CLAUDE_PROJECT_DIR}" --base <base-ref> --out <run>/items.json`
   If it reports zero items, say so and stop.

2. **Deterministic checks**
   `python "${CLAUDE_PLUGIN_ROOT}/core/comment-review/scripts/check_comments.py" --project "${CLAUDE_PROJECT_DIR}" --items <run>/items.json --out <run>/findings.json`
   Apply every finding with `"severity": "auto"` directly in the files (these are mechanical: comment form, trailing period). Then run step 1 again so `items.json` reflects the fixed text, and keep the count of applied fixes as `auto`.

3. **Reviewer** (fresh context)
   Launch the `comment-reviewer` subagent with a task message that gives the absolute paths of `items.json`, `findings.json`, the convention file and section heading, `vocabulary.json`, `decisions.json`, and the output path `<run>/spec.json`, plus the round id and a one-line title of the change. Wait for it. Do not classify items yourself in the main thread.

4. **Review page**
   `python "${CLAUDE_PLUGIN_ROOT}/claude/scripts/review_page.py" --project "${CLAUDE_PROJECT_DIR}" --spec <run>/spec.json --out <run>/review.html`
   The script refuses a spec where any item lacks `a`, an alternative, `d` or `rec`; if it refuses, send the subagent the error and have it fix the spec.
   Publish `review.html` with the Artifact tool, capabilities `{"db": {}}`, icon `checklist`. Tell the user: the link, how many judgment items and how many precedent items, and that choices save automatically. Then stop and wait; do not pick for the user.

5. **Apply**
   When the user says the review is done, read the choices with the ArtifactData tool (`list` on collection `reviews/<round-id>/items`), save them to `<run>/answers.json` as `{"<item id>": {"choice": "b", "comment": "..."}}`, and apply each choice to the files: `a` leaves the text, `b`/`c` replaces it with that option's text, `d` removes the comment block, a comment overrides the choice when it contains a sentence to use. Keep each file's line endings. Then verify every applied item by grepping for the new text and report only what the grep confirms. Items not answered count as `a`.

6. **Record**
   `python "${CLAUDE_PLUGIN_ROOT}/core/comment-review/scripts/record_decisions.py" --project "${CLAUDE_PROJECT_DIR}" --spec <run>/spec.json --items <run>/items.json --answers <run>/answers.json --auto <count from step 2>`
   Report the metrics it prints (`auto`, `asked`, `overturned`) and list any judgment that now appears in two rounds, as a candidate for `vocabulary.json` or the convention. Do not edit those two files without the user's go.

## Never

- Never commit or stage. The user owns git.
- Never present an item with only one option.
- Never report "applied" without the grep in step 5.
