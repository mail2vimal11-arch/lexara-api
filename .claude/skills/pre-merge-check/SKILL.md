# /pre-merge-check

Run before opening a PR. Catches the most common merge-blockers specific to Lexara.

## Steps

Run all checks, then report a PASS / FAIL / WARN summary.

### 1. Tests
```bash
pytest tests/ -v --tb=short
```
**FAIL** if any test exits non-zero (excluding `|| true` suppression — check actual output).

### 2. New TODOs in diff
```bash
git diff main...HEAD -- '*.py' | grep "^+" | grep -i "TODO\|FIXME\|HACK"
```
**WARN** if any new TODO/FIXME lines were added. List them. (Existing ones are tracked — new ones need a ticket or inline resolution.)

### 3. No secrets in diff
```bash
git diff main...HEAD | grep -iE "sk-ant-|Bearer [a-zA-Z0-9_\-]{20,}|password\s*=\s*['\"][^'\"]{6,}"
```
**FAIL** if any matches. These patterns catch Claude API keys, bearer tokens, and hardcoded passwords.

### 4. Billing TODO count unchanged
```bash
grep -c "TODO" app/routers/billing.py
```
**WARN** if count is > 6 (the known baseline). A reduction is good — report it.
**FAIL** if count increased (new TODOs added to billing).

### 5. Auth files untouched
```bash
git diff main...HEAD -- app/middleware/auth.py app/security.py
```
**FAIL** if either file appears in the diff. These require a separate security review; they must not land in a feature PR.

### 6. No direct `alembic downgrade` in scripts
```bash
git diff main...HEAD | grep "alembic downgrade"
```
**FAIL** if found in any changed file.

### 7. requirements.txt consistent
```bash
git diff main...HEAD -- requirements.txt
```
**WARN** if changed — list the added/removed packages so the reviewer can eyeball them.

---

## Report Format

```
Pre-merge check — {branch} → main
{date}

✅ Tests passed (N passed, 0 failed)   or   ❌ Tests FAILED (N failed)
✅ No new TODOs                         or   ⚠️  N new TODO(s): {list}
✅ No secrets detected                  or   ❌ Possible secret on line {N}: {snippet}
✅ Billing TODO count stable (6)        or   ⚠️  Billing TODOs: {count} (was 6)
✅ Auth files untouched                 or   ❌ Auth file modified — needs security review
✅ No alembic downgrade                 or   ❌ alembic downgrade found — needs approval
✅ requirements.txt unchanged           or   ⚠️  requirements.txt changed: {diff summary}

VERDICT: ✅ READY TO PR  |  ⚠️ REVIEW NEEDED  |  ❌ DO NOT MERGE
```

A single ❌ = DO NOT MERGE. One or more ⚠️ with no ❌ = REVIEW NEEDED (human decides). All ✅ = READY TO PR.
