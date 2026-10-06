## Execution rules
- PLAN.md is the source of truth. Re-read it before assigning work.
- Treat any [doing] task as interrupted: check git state and finish it.
- Run tasks whose deps are all [done] in parallel, max 3 at a time, following
  the browser, exclusive and timed-task rules in PLAN.md's "Scheduling".
  `python3 scripts/check_plan.py --waves` prints the current order.
  Use the builder agent for build tasks and qa-tester for QA tasks.
- Teammates only edit files their task owns. Shared interfaces live in
  docs/CONTRACTS.md; message the affected teammate before changing one.
- On finishing a task: the teammate runs its check, commits, and reports the
  check output to the lead. Only the lead edits PLAN.md: it marks the task [done].
- If stuck after 2 attempts, mark it [blocked] with a one-line reason and move on.

## Project language and decisions
- Use the terms in CONTEXT.md for all names: files, functions, variables, UI text.
- Check the ADRs before changing a recorded decision. Changing one is a
  scope change: mark the task [blocked] instead.

## Replanning (lead only)
- You may split tasks, add bug-fix tasks, and correct deps or file ownership.
- Log every change under "## Plan changes" at the bottom of PLAN.md:
  date, what changed, why.
- Never change scope from SPEC.md on your own. If a change would alter scope,
  mark the affected task [blocked] with the reason and continue with other work.
  Scope changes the user approves are recorded in SPEC.md's change log.
- Consult the advisor before any replan and before declaring the plan done.

## Engineering skills
- Build features with the tdd skill: one vertical slice at a time, failing test first.
- When a test or QA check fails and the cause isn't obvious, use diagnosing-bugs.

## QA rules
- QA tasks: start JupyterLab and the static server as PLAN.md's "Shared runtime
  resources" describes, test the feature with the tools in PLAN.md's Tooling
  section, and write everything to qa/<task-id>/ (report.md and screenshots;
  scratch files in qa/<task-id>/scratch/).
- QA fixes nothing: report each bug to the lead, who adds a bug-fix task as
  PLAN.md's "Bug-fix tasks" rule describes.
- Only one teammate uses the browser at a time.
- Stop JupyterLab and the static server when the QA task is finished.

## Tools
- Never install MCP servers or edit .mcp.json. If a task needs a missing
  tool, mark it [blocked] naming the tool.