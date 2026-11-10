# dev-workflow

[한국어](README.md)

A repository for work procedures that run through AI coding tools, managed outside the projects that use them.

Rules stay in the project: the convention documents and the data that goes with them. Procedures stay here: what to collect, how to present it, and where to record the outcome. Switching tools leaves the project as it is, and a different project runs the same procedure.

## Terms

| Term | Meaning |
|---|---|
| Workflow | The procedure for one kind of work. It does not know which tool runs it |
| Adapter | The part that lets one tool run the workflows. It does not change a procedure |
| Host project | The project a workflow runs in. The rules and the data are there |

## Workflows

| Workflow | What it does |
|---|---|
| [Comment review](core/comment-review/README.en.md) | Extracts every new or changed comment in the diff, checks it, proposes alternatives with a recommendation for each, and takes the user's choice |

## Adapters

| Tool | Location | Entry point |
|---|---|---|
| Claude Code | `claude/` | `/dev-workflow:comment-review` |

## Install (Claude Code)

```
/plugin marketplace add codejellydev/dev-workflow
/plugin install dev-workflow@dev-workflow --scope local
```

`--scope local` enables the plugin for the current project only. Users without a GitHub SSH key set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` first.

The session must be able to publish artifacts, because the review page of comment review stores the choices there.

For development, run `claude --plugin-dir <path to this repo>` and `/reload-plugins` after edits.

## Layout

| Location | Contents |
|---|---|
| `core/<workflow>/` | Procedure, prompts and scripts. Tool-agnostic |
| `claude/` | The Claude Code adapter: skills, agents, hooks and the review page |
| `projects/<name>/` | Adapters for a single project. Empty for now |

The repository root is also a Claude Code marketplace that publishes the `dev-workflow` plugin.

## Extending

**Adding a workflow**

1. Create `core/<name>/` and write the procedure in `procedure.md`. Do not name a tool or rely on one tool's features.
2. Put the steps that need no judgment in `scripts/`.
3. Write what the host project provides, and the limitations, in `README.md`.
4. Add an entry point for the workflow to each adapter.

**Adding an adapter**

1. Create a directory at the root, named after the tool.
2. For each workflow, add an entry point that follows `procedure.md` as written.
3. Implement the steps that show items to the user and take a choice with that tool's own means.

Rules are written in neither a workflow nor an adapter. A rule that is needed is read from the host project's documents. Current exceptions are listed under each workflow's limitations.

## License

MIT. See `LICENSE`.
