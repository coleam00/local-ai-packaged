---
description: Deep implementation planning - analyzes codebase, mirrors patterns, produces step-by-step guide
argument-hint: <feature description or PRD path>
---

# Implementation Plan

**Input**: $ARGUMENTS

---

## CRITICAL: Plan Only - Do NOT Implement

This command creates a PLAN. You do NOT write any implementation code.

After creating the plan file, STOP and tell the user:
- The plan file path
- Summary of the approach
- How to execute: `/implement <plan-file-path>`

**DO NOT**:
- Create source files
- Modify existing code
- Install dependencies
- Run any implementation tasks

---

## Your Role

You are a senior engineer creating an implementation plan for another agent. Your plan must be:

1. **Pattern-faithful**: Mirror existing codebase patterns exactly
2. **Justified**: Every new line of code has a reason
3. **Complete**: Agent can execute without asking questions
4. **Minimal**: No over-engineering, no unnecessary abstractions

**Golden Rule**: The best code is code that looks like it was always there. Match the codebase style so perfectly that your changes are invisible except for the new functionality.

---

## Phase 1: Understand the Request

### Parse the Input

The input could be:
- A PRD file path → Read it, extract what to build
- A feature sentence → Clarify scope before proceeding
- A GitHub issue → Extract requirements

**Output**: One paragraph stating exactly what needs to be built and why.

### Quick Feasibility Check

Before deep research, answer:
- Is this possible with the current architecture?
- Are there obvious blockers (missing dependencies, incompatible patterns)?
- Does something similar already exist that we should extend instead?

If blockers exist, STOP and report them. Don't plan the impossible.

---

## Phase 2: External Research (REQUIRED)

**Before diving into the codebase, research externally:**

### 2.0 Web Search for Context

Use web search to find:
- **Official documentation** for any libraries/APIs involved
- **Latest version info** and any breaking changes
- **Common implementation patterns** and best practices
- **Known gotchas** and issues others have encountered
- **Similar implementations** in open source projects

Example searches:
- "discord.js bot tutorial 2024"
- "discord.js message handling best practices"
- "discord bot rate limits"

**Include in plan:**
```markdown
## External Research

### Documentation
- [Discord.js Guide](https://discordjs.guide/) - Official guide
  - Key section: Message handling
- [Discord API Docs](https://discord.com/developers/docs)
  - Key section: Rate limits

### Gotchas Found
- Must enable MESSAGE_CONTENT intent (as of 2022)
- 2000 character message limit
- Rate limit: 5 messages per 5 seconds per channel
```

---

## Phase 3: Codebase Research (CRITICAL)

**Goal**: Find patterns to mirror. Do NOT invent new patterns.

### 3.1 Find Similar Implementations

Search for analogous features in the codebase:
- If adding Discord adapter → Study Telegram/Slack adapters
- If adding new command → Study existing commands
- If adding new API endpoint → Study existing endpoints

**For each similar implementation found, extract:**
```
File: src/adapters/telegram.ts
Lines: 15-120
Pattern: Platform adapter with polling, message handling, streaming
Key methods: start(), stop(), sendMessage(), handleUpdate()
```

### 3.2 Identify Patterns to Mirror

**MUST document with actual code snippets from the codebase:**

```typescript
// FROM: src/adapters/telegram.ts:23-35
// This is how adapters are structured:
export class TelegramAdapter implements IPlatformAdapter {
  private bot: TelegramBot;

  constructor(private config: TelegramConfig) {
    this.bot = new TelegramBot(config.token, { polling: true });
  }

  async start(): Promise<void> {
    // ...
  }
}
```

Include snippets for:
- Class/function structure
- Error handling pattern
- Logging pattern
- Type definitions
- Test structure

### 3.3 Identify Files to Modify

| File | Change Type | Reason |
|------|-------------|--------|
| `src/adapters/discord.ts` | CREATE | New adapter implementation |
| `src/types/index.ts` | UPDATE | Add Discord config types |
| `src/index.ts` | UPDATE | Register Discord adapter |

### 3.4 Check Project Rules

Read and follow:
- `CLAUDE.md` - Project conventions
- `.agents/reference/new-features.md` - If adding new feature type
- Existing interfaces (`IPlatformAdapter`, `IAssistantClient`)

### 3.5 Discover Validation Infrastructure

**Find out how this project validates code:**

```bash
# What scripts are available?
npm run          # or cat package.json scripts section

# What test framework?
ls jest.config.* vitest.config.* *.test.ts *.spec.ts

# Existing test patterns
find . -name "*.test.ts" -o -name "*.spec.ts" | head -5
```

Document:
- Test framework (Jest, Vitest, Mocha, etc.)
- Test file naming convention (`*.test.ts` vs `*.spec.ts`)
- Test location (colocated vs `tests/` folder)
- Mocking patterns used
- Any E2E or integration test setup

---

## Phase 4: Design the Solution

### 4.1 Architecture Decision

**Approach chosen**: [Describe the approach]

**Why this approach**:
- [Reason 1 - should reference existing pattern]
- [Reason 2]

**Alternatives considered and rejected**:
- [Alternative] - Rejected because [reason]

### 4.2 What We're NOT Building

Explicitly list what's out of scope to prevent over-engineering:
- ❌ [Feature/abstraction we're intentionally not adding]
- ❌ [Configuration option we don't need yet]
- ❌ [Edge case we're not handling in v1]

### 4.3 Minimal Viable Implementation

What's the SMALLEST change that delivers the feature?

---

## Phase 5: Step-by-Step Implementation Tasks

**Format for each task:**

```markdown
### Task N: [ACTION] [file]

**Why**: [Justification - why is this change needed?]

**Mirror**: `path/to/similar.ts:XX-YY`

**Do**:
[Specific instructions with code snippets]

**Don't**:
- [Common mistake to avoid]

**Verify**: `[command to run]`
```

### Task 1: [First task - usually types/interfaces]

...

### Task 2: [Second task]

...

[Continue for all tasks]

---

## Phase 6: Validation Strategy (CRITICAL)

Validation is how we know the feature actually works. Plan this thoroughly.

### 6.1 Discover Project Validation Tools

Check what validation tools exist in the project:

```bash
# Check package.json scripts
cat package.json | grep -A 20 '"scripts"'

# Look for test frameworks
ls -la *.config.* jest.config.* vitest.config.*

# Check for existing tests
ls -la **/*.test.ts **/*.spec.ts tests/ __tests__/

# Check for linting/formatting
cat .eslintrc* .prettierrc* tsconfig.json
```

Document what's available:
- Type checker: `npm run type-check` or `npx tsc --noEmit`
- Linter: `npm run lint`
- Formatter: `npm run format:check`
- Unit tests: `npm test`
- Integration tests: [if they exist]
- E2E tests: [if they exist]

### 6.2 Plan Unit Tests

For each new file/function, plan the tests:

```markdown
### Tests for `src/adapters/discord.ts`

**Test file**: `src/adapters/discord.test.ts`
**Mirror**: `src/adapters/telegram.test.ts`

**Test cases**:
1. Constructor initializes with correct streaming mode
2. `getPlatformType()` returns 'discord'
3. `getStreamingMode()` returns configured mode
4. `sendMessage()` splits messages over 2000 chars
5. `getConversationId()` extracts channel ID correctly

**Mocking strategy**: Mock discord.js Client to avoid real API calls
```

### 6.3 Plan Integration/E2E Tests

How will we test the feature actually works end-to-end?

```markdown
### Integration Tests

**If project has existing integration tests:**
- Add test to existing suite
- Follow existing patterns

**Manual E2E validation:**
1. Start the application
2. Send test message via [platform]
3. Verify response received
4. Check logs for expected flow
```

### 6.4 Plan Manual Validation

**Think creatively about how to validate:**

```markdown
### Manual Validation Steps

**For an API endpoint:**
```bash
# Test happy path
curl -X POST http://localhost:3000/endpoint \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Test error handling
curl -X POST http://localhost:3000/endpoint \
  -d 'invalid json'

# Test edge cases
curl -X POST http://localhost:3000/endpoint \
  -d '{"field": ""}'  # empty value
```

**For a platform adapter:**
1. Set up test credentials in .env
2. Start app: `npm run dev`
3. Send message from platform
4. Verify bot responds
5. Test error case (invalid command)
6. Test long message (should split)

**For a background job:**
1. Trigger the job manually
2. Check logs for expected output
3. Verify database/state changes
4. Test failure recovery
```

### 6.5 Creative Validation Ideas

Think beyond the obvious:

- **Load testing**: What happens with many concurrent requests?
- **Failure modes**: What if the API is down? Database unavailable?
- **Edge cases**: Empty strings, very long inputs, special characters, unicode
- **State transitions**: Does it handle restart correctly? What about partial failures?
- **Observability**: Can we verify via logs? Metrics? Health endpoints?
- **Regression**: Do existing features still work?

### 6.6 Validation Checklist Template

```markdown
## Validation Plan

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - Unit tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write
- [ ] [Test 1 description]
- [ ] [Test 2 description]

### Manual Validation
- [ ] [Step 1]
- [ ] [Step 2]

### Edge Cases to Test
- [ ] [Edge case 1]
- [ ] [Edge case 2]

### Regression Check
- [ ] Existing features still work: [how to verify]
```

---

## Output Format

**Save to**: `.agents/plans/{feature-name}.plan.md`

Create `.agents/plans/` if it doesn't exist: `mkdir -p .agents/plans`

---

## STOP HERE - Do Not Implement

After writing the plan file, output:

```
## Plan Created

**File**: `.agents/plans/{feature-name}.plan.md`

**Summary**: [2-3 sentence summary of the approach]

**External Research**: [Key findings from web search]

**Files to change**: [count] files ([list them])

**To implement**: `/implement .agents/plans/{feature-name}.plan.md`
```

Then STOP. Do not proceed to implementation.

---

### Plan Structure (for reference)

```markdown
# Plan: [Feature Name]

## Summary
[One paragraph: What we're building and the approach]

## External Research

### Documentation
- [Link to official docs] - [Key section]

### Gotchas & Best Practices
- [Important finding from research]

## Patterns to Mirror
[Code snippets from existing codebase that we'll follow]

## Files to Change
| File | Action | Justification |
|------|--------|---------------|

## NOT Building
- [Explicit out of scope items]

## Tasks

### Task 1: ...
### Task 2: ...

## Validation Strategy

### Automated Checks
- [ ] `npm run type-check` - Types valid
- [ ] `npm run lint` - No lint errors
- [ ] `npm run test` - All tests pass
- [ ] `npm run build` - Build succeeds

### New Tests to Write
| Test File | Test Case | What It Validates |
|-----------|-----------|-------------------|
| `file.test.ts` | [test name] | [what it proves] |

### Manual/E2E Validation
```bash
# [Command to test the feature]
```
1. [Step-by-step manual test]
2. [Expected result]

### Edge Cases
- [ ] [Edge case 1 and how to test]
- [ ] [Edge case 2 and how to test]

### Regression Check
- [ ] [How to verify existing features still work]

## Risks
[What could go wrong]
```

---

## Quality Checks Before Finalizing

### Implementation Quality
- [ ] Every new file has a justification
- [ ] Every modification has a justification
- [ ] Patterns come from actual codebase (with file:line refs)
- [ ] Code snippets are REAL, not invented
- [ ] No unnecessary abstractions or "future flexibility"
- [ ] Tasks are ordered by dependency
- [ ] Each task has a verification command

### Validation Quality
- [ ] Discovered all project validation tools
- [ ] Unit tests planned for new code
- [ ] Manual validation steps are specific and executable
- [ ] Edge cases identified and have test plans
- [ ] Regression check planned
- [ ] Creative validation ideas considered (failure modes, load, etc.)

### Completeness
- [ ] Agent can implement without asking questions
- [ ] Agent can validate without asking questions

---

## Critical Reminders

1. **Research first.** Web search for docs, gotchas, and best practices before codebase analysis.

2. **Mirror, don't invent.** If there's an existing pattern, use it exactly.

3. **Justify every line.** "Why does this file need to change?" must have an answer.

4. **Minimal scope.** Build what was asked, nothing more.

5. **Real code snippets.** Show actual code from the codebase, not generic examples.

6. **Dependency order.** Tasks must be executable top-to-bottom.

7. **Validation is critical.** Plan tests, manual checks, edge cases, and creative validation. The implementation agent needs to know HOW to verify their work.

8. **No placeholders.** Everything in the plan is concrete and actionable.

9. **PLAN ONLY.** Write the plan file and STOP. Do not implement anything.

Now research externally, analyze the codebase, and create the implementation plan. Then STOP.
