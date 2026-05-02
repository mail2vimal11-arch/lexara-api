# /status-report

Produces a standup-style status report for the Lexara project.

## Steps

1. Read `PROJECT_STATUS.md` — extract Done / In Progress / Blocked / Next Up.
2. Run `git log --oneline -10` — summarise what changed since the last status report.
3. Run `grep -rn "TODO\|FIXME\|HACK" app/ --include="*.py"` — count and list open TODOs.
4. Check `app/routers/billing.py` and `app/routers/usage.py` for the known billing TODOs specifically.
5. Report in this format:

---

## Lexara Status — {date}

**DONE (recent):**
- {bullet per recently completed item from git log or PROJECT_STATUS.md}

**IN PROGRESS:**
- {bullet per in-flight task with owning session}

**BLOCKED:**
- {bullet per blocked item with blocker description}

**NEXT UP:**
- {top 2–3 items from PROJECT_STATUS.md Next Up list}

**Open TODOs:** {count} total — {count} in billing (critical), {count} elsewhere

**Notes:**
- {any anomaly or decision worth flagging}

---

Keep the report under 30 lines. Do not dump raw file contents.
