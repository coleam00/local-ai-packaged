---
description: Lean PRD - problem-first, hypothesis-driven product spec
argument-hint: [output-filename] (default: PRD.md)
---

# Product Requirements Document

**Output**: $ARGUMENTS (default: `PRD.md`)

---

## Your Role

You are a sharp product manager who:
- Starts with PROBLEMS, not solutions
- Demands evidence before building
- Thinks in hypotheses, not specs
- Prioritizes ruthlessly
- Acknowledges uncertainty honestly

**Anti-pattern to avoid**: Don't fill sections with fluff. If you don't have the info, say "TBD - needs user research" rather than inventing plausible-sounding requirements.

---

## Before Writing: Key Questions

If the conversation hasn't covered these, ASK before writing:

1. **Who** has this problem? (Be specific - not "users")
2. **What** problem are they facing? (Observable behavior, not assumed need)
3. **Why** can't they solve it today? (Current alternatives and why they fail)
4. **Why now?** (What changed that makes this worth building?)
5. **How** will we know if we solved it? (Measurable outcome)

---

## PRD Structure

### Page 1: The One-Pager (Most Important)

This page alone should enable a go/no-go decision.

```markdown
# [Product/Feature Name]

## Problem Statement
[2-3 sentences: Who has what problem, and what's the cost of not solving it?]

## Evidence
- [User quote, data point, or observation that proves this problem exists]
- [Another piece of evidence]
- [If no evidence: "Assumption - needs validation"]

## Proposed Solution
[One paragraph: What we're building and why this approach]

## Key Hypothesis
We believe [this capability] will [solve this problem] for [these users].
We'll know we're right when [measurable outcome].

## What We're NOT Building
- [Explicitly out of scope item and why]
- [Another out of scope item]

## Success Metrics
| Metric | Target | How Measured |
|--------|--------|--------------|
| [Primary metric] | [Specific number] | [Method] |
| [Secondary metric] | [Specific number] | [Method] |

## Open Questions
- [ ] [Unresolved question that could change the approach]
- [ ] [Another uncertainty we're betting on]
```

---

### Page 2+: Supporting Detail (Only If Needed)

Expand these sections based on complexity. Skip what's not relevant.

#### Users & Context

**Primary User**
- Who: [Specific description, not generic "user"]
- Current behavior: [What they do today]
- Trigger: [What moment triggers the need]
- Success state: [What "done" looks like for them]

**Jobs to Be Done**
When [situation], I want to [motivation], so I can [outcome].

#### Solution Detail

**Core Capabilities** (MoSCoW)
| Priority | Capability | Rationale |
|----------|------------|-----------|
| Must | [Feature] | [Why essential for hypothesis] |
| Must | [Feature] | [Why essential] |
| Should | [Feature] | [Why important but not blocking] |
| Could | [Feature] | [Nice to have if time] |
| Won't | [Feature] | [Explicitly deferred and why] |

**User Flow**
[Describe the critical path - what's the shortest journey to value?]

#### Technical Approach

**Architecture** (brief)
- [Key technical decision and why]
- [Another decision]

**Dependencies**
- [External dependency and risk level]

**Technical Risks**
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| [Risk] | High/Med/Low | [How we'll handle it] |

#### Implementation

**Phase 1: [Name] - Validate Hypothesis**
- Goal: [What we're trying to learn]
- Build: [Minimum to test the hypothesis]
- Success signal: [How we know to continue]

**Phase 2: [Name] - Expand If Validated**
- Goal: [Next learning goal]
- Build: [What to add]
- Success signal: [Metric target]

#### Decisions Made

| Decision | Choice | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| [Decision] | [What we chose] | [Other options] | [Why this one] |

---

## Quality Checks

Before finishing, verify:

- [ ] Problem is specific and evidenced (not assumed)
- [ ] Solution clearly addresses the stated problem
- [ ] Success metrics are measurable with specific targets
- [ ] Priorities are clear (Must vs Should vs Could)
- [ ] Out-of-scope is explicit
- [ ] Open questions are acknowledged
- [ ] A skeptic could understand why this is worth building

---

## Output

1. Write the PRD to the specified file
2. Summarize: Problem → Solution → Key Metric
3. List the open questions that need answers
4. Suggest next step (validate assumption, user research, prototype, etc.)
