---
description: Create a PR from current branch with unpushed commits
argument-hint: [base-branch] (default: main)
---

# Create Pull Request

**Base branch**: $ARGUMENTS (default: main)

---

## Steps

1. Check current state:
   ```bash
   git status --short
   git log origin/main..HEAD --oneline
   ```

2. Get commit details for PR description:
   ```bash
   git log origin/main..HEAD --pretty=format:"- %s"
   ```

3. Push current branch if needed:
   ```bash
   git push -u origin HEAD
   ```

4. Create PR:
   ```bash
   gh pr create --fill
   ```

   Or with more control:
   ```bash
   gh pr create \
     --title "[concise title from commits]" \
     --body "[summary of changes]"
   ```

## PR Format

**Title**: Concise, imperative mood (e.g., "Add Discord adapter")

**Body**:
```markdown
## Summary
[1-2 sentences: what this PR does]

## Changes
- [commit 1 summary]
- [commit 2 summary]

## Testing
- [ ] Type check passes
- [ ] Tests pass
- [ ] Manually verified
```

## Output

After creating:
```
PR created: [URL]
```
