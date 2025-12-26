---
description: Deep root cause analysis - finds the actual cause, not just symptoms
argument-hint: <issue|error|stacktrace> [quick]
---

# Root Cause Analysis

**Input**: $1
**Mode**: $2 (blank = deep, "quick" = surface scan)

---

## Your Mission

Find the **actual root cause** - the specific code, config, or logic that, if changed, would prevent this issue. Not symptoms. Not intermediate failures. The origin.

**The Test**: Ask yourself "If I changed THIS, would the issue be prevented?" If the answer is "maybe" or "partially", you haven't found the root cause yet. Keep digging.

---

## Investigation Protocol

### Phase 1: Classify and Parse Input

First, determine what you're working with:

**Type A - Raw Symptom** (vague description, error message, stack trace):
→ You need to INVESTIGATE. Form hypotheses, test them, explore the codebase.

**Type B - Pre-Diagnosed Finding** (already identifies location/problem):
→ You need to VALIDATE and EXPAND. Confirm the diagnosis is correct, then look for related issues elsewhere.

Parse the input:
- Stack trace → extract error type, message, call chain
- Error message → identify system, error code, context
- Vague description → identify what's actually being claimed
- Pre-diagnosis → identify the claimed cause and affected code

Restate the symptom in one sentence. What is actually failing?

### Phase 2: Form Hypotheses

Based on the symptom, generate 2-4 hypotheses about what could cause this. For each:
- What would need to be true for this hypothesis to be correct?
- What evidence would confirm or refute it?

Rank by likelihood. Start with the most probable.

### Phase 3: The 5 Whys

For your leading hypothesis, execute the 5 Whys protocol:

```
WHY 1: Why does [symptom] occur?
→ Because [intermediate cause A]
→ Evidence: [code reference, log, or test that proves this]

WHY 2: Why does [intermediate cause A] happen?
→ Because [intermediate cause B]
→ Evidence: [proof]

WHY 3: Why does [intermediate cause B] happen?
→ Because [intermediate cause C]
→ Evidence: [proof]

WHY 4: Why does [intermediate cause C] happen?
→ Because [intermediate cause D]
→ Evidence: [proof]

WHY 5: Why does [intermediate cause D] happen?
→ Because [ROOT CAUSE - specific code/config/logic]
→ Evidence: [exact file:line reference]
```

**Rules:**
- You may need more or fewer than 5 levels. Stop when you hit code you can change.
- Every "because" MUST have evidence. No speculation without proof.
- If evidence refutes a hypothesis, pivot to the next one.
- If you hit a dead end, backtrack and try alternative branches.

**Evidence Standards (STRICT):**
- ✅ VALID: `file.ts:123` with actual code snippet
- ✅ VALID: Command output you actually ran
- ✅ VALID: Test you executed that proves the behavior
- ❌ INVALID: "likely includes...", "probably because...", "may cause..."
- ❌ INVALID: Logical deduction without code proof
- ❌ INVALID: Explaining how a technology works in general

If you cannot prove a step with concrete evidence, either:
1. Run a test/command to get proof, or
2. Omit that step from the chain (skip to what you CAN prove)

### Phase 4: Validate the Root Cause

Before declaring victory, verify:

1. **Causation test**: Does the root cause logically lead to the symptom through your evidence chain?
2. **Necessity test**: If the root cause didn't exist, would the symptom still occur?
3. **Sufficiency test**: Is the root cause alone enough to cause the symptom, or are there co-factors?

If any test fails, your root cause is incomplete. Go deeper or broader.

---

## Mode-Specific Behavior

**If mode is "quick":**
- Limit to 2-3 Whys
- Accept high-confidence hypotheses without exhaustive validation
- Focus on the most likely single path
- Time budget: ~5 minutes of investigation

**If mode is "deep" (default):**
- Full 5 Whys minimum
- Validate alternative hypotheses to rule them out
- Check for contributing factors and co-causes
- **REQUIRED: Git history analysis** (see below)
- **REQUIRED: Test at least one hypothesis with execution** (not just code reading)
- No time limit - keep going until certain

**Git History Requirement (deep mode):**
You MUST run `git log` and/or `git blame` on the affected files and include findings in the report:
- When was the problematic code introduced?
- What commit/PR added it?
- Has it changed recently or been stable?

This context helps the fixing agent understand if it's a regression, original bug, or recent change.

---

## Investigation Techniques

Use these adaptively based on what you find.

**CRITICAL: Test, Don't Just Read**
Reading code tells you what it's supposed to do. Running code tells you what it actually does. When you form a hypothesis, VALIDATE IT:
- Write a quick test script to prove the behavior
- Run the actual command with test inputs
- Execute the code path and observe the result

This is the difference between speculation and evidence.

**For code issues:**
- Grep for error messages, function names, variable names
- Read the full context around suspicious code (not just the line)
- Check git blame to see when/why code was written
- Look for similar patterns elsewhere that work (spot the difference)
- **Run the suspicious code** with edge case inputs to prove the bug

**For runtime issues:**
- Check for environment/config differences
- Look for initialization order dependencies
- Search for race conditions or timing issues
- Examine error handling (or lack thereof)

**For integration issues:**
- Trace data flow across boundaries
- Check type mismatches, serialization, encoding
- Verify assumptions each side makes about the other

**For "it worked before" issues:**
- `git log --oneline -20` to see recent changes
- `git diff HEAD~10` on suspicious files
- Binary search with git bisect mentally

---

## Output Format

**Before writing the report:**
1. Create directory if needed: `mkdir -p .agents/rca-reports`
2. List existing reports: `ls .agents/rca-reports/`
3. Find next available number (if `rca-report-1.md` and `rca-report-2.md` exist, use `3`)

**Save to:** `.agents/rca-reports/rca-report-{N}.md`

At the end of your investigation, tell the user the report path so they can run `/fix-rca` on it.

```markdown
# Root Cause Analysis

**Issue**: [One-line description of the symptom]
**Root Cause**: [One-line description of the actual cause]
**Severity**: [Critical/High/Medium/Low]
**Confidence**: [High/Medium/Low - based on evidence strength]

## Evidence Chain

### The Path from Symptom to Cause

[Your 5 Whys chain, formatted clearly with evidence at each level]

WHY: [Symptom occurs]
↓ BECAUSE: [First level cause]
  Evidence: `file.ts:123` - [relevant code snippet or log]

WHY: [First level cause occurs]
↓ BECAUSE: [Second level cause]
  Evidence: `other-file.ts:456` - [relevant code snippet]

[...continue to root cause...]

↓ ROOT CAUSE: [The actual fixable thing]
  Evidence: `source.ts:789` - [the problematic code]

### Alternative Hypotheses Considered

[If deep mode: list other hypotheses and why they were ruled out]

### Git History Context

[Deep mode only - REQUIRED]
- **Introduced**: [commit hash] - [commit message] - [date]
- **Author**: [who wrote this code]
- **Recent changes**: [Has this code changed recently? When?]
- **Implication**: [Is this a regression, original bug, or long-standing issue?]

## Fix Specification

### What Needs to Change

[Conceptual description of the fix. Be specific about:]
- Which file(s) need modification
- What logic/behavior needs to change
- What the correct behavior should be

### Implementation Guidance

[Pointers and examples to guide the fixing agent:]

```typescript
// Current problematic pattern (conceptual):
[simplified example of what's wrong]

// Required pattern (conceptual):
[simplified example of what it should look like]
```

**Key considerations for implementation:**
- [Important edge case or constraint]
- [Related code that might need updates]
- [Testing approach to verify the fix]

### Files to Examine

- `path/to/primary-file.ts:LINE` - [why this file]
- `path/to/related-file.ts` - [why this file]

## Verification

[How to confirm the fix works:]

1. [Specific test or check to run]
2. [Expected outcome if fixed]
3. [How to reproduce the original issue to compare]
```

---

## Critical Reminders

1. **Symptoms lie.** The error message tells you what failed, not why.

2. **First plausible explanation is often wrong.** Resist the urge to stop early.

3. **No evidence = no claim.** Words like "likely", "probably", "may" are not allowed in evidence blocks. Prove it or omit it.

4. **Test, don't just read.** Run the code with test inputs. Execution proves behavior; reading proves intent.

5. **Git history is mandatory.** In deep mode, you must include when/who/why the code was written.

6. **The fix should be obvious.** If your root cause is correct, the fix writes itself.

7. **Think like a debugger, not a documenter.** Your job is to FIND the cause, not produce a pretty report.

Now investigate. Don't stop until you can point to the exact code that needs to change.
