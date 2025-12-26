---
description: Create git worktrees for parallel branch development with validation
argument-hint: <branch-1> [branch-2] [branch-3] [branch-4] [branch-5]
---

# Git Worktree Setup

**Branch 1**: $1 (required)
**Branch 2**: $2 (optional)
**Branch 3**: $3 (optional)
**Branch 4**: $4 (optional)
**Branch 5**: $5 (optional)

---

## Purpose

Create isolated worktrees for parallel development on multiple branches without conflicts:
- Separate directories for each branch
- Dedicated ports (no conflicts)
- Independent dependencies
- Full validation on each

---

## Port Allocation

| Worktree | Port | Health Endpoint |
|----------|------|-----------------|
| Worktree 1 ($1) | 8124 | http://localhost:8124/health |
| Worktree 2 ($2) | 8125 | http://localhost:8125/health |
| Worktree 3 ($3) | 8126 | http://localhost:8126/health |
| Worktree 4 ($4) | 8127 | http://localhost:8127/health |
| Worktree 5 ($5) | 8128 | http://localhost:8128/health |

---

## Logic

**Count provided arguments** and spawn that many agents in parallel:

| Arguments | Action |
|-----------|--------|
| Only `$1` | Single worktree, run sequentially |
| `$1` + `$2` | Spawn 2 agents in parallel |
| `$1` + `$2` + `$3` | Spawn 3 agents in parallel |
| `$1` + `$2` + `$3` + `$4` | Spawn 4 agents in parallel |
| `$1` + `$2` + `$3` + `$4` + `$5` | Spawn 5 agents in parallel |

**Each worktree MUST pass validation before reporting success**:
1. Dependencies installed (`npm install`)
2. Type check passed (`npm run type-check`)
3. Lint passed (`npm run lint`)
4. Tests passed (`npm test`)
5. Health check passed (server starts and responds)

---

## Single Worktree Setup (when only $1 provided)

Execute these steps sequentially:

### Step 1: Create Worktree Directory

```bash
mkdir -p worktrees
```

### Step 2: Create Git Worktree

```bash
# Create worktree with new branch (or use existing branch)
git worktree add worktrees/$1 -b $1 2>/dev/null || git worktree add worktrees/$1 $1
```

### Step 3: Install Dependencies

```bash
cd worktrees/$1 && npm install
```

### Step 4: Run Validation

```bash
cd worktrees/$1 && npm run type-check && npm run lint && npm test
```

### Step 5: Test Server Startup

```bash
# Start server in background with dedicated port
cd worktrees/$1 && PORT=8124 npm run dev &
SERVER_PID=$!

# Wait for startup
sleep 5

# Health check
curl -f http://localhost:8124/health || echo "Health check failed"

# Kill server
kill $SERVER_PID 2>/dev/null
```

### Step 6: Report

```markdown
## Worktree Ready

**Path**: worktrees/$1
**Branch**: $1
**Port**: 8124

### Validation Results
- [ ] Dependencies installed
- [ ] Type check passed
- [ ] Lint passed
- [ ] Tests passed
- [ ] Health check passed

### To work in this worktree:
```bash
cd worktrees/$1
PORT=8124 npm run dev
```

### To switch Claude Code to this worktree:
Use `/add-dir worktrees/$1` or start a new session in that directory.
```

---

## Parallel Worktree Setup (when multiple branches provided)

For each branch argument provided, spawn an agent using the Task tool.

**IMPORTANT**: Spawn ALL agents in a SINGLE message to enable parallel execution.

### Agent Prompt Template

For each worktree N (where N is 1-5), use this prompt:

```
Set up git worktree for parallel development.

**Branch**: [BRANCH_NAME]
**Port**: [PORT]  # 8124 for $1, 8125 for $2, 8126 for $3, 8127 for $4, 8128 for $5

**CRITICAL**: Report FAILURE if ANY step fails. Do not report success unless ALL steps pass.

**Steps**:
1. Create directory: `mkdir -p worktrees`
2. Create worktree: `git worktree add worktrees/[BRANCH_NAME] -b [BRANCH_NAME] 2>/dev/null || git worktree add worktrees/[BRANCH_NAME] [BRANCH_NAME]`
3. Install dependencies: `cd worktrees/[BRANCH_NAME] && npm install`
   - If fails: Report FAILURE
4. Run type check: `cd worktrees/[BRANCH_NAME] && npm run type-check`
   - If fails: Report FAILURE
5. Run lint: `cd worktrees/[BRANCH_NAME] && npm run lint`
   - If fails: Report FAILURE (warnings OK, errors not OK)
6. Run tests: `cd worktrees/[BRANCH_NAME] && npm test`
   - If fails: Report FAILURE
7. Start server: `cd worktrees/[BRANCH_NAME] && PORT=[PORT] npm run dev &`
8. Wait for startup: `sleep 5`
9. Health check: `curl -f http://localhost:[PORT]/health`
   - If fails: Report FAILURE
10. Kill server: `lsof -ti:[PORT] | xargs kill -9 2>/dev/null`

**Report back** (structured):
- Worktree: worktrees/[BRANCH_NAME]
- Branch: [BRANCH_NAME]
- Port: [PORT]
- Status: SUCCESS or FAILURE
- Validation:
  - npm install: PASS/FAIL
  - type-check: PASS/FAIL
  - lint: PASS/FAIL
  - tests: PASS/FAIL
  - health check: PASS/FAIL
- Errors (if any): [error messages]
```

### Port Assignment Table

| Argument | Branch | Port |
|----------|--------|------|
| $1 | First branch | 8124 |
| $2 | Second branch | 8125 |
| $3 | Third branch | 8126 |
| $4 | Fourth branch | 8127 |
| $5 | Fifth branch | 8128 |

### Spawn Agents

Use the Task tool with `subagent_type: "general-purpose"` to spawn ALL agents in a SINGLE message:

```
# For 2 branches:
<Task 1: Setup worktree for $1 on port 8124>
<Task 2: Setup worktree for $2 on port 8125>

# For 3 branches:
<Task 1: Setup worktree for $1 on port 8124>
<Task 2: Setup worktree for $2 on port 8125>
<Task 3: Setup worktree for $3 on port 8126>

# And so on up to 5...
```

### Combine Results

After ALL agents complete, combine their reports:

```markdown
## Worktrees Ready

### Summary

| # | Branch | Port | Status |
|---|--------|------|--------|
| 1 | $1 | 8124 | ✅ SUCCESS / ❌ FAILED |
| 2 | $2 | 8125 | ✅ SUCCESS / ❌ FAILED |
| 3 | $3 | 8126 | ✅ SUCCESS / ❌ FAILED |
| 4 | $4 | 8127 | ✅ SUCCESS / ❌ FAILED |
| 5 | $5 | 8128 | ✅ SUCCESS / ❌ FAILED |

(Only show rows for worktrees that were requested)

### Validation Details

| Check | WT1 | WT2 | WT3 | WT4 | WT5 |
|-------|-----|-----|-----|-----|-----|
| npm install | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| type-check | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| lint | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| tests | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |
| health | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ | ✅/❌ |

### To work in parallel:

**Worktree 1**: `cd worktrees/$1 && PORT=8124 npm run dev`
**Worktree 2**: `cd worktrees/$2 && PORT=8125 npm run dev`
**Worktree 3**: `cd worktrees/$3 && PORT=8126 npm run dev`
**Worktree 4**: `cd worktrees/$4 && PORT=8127 npm run dev`
**Worktree 5**: `cd worktrees/$5 && PORT=8128 npm run dev`

(Only show commands for worktrees that were requested)

### Database Note

All worktrees share the same DATABASE_URL from `.env`. If you need isolated databases:
- Create separate databases for each worktree
- Copy `.env` to each worktree and update DATABASE_URL
```

---

## Managing Worktrees

### List All Worktrees

```bash
git worktree list
```

### Remove a Worktree

```bash
# Remove worktree directory and prune
git worktree remove worktrees/[branch-name]

# If that fails, force remove
git worktree remove --force worktrees/[branch-name]

# Clean up stale entries
git worktree prune
```

### Switch to a Worktree in Claude Code

```bash
# Option 1: Add as additional directory
/add-dir worktrees/[branch-name]

# Option 2: Start new Claude Code session
cd worktrees/[branch-name] && claude
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port (example: 8124)
lsof -i :8124

# Kill it
kill -9 [PID]

# Or kill all worktree ports at once
for port in 8124 8125 8126 8127 8128; do lsof -ti:$port | xargs kill -9 2>/dev/null; done
```

### Worktree Already Exists

```bash
# Check existing worktrees
git worktree list

# Remove if needed
git worktree remove worktrees/[branch-name]
```

### Branch Already Exists

The command handles this: `git worktree add ... -b $1 || git worktree add ... $1`

- First tries to create new branch
- Falls back to using existing branch

### Dependencies Out of Sync

```bash
# In the worktree directory
rm -rf node_modules package-lock.json
npm install
```

---

## Example Usage

### Single Worktree

```bash
/worktree feature/discord-adapter
```

Creates:
- `worktrees/feature/discord-adapter` directory
- Branch: `feature/discord-adapter`
- Port: 8124

### Two Parallel Worktrees

```bash
/worktree feature/discord-adapter feature/slack-improvements
```

Creates (2 agents in parallel):
- `worktrees/feature/discord-adapter` on port 8124
- `worktrees/feature/slack-improvements` on port 8125

### Three Parallel Worktrees

```bash
/worktree feature/api-v2 feature/ui-redesign fix/memory-leak
```

Creates (3 agents in parallel):
- `worktrees/feature/api-v2` on port 8124
- `worktrees/feature/ui-redesign` on port 8125
- `worktrees/fix/memory-leak` on port 8126

### Five Parallel Worktrees (Maximum)

```bash
/worktree feature/a feature/b feature/c feature/d feature/e
```

Creates (5 agents in parallel):
- Port 8124, 8125, 8126, 8127, 8128

---

## Critical Notes

1. **Ports are fixed**:
   - Worktree 1: 8124
   - Worktree 2: 8125
   - Worktree 3: 8126
   - Worktree 4: 8127
   - Worktree 5: 8128

2. **Validation is mandatory**: Each worktree MUST pass all checks (install, type-check, lint, tests, health) before reporting success

3. **Shared database**: All worktrees share the same DATABASE_URL by default

4. **Independent node_modules**: Each worktree has its own dependencies

5. **Git state is shared**: Commits in any worktree are visible to all (same repo)

6. **Clean up when done**: Use `git worktree remove` to clean up

7. **Maximum 5 worktrees**: This command supports up to 5 parallel worktrees

Now execute the worktree setup based on arguments provided.
