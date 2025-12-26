---
description: Clean up git worktrees after PR merge - removes directory, kills ports, optionally deletes branches
argument-hint: <branch-name|all|merged> [--delete-branches]
---

# Worktree Cleanup

**Target**: $1 (branch name, "all", or "merged")
**Options**: $2 (blank = worktree only, "--delete-branches" = also delete local+remote branches)

---

## Purpose

Complete the worktree lifecycle by cleaning up after a PR is merged:
- Kill processes on worktree ports
- Remove worktree directory
- Prune stale git references
- Optionally delete local and remote branches

---

## Safety First

Before removing anything, check:

1. **Not currently in the worktree** - Can't remove if we're inside it
2. **PR status** - Warn if PR is still open or doesn't exist
3. **Uncommitted changes** - Warn if worktree has uncommitted work
4. **Confirm branch exists** - Don't error on already-deleted branches

---

## Cleanup Modes

### Single Worktree: `/worktree-cleanup branch-name`

Clean up one specific worktree.

### All Worktrees: `/worktree-cleanup all`

Clean up ALL worktrees in the `worktrees/` directory.

### Merged Only: `/worktree-cleanup merged`

Smart cleanup - only removes worktrees whose PRs have been merged.

---

## Step-by-Step Process

### Step 1: Identify Target Worktrees

```bash
# List all worktrees
git worktree list

# For single target
WORKTREE_PATH="worktrees/$1"

# For 'all' - get all worktrees except main
git worktree list --porcelain | grep "worktree " | grep "worktrees/" | sed 's/worktree //'

# For 'merged' - check each worktree's PR status
```

### Step 2: For Each Worktree, Check Safety

```bash
# Check if worktree exists
if [ ! -d "$WORKTREE_PATH" ]; then
  echo "Worktree does not exist: $WORKTREE_PATH"
  # Continue to branch cleanup if requested
fi

# Check for uncommitted changes
cd "$WORKTREE_PATH" && git status --porcelain
# If output not empty, warn user

# Check current directory - can't remove if we're inside
pwd | grep -q "$WORKTREE_PATH" && echo "ERROR: Currently inside worktree"
```

### Step 3: Check PR Status (if GitHub available)

```bash
# Get branch name from worktree
BRANCH=$(cd "$WORKTREE_PATH" && git branch --show-current)

# Check if PR exists and its status
gh pr list --head "$BRANCH" --state all --json number,state,mergedAt

# Interpret:
# - state: "MERGED" → Safe to delete everything
# - state: "OPEN" → Warn: PR still open
# - state: "CLOSED" (not merged) → Warn: PR closed without merge
# - No PR found → Warn: No PR exists for this branch
```

### Step 4: Kill Processes on Worktree Ports

```bash
# Kill any process on ports 8124-8128 that might be from this worktree
for port in 8124 8125 8126 8127 8128; do
  lsof -ti:$port | xargs kill -9 2>/dev/null
done
```

### Step 5: Remove Worktree

```bash
# Go to main repo first
cd /path/to/main/repo

# Remove worktree
git worktree remove "$WORKTREE_PATH"

# If that fails (dirty/locked), force it
git worktree remove --force "$WORKTREE_PATH"

# Prune stale references
git worktree prune
```

### Step 6: Branch Cleanup (if --delete-branches)

Only if `$2` is `--delete-branches`:

```bash
# Delete local branch
git branch -d "$BRANCH"

# If not merged, force delete
git branch -D "$BRANCH"

# Delete remote branch (if exists)
git push origin --delete "$BRANCH" 2>/dev/null || echo "Remote branch already deleted or doesn't exist"
```

---

## Output Format

### Single Worktree Cleanup

```markdown
## Worktree Cleaned Up

**Branch**: fix/my-feature
**Worktree**: worktrees/fix/my-feature
**PR Status**: ✅ Merged (#23)

### Actions Taken
- [x] Killed processes on ports 8124-8128
- [x] Removed worktree directory
- [x] Pruned git references
- [x] Deleted local branch (--delete-branches)
- [x] Deleted remote branch (--delete-branches)

### Verification
```bash
git worktree list  # Should not show this worktree
git branch -a | grep fix/my-feature  # Should return nothing
```
```

### All/Merged Cleanup

```markdown
## Worktrees Cleaned Up

| Branch | PR Status | Worktree | Local Branch | Remote Branch |
|--------|-----------|----------|--------------|---------------|
| fix/bug-1 | ✅ Merged #20 | ✅ Removed | ✅ Deleted | ✅ Deleted |
| fix/bug-2 | ✅ Merged #21 | ✅ Removed | ✅ Deleted | ✅ Deleted |
| feat/new | ⚠️ Open #25 | ⏭️ Skipped | ⏭️ Kept | ⏭️ Kept |

### Summary
- Cleaned: 2 worktrees
- Skipped: 1 worktree (PR still open)
```

---

## Decision Logic

### When to Remove Worktree

| PR Status | Worktree | Local Branch | Remote Branch |
|-----------|----------|--------------|---------------|
| Merged | ✅ Remove | ✅ Safe to delete | ✅ Safe to delete |
| Open | ⚠️ Warn, ask | ⚠️ Keep | ⚠️ Keep |
| Closed (no merge) | ⚠️ Warn, ask | ⚠️ Might want to keep | ⚠️ Keep |
| No PR | ✅ Remove | ⚠️ Ask | N/A |

### Uncommitted Changes

```
⚠️ Worktree has uncommitted changes:
   M src/file.ts
   ?? new-file.ts

Options:
1. Commit or stash changes first
2. Use --force to discard changes
3. Cancel cleanup
```

---

## Example Usage

### Clean up single merged worktree
```bash
/worktree-cleanup fix/flaky-tests
```

### Clean up and delete branches
```bash
/worktree-cleanup fix/flaky-tests --delete-branches
```

### Clean up all worktrees
```bash
/worktree-cleanup all
```

### Clean up only merged worktrees
```bash
/worktree-cleanup merged --delete-branches
```

---

## Edge Cases

### Worktree doesn't exist but branch does
- Skip worktree removal
- Still delete branches if `--delete-branches`

### Branch already deleted
- Don't error
- Report as "already cleaned"

### Currently inside the worktree
- Error and exit
- User must `cd` to main repo first

### No GitHub CLI / Can't check PR status
- Warn that PR status couldn't be verified
- Proceed with cleanup anyway

---

## Lifecycle Complete

After cleanup, the worktree lifecycle is complete:

```
Phase          | Command                         | Status
---------------|--------------------------------|--------
1. Creation    | /worktree branch-name           | ✅
2. Development | Work in worktrees/branch-name   | ✅
3. PR Creation | gh pr create / manual           | ✅
4. Review      | Wait for approval               | ✅
5. Merge       | gh pr merge / manual            | ✅
6. Cleanup     | /worktree-cleanup branch-name   | ✅
```

Now execute the cleanup based on the target specified.
