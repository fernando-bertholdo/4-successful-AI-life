# Changelog — multica-ops

All notable changes to this plugin are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this plugin adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
