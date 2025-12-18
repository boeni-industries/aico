# Agency Flow - Quick Reference

## The Flow
**Goal → Arbiter → Intention → Planner → Plan → Executor → Done**

## Goal Sources

**Manual:**
- `aico agency goal-create` (user-initiated)

**Automated:**
- **Curiosity Engine** - `aico scheduler trigger agency.curiosity_scan --wait`
  - Scans World Model for novelty, gaps, prediction errors
  - Creates curiosity/hobby goals automatically
  - Runs every 6 hours (prefers idle/sleep phases)
- **System Maintenance** - (not yet implemented)
- **Conversation patterns** - (not yet implemented)

## Sequence

1. **Create Goal** → `aico agency goal-create --user <id> --title "..." --origin user`
2. **Run Arbiter** → `aico scheduler trigger agency.arbiter --wait` (converts goal → intention)
3. **Run Executor** → `aico scheduler trigger agency.plan_executor --wait` (executes plan steps)
4. **Check Status** → `aico agency status --user <id>`

## Scheduler Jobs

| Job | Schedule | What it does |
|-----|----------|--------------|
| `agency.curiosity_scan` | Every 6 hours | Scan for curiosity opportunities → Create goals |
| `agency.arbiter` | Every 5 min | Pending goals → Active intentions |
| `agency.plan_executor` | Every 2 min | Execute plan steps |
| `agency.follow_up` | Every 15 min | Proactive reminders |
| `agency.reflection` | Daily 03:00 | Generate learning lessons |

## Quick Test

```bash
USER=1e69de47-a3af-4343-8dba-dbf5dcf5f160

# 1. Create goal
aico agency goal-create --user $USER --title "Test" --origin user --priority high

# 2. Activate it
aico scheduler trigger agency.arbiter --wait

# 3. Execute it
aico scheduler trigger agency.plan_executor --wait

# 4. Check it
aico agency status --user $USER
```
