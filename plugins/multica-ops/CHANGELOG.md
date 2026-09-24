# Changelog — multica-ops

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.9] — 2026-09-24

### Changed

- `patch-description.py` decides the window by counting `description_updated`, not by
  `revision`. It counts the events before reading the description (`N`) and again after writing
  (`M`), and requires exactly one new event, ours — new by id, so a read the server caps cannot
  hide one; if ours has not shown yet, it reads again, up to three times a second apart. The
  0.2.8 check, `revision` exactly +1, raised exit 3 on a comment, a status change or a write the
  `timeline` does not show; a comment in the window now exits 0. The count comes before the
  read because the inverse lets a write land in `N` with the text in hand already stale, and it
  uses no `--since`: that flag drops the whole second it is given, and `updated_at` is the second
  of the last event (measured on CLI v0.5.3). LAS-147, items 2 and 5.
- Exit 3 gives the input for the action instead of "reconcile by hand": the erased text cannot
  be recovered through the CLI (the event keeps no text, `details` is empty, and there is no
  history command), so do not write over it again and ask the event's author to re-apply it.
  It prints the read's `updated_at`, `revision` before and after, each new event with its time,
  `actor_type` and `actor_id`, and the command that lists them. With two or more new events and
  `revision` up by only one, it says nothing was lost. LAS-147, item 4.
- The branch where the re-read differs prints the same window and says ours may be the write
  that was erased; re-running is safe. LAS-147, item 1.
- §8 follows the script: count instead of `revision` +1, the order, the second `--since`
  drops (start one second earlier when searching by hand), no recovery, the author re-applies.
  No `--if-revision` on `issue update` as of v0.5.3.

### Fixed

- `--edits` takes only a JSON list of pairs of two strings, the first non-empty, and exits 2
  otherwise; 0.2.8 turned `null`, numbers and a two-character object key into text and exited
  0. An empty `--append` block exits 2 instead of 1. LAS-147, item 3.

### Added

- `tests/`: a fake `multica` (`fake_multica.py`, reached through `MULTICA_BIN`) that reproduces
  the measured server behaviour, and 15 `unittest` cases for the script;
  `bash tests/run-tests.sh`, standard library only.

---

## [0.2.8] — 2026-09-23

### Added

- §8: **a description write replaces the whole field, and nothing merges it.** Two writers that
  read, edit and write back erase each other in silence; v0.5.2 still has no compare-and-set on
  `issue update`. Three habits — read immediately before writing, change only your substring,
  re-read and compare content — and the case that motivated them (LAS-69, 21/09/2026; LAS-147).
- `skills/board/scripts/patch-description.py`: the three habits as a helper. Exact-substring
  edits and/or an append on a fresh read; no write at all when the result is the stored text;
  write with `--no-start`; then re-read: the content must match ignoring trailing whitespace
  (a write after ours), and `revision` must be exactly one higher (a write before ours is
  erased by ours and shows only there). Exit 0 verified, 1 nothing written, 2 CLI, file or
  usage error, 3 window not clean — a jump in `revision` is not proof of loss, and the
  `timeline` decides.
- What moves `revision`, measured on 24/09/2026 on a throwaway issue (v0.5.2): +1 per
  description write that changes the text, +0 for an identical write (which still logs a
  `description_updated`), +1 per comment or reply, +1 per title or status change, +1 for title
  and description in one call (two events).

---

## [0.2.7] — 2026-09-20

### Added

- §3: **an unquoted heredoc executes backticks**, and prose about the shell is full of them. A
  board comment written with `<<EOF` whose text *mentioned* `` `git ls-files` `` shipped with 440
  lines of repository listing spliced into it (measured 20/09/2026); the two sibling comments in
  the same batch were clean only because they named no commands. Use `<<'EOF'`.
- §4: **`--summary` truncates the body to ~200 characters, and `--output json` does not turn it
  off.** Harmless while scanning threads; wrong when the read is used to *verify what you wrote*.
  The same comment measured 201 characters with the flag and 2431 without — a session can
  conclude its own write was truncated and "fix" a comment that was already complete.
- §4: **`issue comment list --thread` prints a `Next reply cursor:` line before the JSON**, so a
  strict parser dies on character 1 and the error reads as malformed JSON rather than a prefix.
- §5: **a run is not idle just because its status is not `queued`/`running`/`pending`.**
  `waiting_local_directory` is live — runs against the same repository serialise behind it.
  Decide liveness by a deny-list of terminal states and treat anything unrecognised as alive;
  "no run is alive" is the precondition for merging.

---

## [0.2.6] — 2026-09-20

### Added

- §3: **braces when a variable is followed by anything.** `git show $TB:path` looks up the
  variable `$TB:path`, not `$TB` — measured 20/09/2026, it produced the nonexistent ref
  `tech-676-2-17-1k-changelog-local.sh`. Write `"${TB}:path"`.
- §3: **`tr` pads instead of failing when the sets differ in length.** `tr 'A-Z-' 'a-z'` maps
  `-` to `z`, so `LAS-114` becomes `lasz114`. On 20/09/2026 this pointed 17 evidence commands at
  filenames that did not exist and produced 17 false FAIL, one step before they would have been
  written to seven issues — the concrete argument for §8's rule that a board write never shares
  a chain with a step that can fail.
- §4: **an issue's parent is `parent_issue_id`, not `parent_id`.** `parent_id` is real on a
  *comment*, so reading it on an issue returns `None` rather than erroring and the session
  concludes the issue is top-level. Measured against LAS-69, which is stage 3 under LAS-40.
- §5: **reply routing inherits the thread root.** A reply to a member's comment is safe only
  when the root carries no agent mention; under a root that names an agent, that agent is
  enqueued even when both comments are a human's and neither mentions anyone. Measured
  19/09/2026 on CLI v0.4.44: five such replies started five extra Reviewer runs and duplicated
  a review round.

### Changed

- §3: the pipeline-exit note now carries the measured case (an `&&` chain continued past a gate
  harness that had printed 4 FAIL, because the exit read was `tail`'s) and the recipe —
  `OUT="$(cmd 2>&1)"; RC=$?` before any filter, or `set -o pipefail`.
- §1: the provenance note now separates what was measured on v0.4.42 from what was measured on
  v0.4.44 between 19 and 20/09/2026.

---

## [0.2.5] — 2026-09-19

### Fixed

- The stage barrier does not wake the conductor "with no mention at all": the barrier
  comment is posted by the platform (`author_type: system`) and opens with a mention of the
  conductor. What the verdict's author cannot control is the platform's mention — which is
  why removing your own mention is not enough. Measured on the same issue as 0.2.4.

---

## [0.2.4] — 2026-09-19

### Fixed

- 0.2.3 replaced "53 s" with "2 s", and the 2 s was a different event: the stage barrier
  waking the conductor, on another issue. Measured at the source: barrier at 2 s, verdict at
  52 s (53 s from the merge commit), follow-up issues at 150 s and 158 s. Both facts now
  stand, each with its event — the lesson being that a reviewer's correction is a claim to
  verify, not a fact to apply.

---

## [0.2.3] — 2026-09-19

### Fixed

- The pre-merge note in §8 quoted "53 s" from a hand-off document; the primary sources
  (`gh pr view --json mergedAt`, `issue runs`, the issues' `created_at`) give 2 s from the
  merge to the conductor's next run and 150 s to the first follow-up issue. Corrected — the
  same day the plugin started telling sessions to measure before they write a number.

---

## [0.2.2] — 2026-09-19

### Added

- **The recipes the sessions of 18–19/09/2026 had to discover by failing.** Measured on CLI
  v0.4.44. Any string field a person typed can carry a raw control character, intermittently
  (five outputs parsed strictly on the day; earlier sessions hit bodies that did not), so the
  default is a lenient parse — `json.loads(raw, strict=False)` — rather than a strict one that
  dies mid-batch. The playbook manifest keys projects and autopilots by `title:`, not `name:`.
  A board write never shares a command chain with a step that can fail, and in zsh `set -e`
  covers neither command substitution nor a Python heredoc.
- **Pre-merge check for a human-conducted PR:** `issue runs` and `issue timeline` on the issue
  the PR closes, because an agent conductor may be alive on the same PR — on 18/09/2026 a human session
  merged while the conductor agent was still running review rounds; the stage barrier woke it
  2 s after the merge, the verdict 52 s after, and it opened two follow-up issues at 150 s and
  158 s.
- **`/note` addresses nothing to anyone.** §5 already said it wakes no one; §8 now says the
  other half: a pending item that lives only in a `/note` is written to nobody, and goes to a
  checkbox with a `verify:` in the description or to an issue of its own.

---

## [0.2.1] — 2026-09-10

### Added

- **What wakes an agent when you comment.** The reference documents the `mention://` links but
  not the implicit routing, which is the expensive surprise: a plain comment with no mention can
  start a run. Verified against Multica's product documentation and the server's comment-routing
  code — a first token of `/note` (case-insensitive) suppresses every trigger including explicit
  mentions; `@all` cancels the assignee fallback and never reaches agents; otherwise routing
  follows the discussion, with a top-level comment falling back to the issue's agent assignee (a
  squad's leader), while a plain reply to a member's comment does not; the fallback **fires in
  any status, closed issues included**; and it is skipped when the assignee has no runtime, is
  archived, cannot be invoked by the author, or already holds a pending run that consecutive
  comments coalesce into.
- Stated plainly that `issue comment add` has **no `--no-start`** — the flag exists only on
  `issue status`, `issue assign` and `issue update`. A widely-repeated search-engine answer
  claims otherwise.

---

## [0.2.0] — 2026-09-10

### Changed

- **Re-cut as a companion to the official skill, not a competitor.** Multica publishes the
  canonical CLI skill at [`multica-ai/multica-cli`](https://github.com/multica-ai/multica-cli),
  linted daily against the real binary on both the minimum and latest CLI. Running its linter
  against CLI v0.4.42 — four weeks and sixteen patch versions after its last commit — surfaced
  only two divergences, so it is the command reference, and this skill now says so and defers
  to it. Everything it already covers was removed from here: `issue search`, the comment read
  modes, the working-directory restriction on file arguments, when `--parent` is mandatory, the
  `mention://` side effects, metadata versus custom properties, subscribers, run inspection and
  cancellation, sub-issue stages, and PR linking. Two skills describing the same commands
  eventually disagree, and the session obeys whichever it read first.

### Added

- **A governance section** for the case this plugin exists to serve: a board whose agent
  instructions, workspace skills, context and project descriptions are versioned in a
  repository and deployed through the CLI. Reading order, and the eight constraints such a repo
  encodes — editing is not deploying, deployment is a human act, ids come from the manifest,
  drift is measured before state is claimed, undeployed changes are tracked work rather than
  prose, text governing other agents is not changed unilaterally, no credentials in that text,
  and shared text must not hardcode one workspace's ids.
- Output shapes and cost flags absent from the reference as of its v1.1.0, all measured on CLI
  v0.4.42: the 100-item cap on `--limit` and the `has_more` paging subtlety (advance `--offset`
  by the number of issues actually returned), `issue list --fields` for trimming agent context
  cost, `issue timeline`, and the `--content-stdin` / `--description-stdin` / `--context-stdin`
  family that sidesteps the working-directory restriction on macOS.
- Platform limits: `agent update --mcp-config` (agents *consume* MCP servers — pass it by stdin
  or file, since the command line reaches shell history and `ps`), and scheduled autopilots
  taking a full cron expression with an IANA timezone plus `--subscriber` on creation.

---

## [0.1.0] — 2026-09-10

### Added

- First release. One skill, `board`: the operating manual for a Multica board from Claude Code
  or from a Cowork/claude.ai session bridged to the machine running the desktop app.
- Discovery-first design: the profile comes from `~/.multica/profiles`, the workspaces from
  `workspace list --output json`, and every other id from the corresponding `list` command.
  No workspace id, project name or machine-specific path is embedded in the plugin.
- Safe defaults documented as conventions rather than enforcement: `--no-start` on every
  `issue status`, silence on unscoped issues, promotion and deployment reserved for a human,
  no casual `create` of registry objects, and a dated trace when a session acts under a
  human's profile.
- Measured platform notes against **CLI v0.4.42**: the 100-item page cap on `--limit`, the
  `{stages, total, unstaged}` shape of `issue children`, the bare list from
  `issue comment list`, the `{"autopilot": …}` wrapper, the positional label argument on
  `issue label add`, `--name` (not `--property-id`) on `issue property set`, labels not
  inherited through `--parent`, the 255-character cap on `agent create --description`, and the
  absence of a global run listing.
- Shell gotchas that have produced real defects: zsh collapsing a flag-holding variable into a
  single argument (the reason for the `mt()` wrapper), `for x in $VAR` iterating once,
  1-indexed arrays, lowercase `pipestatus`, `$?` after a pipeline, and BSD grep's lack of `\s`.
- Platform limits: per-workspace isolation (only a human profile's CLI sees more than one),
  artifacts disabled inside agent tasks including subagents, and no MCP surface in the binary.
- `MULTICA_PLAYBOOK` hand-off: when a repository versions the Multica configuration, the skill
  defers to its manifests, drift check and deploy script instead of acting directly.
