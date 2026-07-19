# Reviewer commands and prompt templates

Used at pipeline steps 3 (plan challenge) and 5 (implementation review).

## Invoking the cross-vendor reviewer

Write the filled-in prompt to a file first (scratchpad or `tasks/`), then pass it with
command substitution — inlining multi-line prompts in shell arguments breaks on quoting.
Run from the repo root so the reviewer can read the code. Delete the prompt file afterwards.

### From Claude Code → Codex (gpt-5.6-sol, xhigh)

Prefer the `claude-codex-review` skill or the `/codex:review` plugin command when available —
they handle invocation and result parsing. Raw fallback:

```bash
codex exec -s read-only -m gpt-5.6-sol -c model_reasoning_effort="xhigh" \
  "$(cat /path/to/prompt.txt)"
```

If `-m gpt-5.6-sol` is rejected, drop `-m` and `-c` — `~/.codex/config.toml` already
defaults to the current top model at xhigh.

### From Codex → Claude (Fable)

```bash
claude -p --model claude-fable-5 \
  --allowedTools "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*)" \
  < /path/to/prompt.txt
```

Pipe the prompt via stdin as shown — some claude CLI versions drop a positional prompt
argument when it follows `--allowedTools`. If `claude-fable-5` is unavailable, use
`claude-opus-4-8`.

Reviews are read-only by design: the reviewer reports, the host decides and edits. Never
let the reviewer CLI write to the repo.

## Plan-challenge prompt (step 3)

```text
You are reviewing an implementation plan before any code is written. Your job is to make
the plan smaller and sharper, not to admire it.

TASK (verbatim from the user):
{TASK}

MODE: {pragmatic|thorough}

PLAN (steps, artifacts, non-goals):
{PLAN}

Repo: {REPO_PATH} — read code as needed to check claims.

For every step, answer: is it necessary to reach the stated goal? Could it merge with
another step? Does its artifact earn its place as a separate file? Are any planned tests
or checks proving something that matters, or proving that the code is the code?

Respond with at most 40 lines, in exactly this structure:
CUT: <step/artifact> — <why it isn't needed>          (repeat per item; "none" if none)
MERGE: <steps> — <combined form>                       (repeat; "none" if none)
RISK: <the one or two things most likely to go wrong>
MISSING: <gaps — thorough mode only; omit in pragmatic unless the plan cannot reach the goal>
VERDICT: PROCEED | REVISE — one sentence.
```

## Implementation review prompt — pragmatic (step 5)

```text
You are reviewing a completed change. Two jobs, equal weight: find what is broken, and
find what should be deleted.

TASK (verbatim from the user):
{TASK}

Repo: {REPO_PATH}. Changed files: {FILES or "run git diff"}.

Report only:
1. DEFECTS — things that make the requested behavior wrong, with the failing input or
   scenario. Not style, not naming, not hypothetical hardening.
2. DELETE — code, files, tests, checks, or dependencies in this change that the task did
   not need: single-caller abstractions, guards against impossible failures, tests of
   glue, unused parameters. Name each with its location.
3. TIDINESS — scratch files, orphaned imports, or structure that doesn't match the repo.

At most 40 lines. End with: VERDICT: CLEAN | FINDINGS (n defects, m deletions).
An empty DEFECTS section with a real DELETE section is a normal, useful outcome.
```

## Implementation review prompt — thorough (step 5, round 1)

Run up to three of these in parallel, one per PERSPECTIVE: correctness, simplicity,
security. Skip the security perspective when the change has no trust boundary (no user
input, no network, no file parsing, no auth).

```text
You are one reviewer on a panel. Your assigned perspective: {PERSPECTIVE}.

TASK (verbatim from the user):
{TASK}

Repo: {REPO_PATH}. Changed files: {FILES or "run git diff"}.

correctness — logic errors, unhandled edge cases in core behavior (empty input,
boundaries, malformed data), wrong results. Give the failing input for each finding.
simplicity — everything here that could be smaller: single-caller abstractions,
speculative flexibility, tests that restate the implementation, needless files. Your
deletions carry the same weight as defects.
security — injection, path traversal, unsafe deserialization, secrets in code, missing
validation at trust boundaries only.

At most 40 lines. Numbered findings, each with location and concrete scenario.
End with: VERDICT: CLEAN | FINDINGS (n).
```

## Re-review prompt (fix verification, later rounds)

```text
Round {N} follow-up. Verify fixes only — do not re-review the whole change.

Prior findings and the commits/edits that address them:
{FINDING → FIX list}

Repo: {REPO_PATH}.

For each: FIXED | NOT FIXED (why, one line) | NEW PROBLEM INTRODUCED (what).
At most 20 lines. End with: VERDICT: CLEAN | FINDINGS (n).
```

## Handling reviewer output

- Findings are claims. Verify each load-bearing DEFECT against the code (reproduce the
  failing scenario) before changing anything; a confident reviewer can still be wrong.
- DELETE items default to accepted — restore one only with a stated reason tied to the
  task, and say so in the closing report.
- A VERDICT line that never says CLEAN across max rounds is a design signal: stop and
  report the pattern rather than iterating past the round budget.
