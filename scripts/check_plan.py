"""Validate PLAN.md: dependency graph and file ownership.

Checks that every task line parses, task IDs are unique, every dependency
exists, every task but T0 depends on T0, there are no cycles or
transitively-implied dependencies, and no two tasks that could run at the
same time own overlapping files (a [blocked] task is skipped for that check
until it is unblocked).

Usage: python3 scripts/check_plan.py [--waves] [PLAN.md]   (exit 1 on any problem)

--waves also prints the unfinished tasks grouped into waves: every task in a
wave has all its dependencies done or in earlier waves. [blocked] tasks, and
tasks that depend on one, are listed separately as blocked.
"""

import itertools
import re
import sys

LINE = re.compile(
    r"- \[(todo|doing|done|blocked)\] \| (\w+) \| (.*?) \| deps: (.*?) \| owns: (.*?) \| check:"
)
# Anything that looks like a task line, so a typo is reported instead of skipped.
TASK_LIKE = re.compile(r"- \[\w*\] \|")


def parse(path):
    tasks, problems = {}, []
    for n, line in enumerate(open(path, encoding="utf-8"), start=1):
        m = LINE.match(line)
        if not m:
            if TASK_LIKE.match(line):
                problems.append(f"line {n}: task line does not parse: {line.strip()[:70]}")
            continue
        status, tid, _title, deps, owns = m.groups()
        if tid in tasks:
            problems.append(f"line {n}: duplicate task ID {tid}")
        tasks[tid] = {
            "status": status,
            "deps": [d.strip() for d in deps.split(",") if d.strip() not in ("—", "")],
            "owns": re.findall(r"`([^`]+)`", owns),
        }
    return tasks, problems


def ancestors(tasks, tid, memo):
    if tid not in memo:
        memo[tid] = set()  # guards against infinite recursion on cycles
        found = set()
        for d in tasks[tid]["deps"]:
            if d in tasks:
                found |= {d} | ancestors(tasks, d, memo)
        memo[tid] = found
    return memo[tid]


def overlaps(a, b):
    """True if two owned paths could refer to the same file.

    A trailing '/' means a directory; a '*' glob is compared by its literal prefix.
    """
    a_prefix, b_prefix = a.split("*")[0], b.split("*")[0]
    if "*" in a or "*" in b:
        return a_prefix.startswith(b_prefix) or b_prefix.startswith(a_prefix)
    a, b = a.rstrip("/"), b.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def waves(tasks, anc):
    """Group unfinished tasks by the longest chain of unfinished deps below them."""
    level = {}
    blocked = {t for t in tasks if tasks[t]["status"] == "blocked"}
    for tid in sorted(tasks, key=lambda t: len(anc[t])):
        if tid in blocked or anc[tid] & blocked:
            continue
        open_deps = [d for d in tasks[tid]["deps"] if d in tasks and tasks[d]["status"] != "done"]
        if tasks[tid]["status"] != "done":
            level[tid] = 1 + max((level.get(d, 0) for d in open_deps), default=0)
    grouped = {}
    for tid, lv in level.items():
        grouped.setdefault(lv, []).append(tid)
    return [sorted(grouped[lv], key=lambda t: list(tasks).index(t)) for lv in sorted(grouped)]


def main(argv):
    show_waves = "--waves" in argv
    args = [a for a in argv if a != "--waves"]
    path = args[0] if args else "PLAN.md"
    tasks, problems = parse(path)

    for tid, t in tasks.items():
        problems += [f"{tid}: unknown dep {d}" for d in t["deps"] if d not in tasks]
        if tid != "T0" and "T0" not in t["deps"]:
            problems.append(f"{tid}: does not depend on T0")

    memo = {}
    anc = {tid: ancestors(tasks, tid, memo) for tid in tasks}
    problems += [f"{tid}: dependency cycle" for tid in tasks if tid in anc[tid]]

    for tid, t in tasks.items():
        for d in t["deps"]:
            if d != "T0" and any(d in anc.get(e, ()) for e in t["deps"] if e != d):
                problems.append(f"{tid}: dep {d} is already implied by another dep")

    for x, y in itertools.combinations(tasks, 2):
        if x in anc[y] or y in anc[x]:
            continue  # ordered by dependencies, so never concurrent
        if "blocked" in (tasks[x]["status"], tasks[y]["status"]):
            continue  # a blocked task cannot run; re-checked once it is unblocked
        for a in tasks[x]["owns"]:
            for b in tasks[y]["owns"]:
                if overlaps(a, b):
                    problems.append(f"{x} and {y} can run concurrently but both own {a} / {b}")

    print(f"{len(tasks)} tasks checked")
    for p in problems:
        print("PROBLEM:", p)
    if not problems:
        print("OK: no problems found")
        if show_waves:
            for n, wave in enumerate(waves(tasks, anc), start=1):
                print(f"wave {n}: {', '.join(wave)}")
            stuck = [t for t in tasks if tasks[t]["status"] == "blocked"
                     or any(tasks[a]["status"] == "blocked" for a in anc[t])]
            if stuck:
                print(f"blocked: {', '.join(stuck)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
