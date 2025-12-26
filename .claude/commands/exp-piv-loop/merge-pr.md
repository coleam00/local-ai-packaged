---
description: Merge PR after ensuring it's up-to-date with main
argument-hint: [pr-number] (default: current branch's PR)
---

# Merge PR

**PR**: $ARGUMENTS (default: PR for current branch)

---

## Phase 1: Get PR Info

```bash
# If no argument, find PR for current branch
gh pr view --json number,title,state,baseRefName,headRefName,mergeable,mergeStateStatus

# Or with specific PR number
gh pr view $ARGUMENTS --json number,title,state,baseRefName,headRefName,mergeable,mergeStateStatus
```

Extract:
- PR number and title
- Current state (open?)
- Mergeable status
- Merge state (behind, clean, etc.)

---

## Phase 2: Check If Update Needed

```bash
# Check merge status
gh pr view $ARGUMENTS --json mergeStateStatus
```

**If `mergeStateStatus` is:**
- `CLEAN` → Ready to merge, skip to Phase 4
- `BEHIND` → Needs rebase, go to Phase 3
- `BLOCKED` → Check why (failing checks, reviews needed)
- `DIRTY` → Has conflicts, go to Phase 3

---

## Phase 3: Rebase If Behind Main

### 3.1 Checkout the PR Branch

```bash
# Get the branch name
gh pr view $ARGUMENTS --json headRefName --jq '.headRefName'

# Checkout the branch
gh pr checkout $ARGUMENTS
# or
git checkout <branch-name>
```

### 3.2 Rebase onto Main

```bash
# Fetch latest
git fetch origin main

# Rebase
git rebase origin/main
```

### 3.3 Resolve Conflicts (If Any)

If conflicts occur:
```bash
# 1. Check which files have conflicts
git status

# 2. Open and resolve each conflicted file
#    Look for <<<<<<< HEAD markers

# 3. After resolving each file
git add <resolved-file>

# 4. Continue rebase
git rebase --continue

# 5. Repeat until complete
```

### 3.4 Re-validate After Rebase

```bash
# Must pass before pushing
npm run type-check
npm run lint
npm run test
npm run build
```

### 3.5 Force Push Rebased Branch

```bash
# Use --force-with-lease for safety
git push --force-with-lease origin HEAD
```

### 3.6 Wait for CI (If Applicable)

```bash
# Check PR status
gh pr checks $ARGUMENTS

# Wait for checks to pass (optional)
gh pr checks $ARGUMENTS --watch
```

---

## Phase 4: Merge the PR

### 4.1 Final Check

```bash
# Verify PR is ready
gh pr view $ARGUMENTS --json mergeable,mergeStateStatus
```

### 4.2 Merge

```bash
# Squash merge (cleaner history)
gh pr merge $ARGUMENTS --squash --delete-branch

# Or regular merge
gh pr merge $ARGUMENTS --merge --delete-branch

# Or rebase merge
gh pr merge $ARGUMENTS --rebase --delete-branch
```

---

## Phase 5: Cleanup

### 5.1 Switch to Main

```bash
git checkout main
git pull origin main
```

### 5.2 Clean Up Local Branch

```bash
# Delete the merged branch locally (if still exists)
git branch -d <branch-name>

# Prune remote tracking branches
git fetch --prune
```

---

## Output

```markdown
## PR Merged

**PR**: #[NUMBER] - [TITLE]
**Merge type**: [squash/merge/rebase]

### Status
- ✅ PR was up-to-date (or rebased successfully)
- ✅ All checks passed
- ✅ Merged to main
- ✅ Branch deleted

### Now on main
```bash
git log --oneline -3
```

### Next
Ready for next task.
```

---

## Handling Edge Cases

### PR has conflicts that can't be auto-resolved
- Checkout the branch
- Manually resolve conflicts
- Re-validate
- Push
- Then merge

### CI checks are failing
- Do NOT merge
- Report which checks are failing
- Suggest fixing or investigating

### PR needs review approval
- Report this
- Do not merge without required approvals

### Branch protection rules block merge
- Report the blocking rule
- Suggest appropriate action

---

## Critical Reminders

1. **Always check merge status first.** Don't try to merge a PR that's behind.

2. **Rebase, don't merge main into branch.** Keeps history clean.

3. **Re-validate after rebase.** Conflicts or changes from main could break things.

4. **Use --force-with-lease.** Safer than --force, prevents overwriting others' work.

5. **Delete branch after merge.** Keeps repo clean.

6. **Verify merge succeeded.** Check main has the changes.
