---
description: Implement a fix based on an RCA report - validates, implements, and verifies
argument-hint: <path/to/RCA-report.md> [plan]
---

# Fix Implementation from RCA Report

**Report**: $1
**Mode**: $2 (blank = implement fix, "plan" = analyze and plan only, no changes)

---

## Phase 0: Branch Setup

Before making any changes, ensure you're on the correct branch:

```bash
# Check current branch
git branch --show-current

# Check if a fix branch already exists
git branch -a | grep -i fix
```

**If on main/master:**
1. Check if a branch for this fix already exists
2. If yes → `git checkout [branch-name]`
3. If no → Create one: `git checkout -b fix/[issue-name]`

**Branch naming**: `fix/[short-description]` (e.g., `fix/ssh-url-handling`, `fix/command-injection`)

---

## Your Mission

Implement the fix described in the RCA report. But you are NOT a blind executor. You are a thinking engineer who:

1. **Validates** the diagnosis before acting
2. **Understands** the full context, not just snippets
3. **Adapts** the conceptual fix to the actual codebase
4. **Verifies** the fix works before declaring success

**Golden Rule**: If the RCA report's proposed fix doesn't make sense after you read the actual code, STOP and explain why. Don't implement a bad fix.

---

## Phase 1: Parse the RCA Report

Read the report at `$1` and extract:

1. **Root Cause**: What is the actual problem?
2. **Evidence Chain**: How was this diagnosed?
3. **Files to Modify**: Which files need changes?
4. **Fix Specification**: What conceptually needs to change?
5. **Implementation Guidance**: Code patterns/examples provided
6. **Verification Steps**: How to confirm the fix works

Summarize your understanding in 2-3 sentences. What are you fixing and why?

---

## Phase 2: Validate the Diagnosis

**Do NOT skip this phase.** The RCA was written by another agent/human who may have made mistakes.

### 2.1 Read the Actual Code

For each file mentioned in the report:
- Read the FULL file (or relevant sections), not just the lines mentioned
- Verify the problematic code still exists (hasn't already been fixed)
- Understand the surrounding context

### 2.2 Verify the Evidence

For each claim in the evidence chain:
- Does this actually match what you see in the code?
- Is the logic sound?
- Are there any errors in the diagnosis?

### 2.3 Sanity Check the Fix

Ask yourself:
- Does the proposed fix actually address the root cause?
- Could this fix introduce new bugs?
- Are there edge cases the RCA missed?
- Is this the right approach, or is there a better way?

**If you find problems with the RCA:**
- STOP
- Explain what's wrong with the diagnosis
- Suggest what should be investigated instead
- Do NOT implement a fix you don't believe in

---

## Phase 3: Plan the Implementation

### 3.1 Map Conceptual to Concrete

The RCA provides conceptual guidance like:
```typescript
// Required pattern:
await execFileAsync('git', ['clone', repoUrl, targetPath]);
```

You need to map this to the ACTUAL code:
- What's the exact current code?
- What variables/functions are actually used?
- What's the code style? (semicolons, quotes, spacing)
- Are there type annotations? What types?

### 3.2 Identify All Changes Needed

Often the fix requires more than what's explicitly stated:
- Import statements may need updating
- Type definitions may need adjusting
- Similar patterns elsewhere may need the same fix
- Tests may need updating

List every change you plan to make.

### 3.3 Consider Ripple Effects

Ask yourself:
- Does this change break any callers?
- Are there other files using the same pattern that need fixing?
- Do any tests need updating?
- Are there type errors this will introduce?

---

## Phase 4: Implement the Fix

**If mode is "plan"**: Stop here. Output your implementation plan and exit.

**If mode is blank (default)**: Proceed with implementation.

### 4.1 Make Changes

For each file:
- Make the minimum necessary changes
- Follow existing code style exactly
- Don't refactor unrelated code
- Don't add "improvements" not in the RCA
- Don't change formatting of untouched lines

### 4.2 Implementation Rules

**DO:**
- Match existing indentation (tabs vs spaces)
- Match existing quote style (single vs double)
- Match existing semicolon usage
- Preserve existing comments unless they're now wrong
- Add comments only if the change is non-obvious

**DON'T:**
- Refactor adjacent code that's "ugly but working"
- Add type annotations to code you didn't change
- Rename variables for "clarity"
- Add error handling beyond what's needed for the fix
- Create abstractions "for future flexibility"

---

## Phase 5: Verify the Fix

### 5.1 Run Verification Steps from RCA

Execute each verification step from the report's "Verification" section:
- Run the specific tests/commands mentioned
- Check for expected outcomes
- Document results

### 5.2 Run Standard Checks

After the specific verifications:

```bash
# Type check (if TypeScript)
npm run type-check || npx tsc --noEmit

# Lint (if configured)
npm run lint

# Run tests
npm test

# Build (if applicable)
npm run build
```

### 5.3 Manual Verification

If the RCA included reproduction steps:
- Attempt to reproduce the original bug
- Confirm it no longer occurs

---

## Phase 6: Archive and Report

### 6.1 Move Report to Fixed

After successful implementation and verification:

```bash
# Create fixed directory if needed
mkdir -p .agents/rca-reports/fixed

# Move the report to fixed folder
mv $1 .agents/rca-reports/fixed/
```

This keeps the `.agents/rca-reports/` folder clean - only unfixed issues remain there.

**Note:** Only move the report if ALL verifications pass. If the fix failed or was incomplete, leave the report in place.

### 6.2 Output Summary

```markdown
## Fix Implementation Complete

**RCA Report**: [original path] → moved to `.agents/rca-reports/fixed/`
**Root Cause**: [one-line summary]

### Changes Made

| File | Lines | Change |
|------|-------|--------|
| `path/to/file.ts` | 123-125 | [brief description] |

### Verification Results

| Check | Result |
|-------|--------|
| [RCA verification step 1] | ✅ PASS / ❌ FAIL |
| Type check | ✅ PASS / ❌ FAIL |
| Lint | ✅ PASS / ❌ FAIL |
| Tests | ✅ PASS / ❌ FAIL |

### Notes

[Any concerns, follow-ups, or observations]
```

---

## Handling Edge Cases

### If the bug is already fixed:
- Verify the fix is complete
- Run verification steps to confirm
- Report that no changes were needed

### If the fix breaks tests:
- Analyze why tests are failing
- Determine if tests need updating or if the fix is wrong
- If tests are outdated, update them
- If fix is wrong, explain and don't proceed

### If you discover additional issues:
- Fix ONLY what's in the RCA report
- Note additional issues in your report
- Suggest a follow-up RCA if needed

### If the RCA is wrong:
- STOP implementation
- Explain specifically what's wrong
- Provide evidence from the actual code
- Suggest what the correct diagnosis might be

---

## Critical Reminders

1. **You are not a copy-paste machine.** Think about whether the fix makes sense.

2. **Read the actual code.** Report snippets may be outdated or incomplete.

3. **Minimal changes only.** The goal is to fix THIS bug, not improve the codebase.

4. **Verify, verify, verify.** A fix that isn't verified is just a hope.

5. **It's OK to refuse.** If the RCA is wrong, say so. A wrong fix is worse than no fix.

6. **Match the codebase style.** Your changes should be invisible in a code review except for the logic change.

Now read the RCA report and begin.
