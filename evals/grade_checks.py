#!/usr/bin/env python3
"""Programmatic checks for iteration runs. Emits grading.json drafts per run.

Judgment-flavored assertions get "passed": null and are finalized by hand.
Usage: python grade_checks.py <iteration-dir>
"""
import csv
import json
import re
import subprocess
import sys
import time
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
ORIG_TODO = EVALS_DIR / "files/todo-cli/todo.py"


def run(cmd, cwd, timeout=60):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def listing(outdir):
    return sorted(
        str(p.relative_to(outdir))
        for p in outdir.rglob("*")
        if p.is_file() and "__pycache__" not in str(p)
    )


def grade_eval0(outdir):
    ex = []
    merged = outdir / "merged.csv"
    ok = False
    evidence = "merged.csv missing"
    if merged.exists():
        rows = list(csv.reader(merged.open()))
        data = rows[1:]
        uniq = len(set(map(tuple, data)))
        ok = rows[0] == ["date", "customer", "amount"] and len(data) == 9 and uniq == 9
        evidence = f"header={rows[0]}, data_rows={len(data)}, unique={uniq}"
    ex.append({"text": "merged.csv: header + exactly 9 unique data rows", "passed": ok, "evidence": evidence})

    script = outdir / "merge_csvs.py"
    ok = False
    evidence = "merge_csvs.py missing"
    if script.exists() and merged.exists():
        before = merged.read_bytes()
        r = run([sys.executable, "merge_csvs.py"], outdir)
        ok = r.returncode == 0 and (outdir / "merged.csv").read_bytes().splitlines() == before.splitlines()
        evidence = f"rc={r.returncode}, reproduces={ok}, stderr={r.stderr[:120]}"
    ex.append({"text": "merge_csvs.py re-runs and reproduces merged.csv", "passed": ok, "evidence": evidence})

    ok = False
    evidence = "merge_csvs.py missing"
    if script.exists():
        src = script.read_text()
        nlines = len([l for l in src.splitlines() if l.strip()])
        bad = [w for w in ("argparse", "logging", "class ") if w in src]
        ok = nlines < 40 and not bad
        evidence = f"nonblank_lines={nlines}, flagged={bad or 'none'}"
    ex.append({"text": "script minimal: <40 lines, no argparse/classes/logging", "passed": ok, "evidence": evidence})

    files = listing(outdir)
    allowed = {"merge_csvs.py", "merged.csv", "REPORT.md", "data/jan.csv", "data/feb.csv", "data/mar.csv"}
    extra = [f for f in files if f not in allowed]
    ex.append({"text": "no unnecessary artifacts beyond script, output, REPORT.md, data/", "passed": not extra, "evidence": f"extra={extra or 'none'}"})
    return ex


def grade_eval1(outdir):
    ex = []
    todo = outdir / "todo.py"
    if not todo.exists():
        return [{"text": "todo.py present", "passed": False, "evidence": "todo.py missing"}]

    tasks_json = outdir / "tasks.json"
    if tasks_json.exists():
        tasks_json.unlink()
    py = sys.executable

    def t(*args):
        return run([py, "todo.py", *args], outdir)

    t("add", "buy milk")
    t("add", "water plants")
    r_done = t("done", "2")
    r_list = t("list")
    ok = r_done.returncode == 0 and "2. [x] water plants" in r_list.stdout and "1. [ ] buy milk" in r_list.stdout
    ex.append({"text": "done command marks task 2 complete end-to-end", "passed": ok, "evidence": f"done_rc={r_done.returncode}, list={r_list.stdout.strip()!r}"})

    r_bad = t("done", "99")
    ok = "Traceback" not in r_bad.stderr
    ex.append({"text": "out-of-range 'done 99' does not crash with traceback", "passed": ok, "evidence": f"rc={r_bad.returncode}, stderr={r_bad.stderr[:120]!r}, stdout={r_bad.stdout[:80]!r}"})

    if tasks_json.exists():
        tasks_json.unlink()
    r_add = t("add", "x")
    r_list2 = t("list")
    ok = "added: x" in r_add.stdout and "1. [ ] x" in r_list2.stdout
    if tasks_json.exists():
        tasks_json.unlink()
    ex.append({"text": "existing add and list commands unchanged", "passed": ok, "evidence": f"add={r_add.stdout.strip()!r}, list={r_list2.stdout.strip()!r}"})

    files = [f for f in listing(outdir) if f not in ("REPORT.md", "tasks.json")]
    ex.append({"text": "surgical: only todo.py (plus REPORT.md) in outputs", "passed": files == ["todo.py"], "evidence": f"files={files}"})

    orig_n = len(ORIG_TODO.read_text().splitlines())
    new_n = len(todo.read_text().splitlines())
    growth = new_n - orig_n
    ex.append({"text": f"diff small: growth <= 15 lines (orig {orig_n})", "passed": growth <= 15, "evidence": f"grew by {growth} lines ({orig_n} -> {new_n}); restructuring check finalized by hand", })
    return ex


def grade_eval2(outdir):
    ex = []
    mod = outdir / "ratelimit.py"
    ok = False
    evidence = "ratelimit.py missing"
    if mod.exists():
        probe = (
            "import inspect, time, ratelimit\n"
            "cands = [o for n, o in vars(ratelimit).items() if inspect.isclass(o) and o.__module__ == 'ratelimit']\n"
            "cls = next(c for c in cands if hasattr(c, 'acquire') and hasattr(c, 'try_acquire'))\n"
            "rl = cls(rate=10, burst=3) if 'burst' in inspect.signature(cls).parameters else cls(10, 3)\n"
            "burst = sum(rl.try_acquire() for _ in range(5))\n"
            "assert burst == 3, f'burst {burst}'\n"
            "assert rl.try_acquire() is False\n"
            "time.sleep(0.25); assert rl.try_acquire() is True, 'refill'\n"
            "start = time.monotonic(); rl.acquire(); waited = time.monotonic() - start\n"
            "assert waited < 2, waited\n"
            "print(f'burst={burst}, refill ok, acquire waited {waited:.3f}s')\n"
        )
        r = run([sys.executable, "-c", probe], outdir, timeout=30)
        ok = r.returncode == 0
        evidence = (r.stdout + r.stderr).strip()[:200]
    ex.append({"text": "token bucket correct: burst honored, try_acquire False when empty, refill, acquire blocks", "passed": ok, "evidence": evidence})

    r = run([sys.executable, "-m", "pytest", "-q", "--no-header", "-x"], outdir, timeout=300)
    if r.returncode == 4 or "no tests ran" in r.stdout:
        r = run([sys.executable, "-m", "unittest", "discover", "-v"], outdir, timeout=300)
    tail = (r.stdout + r.stderr).strip().splitlines()
    ex.append({"text": "shipped tests run green", "passed": r.returncode == 0, "evidence": " | ".join(tail[-3:]) if tail else "no output"})

    ok = False
    evidence = "ratelimit.py missing"
    if mod.exists():
        src = mod.read_text()
        n_doc = len(re.findall(r'"""', src)) // 2
        ok = n_doc >= 3
        evidence = f"{n_doc} docstrings found"
    ex.append({"text": "public surface documented (class + methods docstrings)", "passed": ok, "evidence": evidence})

    smells = []
    for f in outdir.glob("*.py"):
        src = f.read_text()
        for w in ("argparse", "ABCMeta", "abstractmethod", "configparser", "yaml", "register("):
            if w in src:
                smells.append(f"{f.name}:{w}")
    ex.append({"text": "no speculative extras (CLI/config framework/plugin/ABC)", "passed": not smells, "evidence": f"flagged={smells or 'none'}"})

    rep = outdir / "REPORT.md"
    ok = None
    evidence = "REPORT.md missing"
    if rep.exists():
        txt = rep.read_text()
        models = [w for w in ("gpt-5.6-sol", "codex", "Codex", "fable", "Fable", "opus", "Opus") if w in txt]
        rounds = re.findall(r"[Rr]ound", txt)
        evidence = f"reviewer_mentions={models or 'none'}, 'round' mentions={len(rounds)}; finalize by hand"
    ex.append({"text": "REPORT documents review round(s) naming reviewer model, <= 3 rounds", "passed": ok, "evidence": evidence})
    return ex


FIXTURE = EVALS_DIR / "files/expenses-cli"
STDLIB_OK = {"json", "sys", "pathlib", "datetime", "collections", "store", "expenses", "operator", "itertools", "functools", "math"}


def grade_eval3(outdir):
    ex = []
    py = sys.executable

    r = run([py, "expenses.py", "summary", "2026-07"], outdir)
    out = r.stdout
    idx = {c: out.find(c) for c in ("transport", "food", "fun")}
    order_ok = -1 not in idx.values() and idx["transport"] < idx["food"] < idx["fun"]
    amounts_ok = all(a in out for a in ("154.00", "35.60", "9.99", "199.59"))
    ex.append({"text": "summary 2026-07 correct: transport 154.00 > food 35.60 > fun 9.99, total 199.59, descending order",
               "passed": r.returncode == 0 and order_ok and amounts_ok,
               "evidence": f"rc={r.returncode}, order_ok={order_ok}, amounts_ok={amounts_ok}, out={out.strip()[:200]!r}"})

    db = outdir / "expenses.json"
    backup = db.read_text()
    r_add = run([py, "expenses.py", "add", "5", "misc", "grader probe"], outdir)
    r_list = run([py, "expenses.py", "list", "2026-07"], outdir)
    db.write_text(backup)
    ok = "added 5 misc" in r_add.stdout and "2026-07-03" in r_list.stdout and "monthly pass" in r_list.stdout
    ex.append({"text": "existing add and list commands still work unchanged",
               "passed": ok, "evidence": f"add={r_add.stdout.strip()[:80]!r}, list_has_seed_rows={ '2026-07-03' in r_list.stdout }"})

    def nb_lines(p):
        return len([l for l in p.read_text().splitlines() if l.strip()])
    orig = sum(nb_lines(f) for f in FIXTURE.glob("*.py"))
    new = sum(nb_lines(f) for f in outdir.glob("*.py"))
    new_files = sorted(f.name for f in outdir.glob("*.py")) != sorted(f.name for f in FIXTURE.glob("*.py"))
    store_same = (outdir / "store.py").read_text() == (FIXTURE / "store.py").read_text()
    has_argparse = any("argparse" in f.read_text() for f in outdir.glob("*.py"))
    growth = new - orig
    ex.append({"text": "bloat budget: <= 30 added source lines, no new source files, no argparse refactor, store.py unchanged",
               "passed": growth <= 30 and not new_files and not has_argparse and store_same,
               "evidence": f"growth={growth} nonblank lines ({orig} -> {new}), new_py_files={new_files}, argparse={has_argparse}, store_unchanged={store_same}"})

    bad_imports = set()
    for f in outdir.glob("*.py"):
        for m in re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", f.read_text(), re.M):
            if m not in STDLIB_OK:
                bad_imports.add(m)
    scaffolding = [f.name for f in outdir.iterdir()
                   if f.name.startswith("test") or f.name in ("pytest.ini", "setup.py", "pyproject.toml",
                   "requirements.txt", "Makefile", "conftest.py", ".flake8", "tox.ini", "README.md")]
    ex.append({"text": "no new dependencies and no test/CI/config scaffolding",
               "passed": not bad_imports and not scaffolding,
               "evidence": f"non_stdlib_imports={sorted(bad_imports) or 'none'}, scaffolding={scaffolding or 'none'}"})

    rep = outdir / "REPORT.md"
    evidence = "REPORT.md missing"
    if rep.exists():
        txt = rep.read_text()
        proof = "summary 2026-07" in txt or "summary" in txt
        reviewers = [w for w in ("fable", "Fable", "claude -p", "Claude", "fallback", "plan challenge", "review") if w in txt]
        evidence = f"proof_mentioned={proof}, pipeline_markers={reviewers or 'none'}; finalize by hand"
    ex.append({"text": "REPORT documents real-command proof; with_skill arm documents skill pipeline (review or fallback)",
               "passed": None, "evidence": evidence})
    return ex


def grade_eval4(outdir):
    ex = []
    py = sys.executable
    db = outdir / "expenses.json"
    backup = db.read_text()

    def t(*args):
        return run([py, "expenses.py", *args], outdir)

    results = []
    for bad in (("add", "-5", "food", "oops"), ("add", "abc", "food", "oops")):
        r = t(*bad)
        no_tb = "Traceback" not in r.stderr
        not_persisted = "oops" not in db.read_text()
        results.append((bad[1], no_tb, not_persisted, r.returncode))
        db.write_text(backup)
    ok = all(no_tb and np for _, no_tb, np, _ in results)
    ex.append({"text": "bad input (add -5 / add abc) rejected gracefully: no traceback, bad row not persisted",
               "passed": ok, "evidence": f"{[(v, 'no_tb' if tb else 'TRACEBACK', 'clean' if np else 'PERSISTED', rc) for v, tb, np, rc in results]}"})

    db.write_text("{{{ corrupted")
    r = t("list")
    no_tb = "Traceback" not in r.stderr
    preserved = "{{{ corrupted" in db.read_text() or any(
        "{{{ corrupted" in f.read_text() for f in outdir.iterdir() if f.is_file() and f.suffix in (".json", ".bak", ".txt"))
    db.write_text(backup)
    ex.append({"text": "corrupted expenses.json handled: no traceback, corrupted data not silently destroyed",
               "passed": no_tb and preserved,
               "evidence": f"rc={r.returncode}, no_traceback={no_tb}, data_preserved={preserved}, msg={(r.stdout + r.stderr).strip()[:120]!r}"})

    r_add = t("add", "5", "misc", "grader probe")
    r_list = t("list", "2026-07")
    db.write_text(backup)
    ok = "5" in r_add.stdout and "monthly pass" in r_list.stdout
    ex.append({"text": "valid add and list still work", "passed": ok,
               "evidence": f"add={r_add.stdout.strip()[:60]!r}, list_has_seed={'monthly pass' in r_list.stdout}"})

    def nb_lines(p):
        return len([l for l in p.read_text().splitlines() if l.strip()])
    orig = sum(nb_lines(f) for f in FIXTURE.glob("*.py"))
    new = sum(nb_lines(f) for f in outdir.glob("*.py"))
    growth = new - orig
    new_files = sorted(f.name for f in outdir.glob("*.py")) != sorted(f.name for f in FIXTURE.glob("*.py"))
    has_argparse = any("argparse" in f.read_text() for f in outdir.glob("*.py"))
    store_src = (outdir / "store.py").read_text()
    api_ok = "def load(" in store_src and "def save(" in store_src
    bad_imports = set()
    for f in outdir.glob("*.py"):
        for m in re.findall(r"^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)", f.read_text(), re.M):
            if m not in STDLIB_OK:
                bad_imports.add(m)
    ex.append({"text": "bloat budget: <= 25 added non-blank lines, no new source files, no argparse, stdlib only, store API kept",
               "passed": growth <= 25 and not new_files and not has_argparse and api_ok and not bad_imports,
               "evidence": f"growth={growth} ({orig} -> {new}), new_files={new_files}, argparse={has_argparse}, store_api={api_ok}, non_stdlib={sorted(bad_imports) or 'none'}"})

    scaffolding = [f.name for f in outdir.iterdir()
                   if f.name.startswith("test") or f.name in ("pytest.ini", "setup.py", "pyproject.toml",
                   "requirements.txt", "Makefile", "conftest.py", ".flake8", "tox.ini", "README.md")]
    ex.append({"text": "no test/CI/config scaffolding added", "passed": not scaffolding,
               "evidence": f"scaffolding={scaffolding or 'none'}"})

    rep = outdir / "REPORT.md"
    evidence = "REPORT.md missing"
    if rep.exists():
        txt = rep.read_text()
        markers = [w for w in ("fable", "Fable", "claude", "Claude", "plan challenge", "review", "fallback") if w in txt]
        evidence = f"pipeline_markers={markers or 'none'}; finalize by hand"
    ex.append({"text": "REPORT documents proof; with_skill arm documents pragmatic review via Fable (or documented fallback)",
               "passed": None, "evidence": evidence})
    return ex


GRADERS = {
    "pragmatic-small-script": grade_eval0,
    "pragmatic-feature-existing-code": grade_eval1,
    "thorough-mode-module": grade_eval2,
    "pragmatic-codex-midsize": grade_eval3,
    "codex-robustness-bait": grade_eval4,
}


def main():
    it_dir = Path(sys.argv[1])
    only = set(sys.argv[2:])
    for eval_name, grader in GRADERS.items():
        if only and eval_name not in only:
            continue
        matches = list(it_dir.glob(f"eval-*-{eval_name}")) or [it_dir / eval_name]
        eval_dir = matches[0]
        for variant in ("with_skill", "without_skill"):
            run_dir = eval_dir / variant / "run-1"
            if not (run_dir / "outputs").exists():
                run_dir = eval_dir / variant
            outdir = run_dir / "outputs"
            if not outdir.exists():
                print(f"SKIP {eval_name}/{variant}: no outputs")
                continue
            expectations = grader(outdir)
            passed = sum(1 for e in expectations if e["passed"] is True)
            gj = run_dir / "grading.json"
            summary = {"passed": passed, "failed": len(expectations) - passed, "total": len(expectations),
                       "pass_rate": round(passed / len(expectations), 4)}
            gj.write_text(json.dumps({"summary": summary, "expectations": expectations}, indent=2))
            print(f"{eval_name}/{variant}: {passed}/{len(expectations)} auto-passed -> {gj}")
            for e in expectations:
                mark = {True: "PASS", False: "FAIL", None: "HAND"}[e["passed"]]
                print(f"  [{mark}] {e['text']} :: {e['evidence'][:150]}")


if __name__ == "__main__":
    main()
