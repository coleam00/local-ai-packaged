---
description: Autonomously develop a complete feature from planning to commit
argument-hint: [feature-description]
---

# End-to-End Feature Development

**Feature Description**: $ARGUMENTS

This command chains the 4 core commands for autonomous feature development.

---

## Step 1: Prime - Load Codebase Context

Execute the priming workflow to understand the codebase:

core_commands/prime.md

---

## Step 2: Planning - Create Implementation Plan

Create a detailed implementation plan for the feature.

Execute the planning workflow with the feature description: **$ARGUMENTS**

core_commands/planning.md

Replace `ARGUMENTS` in the planning command with: **$ARGUMENTS**

**IMPORTANT**: Note the feature name that the planning step creates. You'll need it for the next step.

---

## Step 3: Execute - Implement the Feature

Implement the feature from the plan document.

Execute the implementation workflow with the plan file path: `plans/[feature-name].md`

(Use the feature name from Step 2)

core_commands/execute.md

Replace `ARGUMENTS` in the execute command with: `plans/[feature-name].md`

---

## Step 4: Commit - Save Changes

Create a git commit for all changes:

core_commands/commit.md

---

## Final Summary

After completing all 4 steps, provide:

### Feature Implementation Complete

**Original Request**: $ARGUMENTS

**Feature Name**: [feature-name from planning step]

**Steps Executed:**
1. ✅ Prime - Codebase context loaded
2. ✅ Planning - Plan created at `plans/[feature-name].md`
3. ✅ Execute - Feature implemented and validated
4. ✅ Commit - Changes committed to git

**Outputs:**
- Plan document: `plans/[feature-name].md`
- Files created/modified: [list]
- Tests added: [list]
- Commit hash: [hash]

**Next Steps:**
- Push to remote: `git push`
- Create pull request (if applicable)
- Continue with next feature
