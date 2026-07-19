# stop-overengineering

An effort-control skill for coding agents (Claude Code and Codex CLI). It keeps the parts of
agentic engineering that catch real bugs in our evals — planning, iterative review,
refinement — while putting a hard budget on what each of those stages is allowed to *add*.

## The problem

Frontier models at high reasoning effort rarely fail by doing too little. Handed an
open-ended task ("make this handle bad input gracefully"), they spend the surplus on things
nobody asked for: test suites for a project that has no test runner, schema validation for
internal data, backup and recovery machinery, abstraction layers with one caller.

In our measurements, **gpt-5.6-sol at xhigh reasoning is the clearest case**. Given a small
two-file expense tracker and asked to handle bad input and a corrupted data file, it shipped
**148 lines** including an unrequested `unittest` suite and per-field schema validation — and
it did this even after running a code review on its own work, because a review that is only
asked "is this correct?" will polish bloat rather than remove it. The same task, same model,
same sandbox, run through this skill: **11 lines**, no scaffolding, friendlier error
messages, and a higher score on the graded functional checks.

Dropping the reviews would be the wrong fix, because they catch real defects. This skill
keeps them and adds a **deletion mandate**: every review must answer two questions with equal
weight, *what is broken?* and *what should be deleted?* Under that contract, the same model
that gold-plated the expense tracker found two genuine crash bugs by mutation testing in our
thorough-mode run.

## Two modes, one pipeline

Both modes run the same pipeline: frame a verifiable goal, plan with explicit non-goals,
challenge the plan before writing code, execute, review cross-vendor, refine, tidy, report.
The modes differ only in how much each stage may add.

| | Pragmatic (default) | Thorough |
|---|---|---|
| For | day-to-day features, scripts, fixes | public APIs, releases, migrations, concurrency |
| Additions | necessity gate: every function, file, test, and check must justify itself | hardening that pays rent now: trust-boundary validation, edge-case tests, docstrings |
| Review budget | 1 plan challenge + 1 review round (re-review only verifies fixes) | up to 3 rounds; round 1 fans out correctness / simplicity / security perspectives |
| Tests | one proof at the highest sensible level | the tests that matter; still no coverage theater |
| Still banned | everything on the smells list | config systems, plugin points, single-implementation abstractions |

A proportionality rule applies the same standard to the pipeline itself: throwaway one-off scripts skip
the review committee entirely (sending one is itself overengineering), while any change to a
program with existing users keeps at least the single review round.

## Cross-vendor review wiring

Self-review shares the blind spots of the code it reviews, and same-vendor review shares the
model's. Reviews therefore cross vendor lines:

| Host | Execution | Plan challenge + reviews |
|---|---|---|
| Claude Code | Fable subagents | Codex CLI: `gpt-5.6-sol`, reasoning `xhigh` |
| Codex | native (`gpt-5.6-sol` xhigh) | Claude CLI: `claude -p --model claude-fable-5` |

If the cross-vendor CLI is unavailable, the review falls back to the strongest same-vendor
model in a fresh context, and the closing report flags the substitution so a downgraded
review is never silently passed off as the real thing.

## Measured results

Five A/B evals, each run with and without the skill (harness in `evals/`, aggregated results
in `evals/results/`; raw runs land in the generated workspace). Evals 3 and 4 use Codex
`gpt-5.6-sol` xhigh as the executing agent in both arms, so the only variable is the skill.

| Eval | Task | Without skill | With skill |
|---|---|---|---|
| 2 | thorough mode: token-bucket rate limiter | 31-test module, no external review, 4/5 checks | reviewer found 5 findings incl. 2 crash bugs via mutation testing, round 2 CLEAN, 5/5 checks |
| 3 | small feature, "keep it pragmatic" hint | +12 lines, lean | +12 lines, lean (identical — with a hint and small scope, the model behaves) |
| 4 | open-ended hardening ask, no hint | **+148 lines**, unrequested test suite, 4/6 checks | **+11 lines**, 6/6 checks, plan challenge PROCEED + review CLEAN |

Evals 0–1 (small pragmatic tasks with Claude subagents) passed all functional checks in both
arms and are omitted from the table. Aggregate assertion pass rate: 100% with the skill vs
89.3% without. Two caveats: wall-clock is 16–41% *higher* with the skill (review calls cost
minutes; the savings are in code volume and maintenance surface, not runtime), and each eval
is a single run — the direction is consistent, the magnitudes will vary.

## Install

### Claude Code

Copy or symlink the skill directory into your skills folder:

```bash
ln -s /path/to/this/repo/stop-overengineering ~/.claude/skills/stop-overengineering
```

The skill triggers on implementation tasks and on phrases like "pragmatic mode", "thorough
mode", "keep it simple", or "stop overengineering".

### Codex CLI

Codex does not load Claude skills automatically. Add a pointer to your `~/.codex/AGENTS.md`:

```markdown
For implementation tasks, read ~/.claude/skills/stop-overengineering/SKILL.md
and follow it. Default to pragmatic mode.
```

One CLI-version note: pipe reviewer prompts to `claude -p` via stdin — some versions drop a
positional prompt argument that follows `--allowedTools` (the templates in
`references/review-prompts.md` already do this).

## Repository layout

```
stop-overengineering/        the skill: SKILL.md + references/review-prompts.md
evals/                       eval definitions (evals.json) and task fixtures
stop-overengineering-workspace/   generated eval runs, grading, benchmark (disposable)
```

## Development

The eval harness follows the skill-creator loop: each eval runs the same prompt with and
without the skill, outputs are graded by scripted assertions (`evals/grade_checks.py`), and
results aggregate into a benchmark (`evals/results/`).
To extend coverage, add an eval to `evals/evals.json` with a fixture and assertions, run both
arms, and grade. When the skill misfires in real use, turn that failure into a regression
eval — it is better signal than any synthetic case.
