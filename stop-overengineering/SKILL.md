---
name: stop-overengineering
description: >-
  Effort-control harness for coding work with two modes. Pragmatic mode (default) plans,
  cross-reviews, and iteratively refines while aggressively cutting unnecessary code, tests,
  checks, abstractions, files, and token spend. Thorough mode runs iterative multi-reviewer
  refinement up to useful-level robustness without gold-plating. Both modes challenge the plan
  and review the implementation with a top model from the other vendor (Codex gpt-5.6-sol xhigh
  from Claude Code, Claude Fable from Codex) and delegate execution to subagents. Use this for
  any non-trivial implementation, feature, refactor, or script — especially when the user says
  "pragmatic", "thorough", "keep it simple", "lean", "minimal", "stop overengineering",
  "no unnecessary tests", "don't gold-plate", "production-grade", or "be comprehensive" —
  even if they never use the word "overengineering".
---

# Stop Overengineering

Agents fail in two directions. They gold-plate: abstractions with one caller, defensive
checks for impossible failures, test suites for glue code, config systems nobody asked for.
Or they under-verify: ship plausible code with no plan, no review, no proof. This skill holds
one pipeline — frame, plan, challenge the plan, execute, cross-model review, refine, tidy —
and gives it two throttle settings. The difference between the modes is not whether you plan
and review; it is how much each stage is allowed to add.

## Pick the mode

**Pragmatic (default).** Full pipeline, minimum additions. Every step, file, test, and check
must justify its existence. Optimizes for the smallest correct change and the lowest token
spend that still includes real planning and real review.

**Thorough.** Same pipeline, iterated to a fixpoint. Robustness beyond the literal ask is
allowed when it pays rent now (see "Useful overengineering"). Use when the user says
thorough / comprehensive / production-grade, or when the surface is high-stakes: public API,
release, data migration, security-sensitive code, anything hard to change after shipping.

The user's explicit choice always wins. Otherwise default to pragmatic and announce the mode
in one line at the start so it can be overridden cheaply.

## Proportionality check — the pipeline must pass its own gate

The full downgrade — skipping subagents AND the cross-vendor review — is reserved for
throwaway work: a one-off script or scratch analysis with no existing users, where being
wrong costs one rerun. There, apply the necessity gate and tidiness rules yourself, run the
proof, and state in your report that you downgraded and why. A 15-line one-shot script does
not need a review committee; sending one is itself overengineering.

Any change to an existing program — something that is run again, imported, or read by
someone else — keeps the review: skip the subagents if the change is small, but still send
the diff for the single pragmatic review round. In pragmatic mode that review is the only
external check the work gets, and it is precisely on "obviously simple" changes that
self-review shares the author's blind spot. What you save by skipping it is one CLI call;
what it catches rides into a program people keep using. When in doubt, run the full
pipeline.

## Model wiring (host-aware)

Detect which CLI you are and wire accordingly. Never review your own work with your own
model family — the cross-vendor pass exists because self-review shares the blind spots of
the code it reviews.

| Host you are running in | Execution subagents | Plan challenge + reviews |
|---|---|---|
| Claude Code | Fable (Agent tool, `model: "fable"`) | Codex CLI: `gpt-5.6-sol`, reasoning `xhigh` |
| Codex | native (`gpt-5.6-sol` xhigh) | Claude CLI: `claude -p --model claude-fable-5` |

Exact commands and all reviewer prompt templates live in
`references/review-prompts.md` — read it when you reach steps 3 and 5.

Fallbacks: if `gpt-5.6-sol` is rejected, drop the `-m` flag and use the default model in
`~/.codex/config.toml` (it is kept current). If the cross-vendor CLI fails twice, review with
a top in-host model instead (Fable/Opus subagent in Claude Code; a fresh native pass in
Codex) and flag the substitution in your report — a same-vendor review is worth less, so the
user should know they got one.

Pragmatic mode saves tokens through fewer, tighter steps and bounded outputs — never by
downgrading to weaker models. A cheap model that misses the flaw costs more than the strong
model that catches it.

## The pipeline

1. **Frame.** Restate the task as a verifiable goal plus the proof you will run at the end
   (a command and its expected result). One or two sentences. If the goal cannot be made
   verifiable, stop and ask before burning tokens on it.

2. **Plan.** Smallest set of steps that reaches the goal. Each step names its artifact.
   Include an explicit **non-goals** list — what you are deliberately not building. Writing
   non-goals down is the cheapest overengineering prevention there is: it converts silent
   scope creep into a visible diff against the plan.

3. **Challenge the plan — before writing any code.** Send the plan to the cross-vendor
   reviewer using the plan-challenge prompt in `references/review-prompts.md`. The
   reviewer's primary job is to cut: steps that aren't necessary, artifacts that could be
   merged, tests that prove nothing. In thorough mode it also hunts for gaps. Adopt the
   cuts by default; keep a challenged step only with a stated reason. Catching a needless
   component here costs one review; catching it after implementation costs the
   implementation, the review, and the deletion.

4. **Execute.** Delegate implementation to subagents with bounded scope — one step or one
   coherent group of steps each, using the execution model from the table above. Paste the
   constraint block (below) into every subagent prompt: subagents do not inherit this
   skill's context, and an unconstrained subagent will happily gold-plate. Treat subagent
   output as claims; spot-check anything load-bearing.

5. **Review.** Send the diff to the cross-vendor reviewer with the mode's review prompt
   from `references/review-prompts.md`. Reviews here subtract as well as flag: every
   review must answer both "what is broken?" and "what should be deleted?".

6. **Refine.** Reviewer findings are claims — verify the load-bearing ones against the code
   before rewriting to satisfy them. Fix what survives verification, then re-run the exact
   gate that caught each problem. Round limits are set per mode below.

7. **Tidy and close.** Run the tidiness sweep (below), run the proof named in step 1, and
   finish with the closing report (below).

## Pragmatic mode

**The necessity gate.** Before adding anything — a function, file, dependency, abstraction,
test, or check — it must survive these questions:

1. Was this asked for, or is it strictly required to make what was asked for work?
2. Will it be exercised by a caller that exists today? (Abstractions need two real users,
   not one real and one imagined.)
3. Can the failure it guards against actually happen in this context?
4. Could an existing file or function host this instead of a new one?

A "no" on 1 or 2 means don't build it. Note real future needs in the report instead —
a sentence costs nothing; speculative code costs review, maintenance, and reader attention
forever.

**Code budget.** If the diff is growing to several times what the ask sounds like, stop and
re-plan rather than finishing the big version. If 200 lines could be 50, rewrite before
review — reviewers should spend their pass on correctness, not on bulk you already knew
was excessive.

**Test policy.** Prove the requested behavior at the highest sensible level — one
end-to-end or integration proof beats a dozen unit tests of internals. No tests for glue,
wiring, or trivial transforms. No mocking ceremonies unless the boundary is genuinely
expensive or nondeterministic. No coverage targets. Use the project's existing test
runner; never introduce a test framework, CI job, linter, formatter, pre-commit hook, or
type-checking config that wasn't asked for.

**Round budget.** One plan challenge, one implementation review. A second review round only
if the first found a real defect — and then it re-checks the fix, not the whole diff.
Reviewer output capped at ~40 lines (the caps are in the prompt templates). Subagents
return conclusions, not file dumps.

**Token discipline.** Delegate broad reading to subagents so the main thread keeps only
conclusions. Don't re-read files you've already read or re-derive established facts. Ship
when the proof passes — polishing beyond the proof is spend without return.

## Thorough mode

**Useful overengineering** — robustness that pays rent now, allowed and encouraged:

- Input validation at trust boundaries (user input, file formats, network data) — not on
  internal calls between functions you both wrote.
- Error messages that tell the operator what to do, not just what broke.
- Edge-case tests for the core logic: empty input, boundaries, malformed data, concurrency
  where it genuinely exists.
- Docstrings and a usage example on the public surface.
- Extension seams only where a follow-up change is already scheduled — name the scheduled
  change in the report when you add one.

Still banned even here: speculative config systems, plugin architectures, abstract base
classes with one implementation, wrappers around single functions, coverage theater. The
overengineering smells list below applies in both modes; thorough mode buys depth on the
real requirements, not permission for the fake ones.

**Round budget.** Up to three review rounds, stopping early when a round comes back clean.
In round one, fan the review out to parallel perspectives — correctness, simplicity,
security — as separate reviewer calls or subagents. The simplicity reviewer's cuts carry
the same weight as the correctness reviewer's defects: thorough means well-verified, not
big. Later rounds are single-reviewer passes over the changes since the previous round. If
round three still finds substantive defects, stop and report the pattern instead of
grinding — repeated failed rounds signal a design problem, not a polish problem.

## Overengineering smells — delete on sight, both modes

Abstraction smells:
- A class, interface, or wrapper with exactly one implementation or one caller
- A factory, registry, or plugin system with a known, fixed set of members
- Parameters, flags, or config keys nothing sets
- "Generic" helpers generalized from a single use case

Defense smells:
- try/except or null-checks around calls that cannot fail in this context
- Re-validating data already validated upstream
- Fallback paths that have no trigger and have never run
- Logging scaffolding in a script that runs once and prints its result

Process smells:
- CLI argument parsing in a script with one fixed invocation
- Backwards-compatibility shims for code that has no external users
- New lint/CI/type-check configs nobody requested
- A README, changelog, or docs page for an internal one-shot script

Test smells:
- Unit tests that restate the implementation line by line
- Mocks of cheap, deterministic collaborators
- Tests for third-party library behavior
- Coverage-driven tests of trivial getters, glue, or wiring

## Repo tidiness — non-negotiable, both modes

- Every new file needs a justified home; ask whether an existing file can host the code
  first. No `utils/` dumping grounds, no `helpers2.py`.
- Scratch work goes in the scratchpad or `tasks/` (gitignored) — never the project tree.
  Delete one-off debug and verification scripts after they've served their purpose.
- Remove imports, variables, and files your change orphaned. Leave unrelated pre-existing
  dead code alone — that's someone else's diff.
- Match the project's existing naming, layout, and style; don't "improve" adjacent code.
- Final sweep before closing: `git status` (or a directory listing outside git) must show
  only files that belong to the change. Stray artifacts are a bug in your process.

## Subagent constraint block

Paste this into every execution subagent prompt, filling in the mode:

```text
EFFORT MODE: {pragmatic|thorough}
- Build exactly what the task states; list anything extra you believe is needed instead
  of building it.
- No new abstractions with a single caller, no new dependencies, no new config, no new
  files beyond those named in the task.
- Tests: {pragmatic: only the proof named in the task} {thorough: core logic and real
  edge cases; no coverage padding}.
- No lint/CI/tooling additions. Match existing project style; touch only the files the
  task names.
- Leave no scratch files. Return a summary of what you changed and the commands you ran
  with their results — conclusions, not file dumps.
```

## Closing report

End every run with a short report:

- Mode used (and any proportionality downgrade or reviewer fallback, with the reason)
- What was cut or deliberately not built, including anything deferred with a note
- Review rounds run, which model reviewed, and what each round changed
- The proof: the exact command run and its result
