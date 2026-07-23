# stop-overengineering

`stop-overengineering` is an effort-control skill for Claude Code and Codex CLI. It keeps
planning and review while limiting code, tests, files, checks, and review rounds to what
the current task needs.

## Modes

| | Pragmatic (default) | Thorough |
|---|---|---|
| Use for | Day-to-day features, scripts, and fixes | Public APIs, releases, migrations, security-sensitive code, and code that is hard to change after release |
| Additions | Only what the request and its proof require | Validation and tests for current trust boundaries and core edge cases |
| Review | One plan challenge and one implementation review; a fix-only re-review when needed | Up to three rounds; the first may cover correctness, simplicity, and security separately |
| Tests | One end-to-end or integration proof when applicable | Tests for core behavior and relevant edge cases |
| Excludes | New frameworks, speculative options, single-use abstractions, and unrelated cleanup | The same exclusions |

The user can choose either mode. Otherwise, the skill uses pragmatic mode. It may skip
subagents and external review for a throwaway script or scratch analysis with no existing
users. Changes to an existing program keep the implementation review.

## Workflow

1. Define a result that can be checked and name the final proof.
2. Plan the smallest change and list the non-goals.
3. Ask a cross-vendor reviewer to cut unneeded steps, files, tests, and checks. In
   thorough mode, also ask it to identify gaps.
4. Implement the plan with a fixed scope.
5. Review the diff for defects and additions that the task did not need.
6. Verify each finding, fix confirmed problems, and rerun the failed check.
7. Remove scratch files and report the mode, review rounds, omitted work, and proof.

The full rules are in
[`stop-overengineering/SKILL.md`](stop-overengineering/SKILL.md). Reviewer commands and
prompts are in
[`stop-overengineering/references/review-prompts.md`](stop-overengineering/references/review-prompts.md).

## Review setup

The implementation and review use different model vendors:

| Host | Implementation | Plan challenge and implementation review |
|---|---|---|
| Claude Code | Fable subagents | Codex CLI with `gpt-5.6-sol` at `xhigh` reasoning |
| Codex | Native `gpt-5.6-sol` at `xhigh` reasoning | Claude CLI with `claude-fable-5` |

If the other vendor's CLI is unavailable, the skill runs a fresh same-vendor review and
reports the substitution.

## Evaluation

The repository contains five A/B tasks. The tasks cover two small scripts, one shared
rate limiter, one bounded feature, and one open-ended input-hardening request. Evals 3
and 4 use Codex `gpt-5.6-sol` at `xhigh` reasoning as the executor in both arms.

| Task | Without skill | With skill |
|---|---|---|
| Shared rate limiter | 4 of 5 checks; 31-test module; no external review | 5 of 5 checks; five correctness findings; second review clean |
| Bounded summary command | 5 of 5 checks; 12 added nonblank lines | 5 of 5 checks; 12 added nonblank lines |
| Open-ended input hardening | 4 of 6 checks; 148 added nonblank lines and an unrequested test suite | 6 of 6 checks; 11 added nonblank lines |

All five skill runs passed their assertions. Three of the five runs without the skill
also passed every assertion. Mean wall time was 556.0 seconds with the skill and 243.1
seconds without it.

This is a small regression set and does not measure run-to-run variance. See
[`evals/evals.json`](evals/evals.json) for the tasks and
[`evals/results/benchmark.md`](evals/results/benchmark.md) for the aggregate results.

## Install

### Claude Code

Copy or symlink the skill directory into the Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/stop-overengineering/stop-overengineering \
  ~/.claude/skills/stop-overengineering
```

The skill triggers on implementation work and requests such as "pragmatic mode,"
"thorough mode," "keep it simple," or "stop overengineering."

### Codex CLI

Copy or symlink the skill directory into the user skills directory:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/stop-overengineering/stop-overengineering \
  ~/.agents/skills/stop-overengineering
```

Codex detects skills in this directory without a feature flag. Restart Codex if the skill
does not appear.

To require the skill for each nontrivial implementation, add this rule to
`~/.codex/AGENTS.md`:

```markdown
Implementation work beyond a trivial one-liner goes through the
stop-overengineering skill. Default to pragmatic mode.
```

The reviewer templates send Claude prompts through standard input because some Claude
CLI versions do not keep a positional prompt placed after `--allowedTools`.

## Repository layout

```text
stop-overengineering/              Skill instructions and reviewer prompts
evals/                             Task definitions, fixtures, grader, and results
stop-overengineering-workspace/    Generated eval runs; not committed
```

## Development

Each eval runs the same task with and without the skill. The grader checks mechanical
assertions; judgment-based assertions require manual review. To add a case:

1. Add the prompt, fixture, and assertions to `evals/evals.json`.
2. Run both arms.
3. Run `evals/grade_checks.py` and complete any judgment-based assertions.
4. Regenerate the files under `evals/results/`.

When the skill produces an unwanted result in real work, add a case that reproduces that
result.
