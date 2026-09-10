---
name: board
description: The layer around the official Multica CLI skill — where the binary hides in a desktop-app install, how to reach it from a bridged Cowork/claude.ai session, the shell and JSON shapes that bite, the platform limits, and how to work a board that is governed by a repository which versions its Multica configuration. Use alongside the official `multica-cli` skill whenever a task touches a Multica board.
---

# Multica: the parts around the command reference

## 0. The command reference is not this skill

Multica publishes the canonical CLI skill at
[`multica-ai/multica-cli`](https://github.com/multica-ai/multica-cli). It is well maintained —
a linter runs its documented commands against the real binary daily, on both the minimum and
latest CLI — and it is the authority on the command surface:

```text
/plugin marketplace add multica-ai/multica-cli
/plugin install multica-cli@multica-cli
```

Go there for: `issue search` semantics, the comment read modes (`--roots-only --summary`,
`--thread --tail`, `--recent` capping *threads* not comments, `--compact`, `--full`), the
working-directory restriction on `--content-file` / `--description-file` / `--attachment`, when
`--parent` is mandatory, the `mention://` side effects, metadata versus custom properties,
subscribers, run inspection and cancellation, sub-issue stages, and PR linking.

**Do not restate any of that here.** Two skills that describe the same commands will disagree
eventually, and the session obeys whichever it read first. This skill covers what that
reference does not, and the moment it starts to overlap, the overlap is the bug.

If the reference is not installed, say so before operating a board — the safe defaults for
mentions, status side effects and comment writes live there.

## 1. Finding the binary in a desktop-app install

The reference assumes `multica` is on `PATH` (a package-manager install). With the desktop app
it is not, and `command -v multica` returning nothing is expected — the reference's very first
step, `multica version`, fails there.

```bash
M="${MULTICA_BIN:-/Applications/Multica.app/Contents/Resources/app.asar.unpacked/resources/bin/multica}"
"$M" --version
ls ~/.multica/profiles       # the profile names on this machine
P="${MULTICA_PROFILE:-<one of those>}"
"$M" --profile "$P" workspace list --output json    # -> [{id, name, slug}, …]
```

Record the version next to any claim you make about the surface. The CLI ships changes almost
daily; everything measured below held on **v0.4.42**.

## 2. Two routes, and only one is direct

**Claude Code on the machine with the desktop app** — run the CLI in the shell. Done.

**A Cowork or claude.ai session bridged to that machine** — the session's own shell runs in a
separate sandbox with only the connected folders mounted. It cannot see `/Applications`, so it
cannot reach the CLI. The route that works is the bridge's shell on the user's machine (on
macOS, an AppleScript `do shell script "…"`), and three things bite there:

- Nested quoting breaks easily — avoid `python3 -c` with inner quotes. Write output to a file
  inside a connected folder and read it from the sandbox.
- That shell reports any non-zero exit as a tool error, even a `which` that finds nothing. End
  with `; echo done`, or `|| true`, when the exit code does not matter.
- The sandbox usually cannot delete files in connected folders. Clean up from the same bridge
  shell that created them.

With the desktop app closed, neither route exists. Say so and move on.

## 3. Shell gotchas that have produced real defects

Mostly zsh, the macOS default:

- **A variable holding several flags becomes one argument.** `"$M" $flags --help` fails. Wrap
  it: `mt(){ "$M" --profile "$P" --workspace-id "$WS" "$@"; }` — or drive the CLI from Python's
  `subprocess`.
- `for x in $VAR` iterates **once**. Use `${=VAR}` or a real array. This has silently produced
  batches of issues carrying an invalid `--workspace a b`.
- zsh arrays are **1-indexed**: `${A[0]}` is empty, which is how an issue gets created with a
  blank field.
- `pipestatus` is lowercase, and `EXIT=$?` after a pipeline measures the *last* command:
  `bash script | tail` gives you `tail`'s exit code.
- Agent shells often abort on the first non-zero exit. Guard commands whose non-zero exit is a
  normal outcome — a drift check that exits 1 on "differs" — with `|| true` or `set +e`.
- BSD grep has no `\s` (use `[[:space:]]`), and `--include=*.md` needs quoting in zsh.

## 4. Output shapes and cost flags the reference does not state

Measured on v0.4.42, against reference v1.1.0:

- `--limit` caps at **100** (default 50); above it the CLI refuses and tells you to page.
  Paging is subtle: advance `--offset` by the **number of issues in the response you just got**,
  using `has_more` from the JSON — not by your requested page size.
- `issue list --fields id,title,status,…` trims the returned object client-side, explicitly to
  cut agent context cost. It is the cheapest flag on the whole board surface and it is absent
  from the reference.
- `issue children --output json` returns `{stages, total, unstaged}`, not an array. Iterate
  `.stages[]` and check `(.unstaged|length) == 0`; a bare `.[]` walks three heterogeneous
  values without erroring.
- `issue comment list` returns a bare list, not `{comments: […]}`, and bodies can carry raw
  control characters — strip them before parsing.
- `autopilot get` wraps its payload in `{"autopilot": {…}}`; the other `get` commands do not.
- `status_category` collapses custom review statuses together; only `.status` separates them,
  and `status_name` comes back empty for custom statuses inside `children`.
- `trigger_comment_id` exists only on runs of `kind: comment`. A `direct` run carries
  `attribution: issue_assignment` with `source: direct_human`; one started by an agent on a
  human's behalf carries `source: delegation` with the human `initiator` preserved.
- `issue timeline` answers "when did this reach review" and "how long has it sat here" — the
  reference does not mention it, and its own linter flags that.
- `--content-stdin` / `--description-stdin` / `--context-stdin` exist and the CLI's own help
  recommends them for multi-line bodies. The reference prescribes files only, which is the
  portable choice (stdin mangles non-ASCII on Windows) — on macOS, stdin sidesteps the
  working-directory restriction and leaves no file to clean up.

## 5. What wakes an agent when you comment

The reference covers the `mention://` links. It does not cover the **implicit** routing, and
that is what costs money by accident: a plain comment carrying no mention at all can start a
run. These rules come from Multica's own product documentation and the server's comment-routing
code, not from inference.

- A comment whose **first whitespace-delimited token is `/note`** (case-insensitive) triggers
  nothing at all — mentions inside it included, because the check runs before mentions are
  parsed. It posts as an ordinary comment and the token stays in the body. This is the
  one-command way to write on an issue without waking anyone.
- `@all` notifies every member and switches off the assignee fallback for that comment. It does
  not reach agents: agents have no inbox.
- With neither of those, routing follows the discussion: a reply to an agent's comment goes to
  that agent; a reply inside a discussion an agent already joined stays with that agent; a
  **top-level** comment matching neither goes to the issue's **agent assignee** (the leader,
  when the assignee is a squad). A plain reply to a *member's* comment does not fall back to the
  assignee. Any explicit mention — including of a member — cancels the fallback.
- **The assignee fallback fires in any status, closed issues included.** Comments are
  conversational and follow-up questions on finished work are expected behaviour. A terminal
  status is not a safe place to write.
- It is skipped when the assignee has no runtime, is archived, you cannot invoke it, or it
  already holds a pending run on that issue — consecutive comments coalesce into the waiting run
  rather than starting a second one.
- `issue comment add` has **no `--no-start`**. That flag exists on `issue status`, `issue assign`
  and `issue update`, and nowhere else. Anything claiming otherwise — including a confident
  answer from a search engine — is wrong; `--help` settles it in one second.

So the recipe for commenting on an agent-assigned issue without starting a run is a `/note`
prefix, not an unassign-comment-reassign dance. The dance works, but it mutates ownership for
the duration and is not needed.

## 6. Platform limits worth knowing before you promise something

- **Workspace isolation is real.** An agent running in one workspace cannot read another; only
  a human profile's CLI sees more than one. Cross-workspace search, dependencies and any
  portfolio view exist *only* through that CLI. When writing anything that governs agents, ask
  whether it assumes an agent can see a neighbouring workspace — if it does, that is a defect.
- **Agents cannot produce artifacts.** In an agent task the artifact tool is disabled and the
  refusal is explicit: `Artifact is disabled for this session, in subagents as well as here`.
  Delegating to a subagent does not work around it. Attach a file to a comment instead.
- **There is no MCP surface on the CLI** — but `agent update` takes `--mcp-config`,
  `--mcp-config-stdin` and `--mcp-config-file`, so agents *consume* MCP servers. The useful
  question is which servers your agents should have, not how to wrap the CLI in one. Pass that
  config by stdin or file: on the command line it lands in shell history and `ps`.
- `agent create --description` caps at 255 characters, and `--instructions` takes a string, not
  a path.
- Scheduled autopilots take a full cron expression and an IANA timezone
  (`autopilot trigger-add --kind schedule --cron … --timezone …`), and `autopilot create` takes
  `--subscriber`. Sub-hourly expressions are writable; whether the server honours a given
  granularity is a test, not a promise.

## 7. When a repository governs the board

A team running Multica seriously keeps its agent instructions, workspace skills, workspace
context and project descriptions **versioned in a repository** and pushes them to the server
through the CLI. If `MULTICA_PLAYBOOK` is set, or the working tree looks like such a repo, that
repository outranks this skill and the reference on everything it declares.

**Read before acting, in this order:** the repo's agent-context file (`CLAUDE.md` / `AGENTS.md`)
for the rules that bind you; the root `README` for what each directory is and which of them
deploy; the per-workspace manifest for ids; and the scripts directory for the drift check and
the deploy tool.

The constraints such a repo almost always encodes — assume them until its own text says
otherwise:

1. **Editing is not deploying.** A file in that repo is operational *text*; the live system
   changes only when `agent update`, `skill update`, `workspace update`, `project update` or
   `autopilot update` runs. A commit changes nothing on the server. Saying "the agent now does
   X" because the file says X, with no deployment, is a false statement about the system.
2. **Deployment is a human act.** Never run those five commands on your own. Propose the diff,
   name the file, and stop. If the repo ships a deploy script, its dry-run is yours to use and
   its apply mode is not.
3. **Ids come from the manifest, never from memory or from a listing you skimmed.** The
   manifest is generated from the server and diffable; that is the point of it.
4. **Measure drift before you claim state.** If the repo ships a drift check, run it and read
   its exit code as state, not as failure — "differs" is the normal condition before a
   deployment.
5. **A committed-but-undeployed change is tracked work, not a paragraph.** Register it wherever
   that repo says pending work lives — a board item, not a heading in a versioned file, which
   is how status silently goes stale.
6. **Text that governs other agents is not yours to change unilaterally.** Behavioural rules,
   status contracts, backlog policy and review thresholds are decisions of whoever owns the
   system. Propose in diff; a taken decision gets recorded where that repo records decisions.
7. **No credentials in any of that text.** Instructions are stored server-side and passed
   through process arguments.
8. **Shared text must not hardcode one workspace's ids.** A registry id from workspace A
   deployed into workspace B points at nothing, and the failure is silent. Render it from the
   manifest, or write the sentence without the id.

Before writing anything into such a repo, ask yourself the two questions it exists to enforce:
does this change behaviour on the server (then it needs a deployment, tracked), and does it
assume an agent can see a workspace it cannot?

## 8. Conduct on the board

The reference covers the mechanics of side effects. These are the habits around them:

- Scoping is a human gate. Promoting an item out of the unscoped column is where a person's
  decision is cheap and changes the outcome; leave it to them, and do not comment on an
  unscoped item — that comment is written to nobody.
- Acts performed with a human's profile are indistinguishable from that human in
  `issue timeline`. When a session acts, leave a dated note saying so.
- Never create a registry object — agent, skill, project, autopilot — casually. It will appear
  in no manifest and no drift check will see it.
