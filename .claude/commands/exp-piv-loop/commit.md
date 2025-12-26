---
description: Quick commit with natural language file targeting
argument-hint: [target description] (blank = all changes)
---

# Commit

**Target**: $ARGUMENTS

## Steps

1. Check current state: !`git status --short`

2. Interpret the target and select files:
   - Blank → all new + changed files
   - Natural language → figure out which files match

3. Stage only the matching files

4. Write concise commit message (one line, imperative mood)

5. Commit and show result

## Target Examples

```
/commit                                    # Everything
/commit all typescript files               # *.ts only
/commit files in src/handlers              # That folder
/commit everything except tests            # Exclude *test*
/commit the API changes                    # Interpret from diff
/commit don't include package-lock         # Exclude specific
/commit only the new files                 # Untracked only
/commit just the bug fix we did            # Recent work context
```

You are the implementation agent - interpret the target intelligently based on git status and the conversation context.
