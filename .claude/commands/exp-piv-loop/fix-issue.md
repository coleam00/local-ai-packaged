---
description: Fix a GitHub issue end-to-end - investigate, fix, test, and create PR
argument-hint: <issue-number or github-url>
---

# Fix GitHub Issue

**Input**: $ARGUMENTS (issue number like `123` or full URL)

---

## Your Mission

Take a GitHub issue from report to resolution. You are autonomous:

1. **Fetch** the issue and understand what's broken
2. **Investigate** the codebase to find the root cause
3. **Fix** the issue with minimal, pattern-following code
4. **Test** thoroughly - automated and manual validation
5. **PR** with proper description linked to the issue

**Golden Rule**: Complete the entire workflow. The human reviews the PR, not your intermediate steps.

---

## Phase 1: Fetch and Validate Issue

### 1.1 Get Issue Details

```bash
# If input is a number
gh issue view $ARGUMENTS --json title,body,state,labels,comments,assignees,url

# If input is a URL, extract the number first
```

Extract:
- **Title**: What's the reported problem?
- **Body**: Reproduction steps, expected vs actual behavior
- **Labels**: Is this a bug? Enhancement?
- **Comments**: Any additional context or discussion?
- **State**: Is it still open?

### 1.2 Validate It's Fixable

**Proceed if:**
- Issue is open
- It's a bug or fixable problem (not a feature request needing PRD)
- No existing PR already linked

**Stop and report if:**
- Issue is closed → "Issue already closed"
- It's a large feature request → "This needs `/plan` not `/fix-issue`"
- PR already exists → "PR #X already addresses this issue"
- Issue is unclear → Ask for clarification (but try to proceed if possible)

### 1.3 Parse the Problem

From the issue, extract:
```markdown
**Symptom**: [What's happening that shouldn't]
**Expected**: [What should happen instead]
**Reproduction**: [Steps to trigger the bug]
**Environment**: [Any version/config specifics mentioned]
```

---

## Phase 2: Branch Setup

### 2.1 Check Current State

```bash
# What branch are we on?
git branch --show-current

# Is working directory clean?
git status --porcelain

# Are we up to date with remote?
git fetch origin
git status
```

### 2.2 Create or Use Fix Branch

**If on main/master:**
```bash
# Create descriptive branch name
git checkout -b fix/issue-{number}-{brief-description}

# Example: fix/issue-123-ssh-url-clone-error
```

**If already on a fix/feature branch:**
- Use current branch (assume it's for this work)
- Note this in your report

**If working directory is dirty:**
- Stash or commit existing changes first
- Or note the risk and proceed carefully

### 2.3 Ensure Up-to-Date

```bash
git pull origin main --rebase
# or
git merge origin/main
```

---

## Phase 3: Investigate (RCA-Lite)

### 3.1 Search for Relevant Code

Based on the issue description:
- Search for error messages mentioned
- Find files/functions mentioned
- Look for related code paths

```bash
# Search for keywords from the issue
rg "error message from issue"
rg "function name mentioned"
```

### 3.2 Form Hypothesis

Based on what you find:
- What's the likely cause?
- What code path leads to this behavior?
- What would fix it?

### 3.3 Validate Hypothesis

- Read the relevant code
- Trace the execution path
- Confirm your understanding
- If wrong, form new hypothesis

**If issue is unclear or can't reproduce:**
- Make your best judgment based on the code
- Note uncertainty in PR description
- Proceed with fix

---

## Phase 4: Implement the Fix

### 4.1 Make Changes

**Follow these principles:**
- Minimal change that fixes the issue
- Mirror existing codebase patterns
- No drive-by refactoring
- No scope creep

### 4.2 Add or Update Tests

**Required:**
- Add test that would have caught this bug
- Test should fail without fix, pass with fix

**Test naming:**
```typescript
it('should handle [edge case from issue]', () => {
  // Arrange: Set up the problematic scenario
  // Act: Trigger the bug
  // Assert: Verify correct behavior
});
```

### 4.3 Update Documentation (if needed)

- If the issue was caused by unclear docs, update them
- If behavior change is user-facing, document it

---

## Phase 5: Validate

### 5.1 Automated Checks

```bash
# All must pass
npm run type-check
npm run lint
npm run test
npm run build
```

### 5.2 Specific Validation

Based on the issue's reproduction steps:
- Can you still reproduce the bug? (Should be NO)
- Does the expected behavior now work? (Should be YES)

```bash
# Run specific test if mentioned in issue
npm test -- --grep "relevant test"

# Or manual validation
# [specific commands based on the issue]
```

### 5.3 Regression Check

- Run full test suite
- Check that related functionality still works
- Quick smoke test of main features if possible

---

## Phase 6: Commit and Push

### 6.1 Sync with Main (Rebase if Needed)

Before committing, ensure branch is up-to-date with main:

```bash
# Fetch latest
git fetch origin main

# Check if we're behind
git log HEAD..origin/main --oneline
```

**If behind main:**
```bash
# Rebase onto latest main
git rebase origin/main

# If conflicts, resolve them:
# 1. Fix conflicts in files
# 2. git add <resolved-files>
# 3. git rebase --continue

# After rebase, re-validate everything
npm run type-check
npm run lint
npm run test
npm run build
```

### 6.2 Stage Changes

```bash
git add -A
git status  # Verify what's being committed
```

### 6.3 Write Commit Message

Format:
```
Fix [brief description] (#ISSUE_NUMBER)

[Longer description of what was wrong and how it's fixed]

- [Change 1]
- [Change 2]

Fixes #ISSUE_NUMBER
```

Example:
```
Fix SSH URL handling in clone command (#123)

The clone command was incorrectly prepending https:// to SSH URLs,
resulting in invalid URLs like https://git@github.com:...

- Added SSH URL detection before authentication logic
- Convert git@github.com: to https://github.com/ format
- Added test for SSH URL handling

Fixes #123
```

### 6.4 Push

```bash
# Normal push
git push -u origin HEAD

# If you rebased, force push is needed
git push -u origin HEAD --force-with-lease
```

---

## Phase 7: Create Pull Request

### 7.1 Create PR with gh CLI

```bash
gh pr create \
  --title "Fix: [Brief description] (#ISSUE_NUMBER)" \
  --body "$(cat <<'EOF'
## Summary

[One paragraph: What was the bug and how did you fix it?]

## Changes

- [Change 1]
- [Change 2]

## Testing

- [x] Added test for [scenario]
- [x] All existing tests pass
- [x] Manual verification: [what you tested]

## Issue

Fixes #ISSUE_NUMBER

---
*Automated fix by Claude*
EOF
)"
```

### 7.2 Verify PR Created

```bash
gh pr view --web  # Opens PR in browser (optional)
gh pr view        # Show PR details
```

---

## Phase 8: Report Results

Output summary:

```markdown
## Issue Fixed

**Issue**: #[number] - [title]
**Branch**: `fix/issue-[number]-[description]`
**PR**: #[pr-number] - [pr-url]

### What Was Wrong
[Brief explanation of the root cause]

### What Was Fixed
[Brief explanation of the solution]

### Changes Made
| File | Change |
|------|--------|
| `path/to/file` | [description] |

### Validation
| Check | Result |
|-------|--------|
| Type check | ✅ |
| Lint | ✅ |
| Tests | ✅ |
| Build | ✅ |
| Manual | ✅ [what was tested] |

### Notes
[Any caveats, follow-ups, or things to watch]
```

---

## Handling Edge Cases

### Issue is vague or unclear
- Make your best interpretation
- Note assumptions in PR description
- Proceed with fix

### Can't reproduce the issue
- Fix based on code analysis
- Note "Could not reproduce, fixed based on code review" in PR
- Proceed

### Fix requires breaking changes
- Note in PR description
- Suggest it might need discussion
- Still create the PR for review

### Tests are already failing (before your changes)
- Note this in PR
- Don't fix unrelated test failures
- Focus on the issue at hand

### Multiple issues in one
- Fix the main issue
- Note related problems in PR
- Suggest follow-up issues if needed

---

## Critical Reminders

1. **Autonomous execution.** Complete the whole workflow, don't stop to ask.

2. **Minimal fix.** Solve the reported problem, nothing more.

3. **Tests are mandatory.** Add a test that validates the fix.

4. **Good PR description.** The reviewer should understand the problem and solution.

5. **Link to issue.** Use "Fixes #123" so GitHub auto-closes it on merge.

6. **Handle uncertainty.** If unclear, make a judgment call and document it.

7. **Complete the job.** Human reviews the PR, not intermediate steps.

Now fetch the issue and fix it end-to-end.
