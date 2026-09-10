---
name: board
description: Operate a Multica board — read, create and update issues, and inspect agents, skills, projects and autopilots — from Claude Code, or from a Cowork/claude.ai session bridged to the machine that has the Multica desktop app. Use whenever a task touches a Multica workspace, or when a session needs to know the board exists at all.
---

# Operating a Multica board

Multica is an agentic project-management platform: issues on a board, agents that pick them
up, and a local daemon that runs those agents. The desktop app ships a CLI, and the CLI is the
only surface that sees more than one workspace at a time.

This skill is the operating manual: how to find the CLI, how to discover ids instead of
guessing them, which acts are safe for a session to perform on its own, and the gotchas that
have actually broken real sessions. Everything about the platform below was measured against
**CLI v0.4.42**; the CLI ships changes almost daily, so run `multica --version` and record it
alongside any claim you make about the surface.

## 1. Find the CLI

The binary is inside the desktop app, not on `PATH`. On macOS, `command -v multica` returns
nothing — that is expected, not a broken install.

```bash
M="${MULTICA_BIN:-/Applications/Multica.app/Contents/Resources/app.asar.unpacked/resources/bin/multica}"
[ -x "$M" ] || echo "set MULTICA_BIN to the multica binary"
```

Prefer the `MULTICA_BIN` environment variable over a hardcoded path — scripts in the wild
already read it, and it is the one knob that survives an app relocation.

## 2. Discover the profile and the workspaces — never hardcode ids

A profile isolates config, daemon state and credentials. The desktop app creates one; its
directory name is the profile name:

```bash
ls ~/.multica/profiles          # the profile names available on this machine
"$M" config show                # config file location and current values
```

Then let the CLI tell you what exists, rather than typing a UUID from memory:

```bash
P="${MULTICA_PROFILE:-<profile from the listing above>}"
"$M" --profile "$P" workspace list --output json    # -> [{id, name, slug}, ...]
```

Everything else is addressed from there:

```bash
WS=<workspace id from the listing>
mt(){ "$M" --profile "$P" --workspace-id "$WS" "$@"; }

mt agent list --output json      # ids, model, thinking_level, max_concurrent_tasks, runtime_id
mt project list --output json
mt skill list --output json
mt runtime list --output json    # runtime names, to resolve runtime_id
```

If the project keeps a versioned manifest of its Multica configuration (see §9), read the ids
from there instead — a manifest generated from the server is more trustworthy than a listing
you paged through by hand, and it is diffable.

`auth status` confirms who you are talking to. It prints a truncated credential: never paste
its output into a file, an issue, or a commit.

## 3. Two routes, and only one of them is direct

**From Claude Code on the machine with the desktop app** — run the CLI directly in the shell.
Nothing else is needed.

**From a Cowork or claude.ai session bridged to that machine** — the session's own shell runs
in a separate sandbox with only the connected folders mounted. It cannot see `/Applications`
and therefore cannot reach the CLI. The route that works is the bridge's shell on the user's
machine (on macOS, an AppleScript `do shell script "…"`). Three things bite there:

- Nested quoting breaks easily. Avoid `python3 -c` with inner quotes; write the output to a
  file inside a connected folder and read it from the sandbox.
- The AppleScript shell reports a non-zero exit as a tool error — even a `which` that finds
  nothing. End with `; echo done`, or `|| true`, when the exit code does not matter.
- The sandbox usually cannot delete files in connected folders. Clean up temporary files from
  the same bridge shell that created them.

If the desktop app is closed or offline, neither route exists. Say so and move on.

## 4. Safe defaults

These are conventions, not enforcement — the CLI will happily do all of them. Adopt them
unless the project says otherwise, and treat a deviation as something to confirm with a human
first.

1. **`--no-start` on every `issue status`.** Without it, moving an issue dispatches an agent
   run. A status change is bookkeeping; dispatching work is a decision.
2. **Do not comment on issues in `backlog`.** A backlog item has not been scoped yet; a
   comment there is written to nobody.
3. **Promotion is human.** Moving an issue out of `backlog` into the working column is the
   moment scope and rigor get fixed. Leave it to a person.
4. **Editing is not deploying.** `agent update`, `skill update`, `workspace update`,
   `project update` and `autopilot update` write to the live server. If the project versions
   its agent instructions and skills in git, a commit changes nothing until one of those runs.
   Never run them unprompted; propose the diff and stop.
5. **Never `create` a registry object casually.** A stray agent, skill or project is invisible
   debt — it will not appear in any manifest, and drift checks will not see it.
6. **Leave a trace.** Acts performed with a human's profile are indistinguishable from that
   human in `issue timeline`. When a session acts, say so in a dated note on the issue.
7. **No credentials in instruction, skill or context text.** That text is stored server-side
   and passed through process arguments.

## 5. Reading

```bash
mt issue list --status backlog --limit 100 --offset 0 --output json
mt issue get <ID> --output json
mt issue children <ID> --output json
mt issue comment list <ID> --roots-only --compact --output json
mt issue runs <ID>
mt issue property list <ID>
mt issue label list <ID>
mt workspace get --output json        # the rendered workspace context
```

Output shapes that do not match the obvious guess:

- `--limit` caps at **100**; the CLI refuses more and tells you to page with `--offset`.
- `issue children --output json` returns `{stages, total, unstaged}`, not an array. Iterate
  `.stages[]`; `.[]` will silently walk three heterogeneous values. Check
  `(.unstaged|length) == 0` before trusting a stage view.
- `issue comment list` returns a bare list, not `{comments: [...]}`. Comment bodies can carry
  raw control characters — strip them before parsing JSON.
- `autopilot get` wraps its payload in `{"autopilot": {...}}`; the other `get` commands do not.
- `status_category` collapses custom review statuses together; only `.status` distinguishes
  them, and `status_name` comes back empty for custom statuses inside `children`.
- `trigger_comment_id` exists only on runs of `kind: comment`. A `direct` run carries
  `attribution: issue_assignment` and `source: direct_human`; a run started by an agent on a
  human's behalf carries `source: delegation` with the human `initiator` preserved.
- There is no way to list runs globally: `multica run list` does not exist (the command is
  `runtime`), and `issue runs <ID>` is the only view.

## 6. Writing

```bash
mt issue create --title "…" --description-stdin --project <project id>
mt issue comment add <issue id> --content-stdin
mt issue comment add <issue id> --parent <comment id> --content-stdin
mt issue status <ID> in_progress --no-start
mt issue property set <ID> --name "<property name>" --value "<option name>"
mt issue label add <ID> <label id>
```

- `issue label add` takes the label as a **positional argument**; `--label-ids` does not exist.
  Create the issue first, then label it in a second call — a failed flag after creation leaves
  an unlabeled issue behind, not a clean rollback.
- `issue property set` uses `--name`, not `--property-id`, and `issue property unset` exists.
- `--parent` on creation does **not** inherit the parent's labels.
- `agent create --description` caps at 255 characters, and `--instructions` takes a string, not
  a file path.
- Commenting on a closed issue does not dispatch a run.
- Closing the last child of a stage generates a system comment that mentions the parent's
  assignee — which can wake an agent with no human gesture involved.

## 7. Shell gotchas that have cost real sessions

Mostly zsh, which is the default shell on macOS:

- **A variable holding several flags becomes one argument.** `"$M" $flags --help` fails. Use a
  function with `"$@"` — that is what `mt()` above is for — or drive the CLI from Python's
  `subprocess`.
- `for x in $VAR` iterates **once**. Use `${=VAR}` or a real array. This has silently produced
  batches of issues carrying an invalid `--workspace a b` argument.
- zsh arrays are **1-indexed**: `${A[0]}` is empty, which is how an issue gets created with a
  blank field.
- `pipestatus` is lowercase in zsh, and `EXIT=$?` after a pipeline measures the *last* command
  of the pipeline: `bash script | tail` gives you `tail`'s exit code.
- Agent shells often abort on the first non-zero exit. Guard commands whose non-zero exit is
  a normal outcome (a drift check that exits 1 on "differs") with `|| true` or `set +e`.
- BSD grep on macOS does not understand `\s` — use `[[:space:]]` — and `--include=*.md` needs
  quoting in zsh.

## 8. What the platform does not do

- **Workspace isolation is real.** An agent running in one workspace cannot read another. Only
  a human profile's CLI sees all of them, so cross-workspace search, cross-workspace
  dependencies and any portfolio-wide view exist *only* through the CLI. When you write
  anything that governs agents, ask whether it assumes an agent can see a neighbouring
  workspace — if it does, that is a defect.
- **Agents cannot produce artifacts.** In an agent task the artifact tool is disabled, and the
  refusal is explicit: `Artifact is disabled for this session, in subagents as well as here`.
  Delegating to a subagent does not work around it. To deliver something visual through the
  board, attach a file to a comment.
- **There is no MCP surface.** The v0.4.42 command tree is `agent`, `autopilot`, `chat`,
  `issue`, `label`, `project`, `property`, `repo`, `skill`, `squad`, `workspace`, `daemon`,
  `runtime`, `attachment`, `auth`, `config`, `login`, `setup`, `update`, `user`, `version`.
  Anything MCP-shaped has to wrap this binary, which means it inherits the machine and the
  profile it runs under.

## 9. Project conventions

A team operating Multica seriously usually keeps its agent instructions, workspace skills,
workspace context and project descriptions versioned in a repository, and deploys them to the
server through the CLI. When that repository exists, it — not this skill — is the authority on
ids, deploy procedure and house rules.

Point `MULTICA_PLAYBOOK` at it and read, in order: the repo's own agent-context file, its
README, and any per-workspace manifest of ids. If a drift check and a deploy script live
there, use them: they encode the safety rules in §4 as code, and running a raw
`agent update` behind their back is how a board starts lying about what is deployed.
