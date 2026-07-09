---
name: langfuse-user-feedback
description: Wires up user feedback (thumbs up/down, ratings, comments) from an application's frontend to Langfuse scores. Use when user wants to capture end-user feedback, add ratings to traces, or connect user complaints to Langfuse.
---

# User Feedback

Tracing must already be set up — feedback is stored as scores on traces.

Docs: https://langfuse.com/docs/observability/features/user-feedback

## Workflow

### 1. Determine What Feedback to Capture

If the user has asked for something specific, go with that. Otherwise, look at the application and **present a few UX options** for how feedback could work, then ask the user which they prefer before implementing.

Common UX patterns to suggest:

| UX Pattern | Best for | How it works |
|------------|----------|--------------|
| Thumbs up/down | Chat apps, Q&A | Simple binary buttons next to each response |
| Star rating (1–5) | Content generation, summaries | Star row or dropdown after each output |
| "Was this helpful?" banner | Search, documentation assistants | Single yes/no prompt at the bottom of a response |
| Regenerate / copy tracking | Any app with these actions | Implicit — log when users retry (negative signal) or copy output (positive signal) |
| Free-text comment | Complex outputs, internal tools | Optional text field alongside a rating |
| Report button | Any user-facing app | Flag icon to report bad/harmful responses |

This table is not exhaustive — if the application suggests a different feedback pattern that fits better, propose that instead. Present 2–3 options that match the application's use case and ask the user which approach they'd like. This decision shapes everything downstream (score names, data types, frontend components), so it's important to align early.

Feedback can be **explicit** (user rates via thumbs, stars, etc.) or **implicit** (derived from behavior like copying output, retrying, or escalating to support). Both are stored as scores. Explicit feedback requires the trace ID to reach the frontend; implicit feedback is logged server-side where the event already happens.

### 2. Choose Score Names

Name reflects the signal source, not what you hope it measures (e.g., `user-thumbs` not `response-quality` — a thumbs down doesn't tell you *what* was wrong). Avoid generic names like `feedback` or `score`.

Rules:
- Lowercase with hyphens
- One consistent name per feedback type across the entire app
- If capturing multiple signals, each gets its own distinct name

### 3. Implement Score Creation

**For implicit feedback (server-side):** Use `langfuse.create_score()` / `langfuse.score.create()` wherever the event is already handled in application code. Fetch SDK docs for current API: https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk

**For explicit feedback (frontend):** Use `LangfuseWeb` in the browser. It uses the public key only — no secret key exposed.

```typescript
import { LangfuseWeb } from "langfuse";

const langfuse = new LangfuseWeb({
  publicKey: process.env.NEXT_PUBLIC_LANGFUSE_PUBLIC_KEY!,
  baseUrl: process.env.NEXT_PUBLIC_LANGFUSE_HOST,
});

langfuse.score({
  traceId,
  name: "user-thumbs",
  value: 1, // 1 = positive, 0 = negative
  dataType: "BOOLEAN",
  comment: optionalUserComment,
});
```

The trace ID must be available in the frontend for this to work. For Vercel AI SDK, the non-obvious pattern is using `generateMessageId`:

```typescript
import { getActiveTraceId } from "@langfuse/tracing";

// Inside route handler wrapped with observe()
return result.toUIMessageStreamResponse({
  generateMessageId: () => getActiveTraceId() || crypto.randomUUID(),
});
```

### 4. Verify

Trigger a feedback action and check the trace's Scores tab in Langfuse. Confirm the score name, value, and data type are correct.

Point users to what they can do with feedback data: filter traces by low scores, use score analytics for trends, build annotation queues for team review.

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Secret key in frontend code | Security risk | Use `LangfuseWeb` with public key only |
| Missing `dataType` on boolean scores | Value `1` inferred as `NUMERIC` | Always pass `dataType: "BOOLEAN"` explicitly |
| Inconsistent score names across the app | Can't aggregate or filter reliably | Pick one name per feedback type, use it everywhere |
