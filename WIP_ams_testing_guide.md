# AMS Testing Guide - Quick Debug Output

**Date:** 2025-11-07  
**Purpose:** Quick visual debugging with print statements

---

## What to Look For When Starting Backend

### ✅ Expected Output (Success)

When you start the backend with `uv run aico backend start`, you should see:

```
📋 [SCHEDULER] Registered built-in task: ams.memory_consolidation
🧠 [AMS] Initializing Adaptive Memory System components...
🧠 [AMS] ✅ Idle detector initialized
🧠 [AMS] ✅ Consolidation scheduler initialized
🧠 [AMS] ✅ Evolution tracker initialized
🧠 [AMS] ✅✅✅ Adaptive Memory System components initialized successfully!
```

### ⚠️ Expected Output (Disabled)

If consolidation is disabled in config:

```
🧠 [AMS] ⚠️  Consolidation disabled in configuration, skipping AMS initialization
```

### ❌ Error Output

If something fails:

```
🧠 [AMS] ❌❌❌ Failed to initialize AMS components: [error message]
🧠 [AMS] Traceback:
[full traceback]
```

---

## Testing Consolidation Task

### Manual Test Output

When running manual consolidation test:

```
🧠 [AMS_TASK] ========================================
🧠 [AMS_TASK] Starting memory consolidation task
🧠 [AMS_TASK] ========================================
🧠 [AMS_TASK] Getting memory manager from backend services...
🧠 [AMS_TASK] ✅ Memory manager ready
🧠 [AMS_TASK] ✅ AMS components are enabled
🧠 [AMS_TASK] Step 1: Checking system idle status...
🧠 [AMS_TASK] ✅ System is idle, proceeding with consolidation
🧠 [AMS_TASK] Step 2: Getting users for today's shard (1/7)...
🧠 [AMS_TASK] Found 3 users for shard 2/7
🧠 [AMS_TASK] Step 3: Executing consolidation for 3 users...
🧠 [AMS_TASK] ========================================
🧠 [AMS_TASK] Consolidation complete in 2.45s
🧠 [AMS_TASK] ✅ Successful: 3
🧠 [AMS_TASK] ❌ Failed: 0
🧠 [AMS_TASK] ⚠️  Skipped: 0
🧠 [AMS_TASK] ========================================
```

---

## Quick Debugging Checklist

### 1. Backend Startup
- [ ] See "Registered built-in task: ams.memory_consolidation"
- [ ] See "AMS Initializing..." message
- [ ] See three ✅ for idle detector, scheduler, tracker
- [ ] See final "✅✅✅ successfully!" message

### 2. Configuration Check
If you see "⚠️ Consolidation disabled":
```bash
# Check config
grep -A 5 "consolidation:" config/defaults/core.yaml

# Should show:
#   enabled: true
```

### 3. Task Registration
```bash
# Check if task is registered
uv run aico logs tail --filter="SCHEDULER" | grep "ams.memory_consolidation"

# Should see:
# 📋 [SCHEDULER] Registered built-in task: ams.memory_consolidation
```

### 4. Manual Test
Look for these key markers:
- ✅ Memory manager ready
- ✅ AMS components are enabled
- ✅ System is idle (or ⚠️ not idle)
- Found X users for shard Y/7
- Final statistics with ✅/❌/⚠️

---

## Common Issues & Solutions

### Issue: No AMS initialization messages
**Cause:** Consolidation disabled in config  
**Solution:** Set `memory.consolidation.enabled: true`

### Issue: "❌ Cannot initialize consolidation scheduler"
**Cause:** Missing working_store, semantic_store, or db_connection  
**Solution:** Check memory manager initialization logs earlier

### Issue: "⚠️ System not idle"
**Cause:** CPU usage above threshold  
**Solution:** Normal - task will skip and try again next time

### Issue: "Found 0 users for shard X/7"
**Cause:** No users in today's shard  
**Solution:** Normal - wait for different day or add more users

---

## Print Statement Locations

### Memory Manager (`manager.py`)
- Line 400: AMS initialization start
- Line 406: Consolidation disabled warning
- Line 416: Idle detector initialized
- Line 430: Consolidation scheduler initialized
- Line 441: Evolution tracker initialized
- Line 445: Success message (triple ✅)
- Line 449: Error message (triple ❌)

### Consolidation Task (`ams_consolidation.py`)
- Line 58-60: Task execution start
- Line 72: Consolidation disabled
- Line 83: Getting memory manager
- Line 93: Memory manager ready
- Line 115: AMS components enabled
- Line 128: Step 1 - Idle check
- Line 145: System is idle
- Line 152: Step 2 - User shard
- Line 181: Found X users
- Line 198: Step 3 - Executing
- Line 233-238: Final statistics
- Line 267: Task execution failed

### Scheduler (`core.py`)
- Line 70: Task registration

---

## Grep Commands for Quick Checks

```bash
# Check AMS initialization
uv run aico logs tail --filter="AMS" | grep "✅✅✅"

# Check task registration
uv run aico logs tail --filter="SCHEDULER" | grep "ams.memory"

# Check consolidation execution
uv run aico logs tail --filter="AMS_TASK"

# Check for errors
uv run aico logs tail --filter="❌"

# Check for warnings
uv run aico logs tail --filter="⚠️"
```

---

## Success Indicators

### Startup Success
```
✅ Task registered
✅ Idle detector initialized
✅ Consolidation scheduler initialized
✅ Evolution tracker initialized
✅✅✅ AMS initialized successfully
```

### Execution Success
```
✅ Memory manager ready
✅ AMS components enabled
✅ System is idle
Found X users
✅ Successful: X
❌ Failed: 0
```

---

## Next Steps After Successful Startup

1. **Verify in logs:**
   ```bash
   uv run aico logs tail --filter="AMS" --limit=50
   ```

2. **Check database:**
   ```bash
   uv run aico db exec "SELECT COUNT(*) FROM consolidation_state"
   ```

3. **Run manual test:**
   ```bash
   uv run python scripts/test_consolidation.py
   ```

4. **Monitor scheduled execution:**
   ```bash
   # Wait for 2 AM or change cron schedule for testing
   uv run aico logs tail --filter="AMS_TASK" --follow
   ```

---

## Emoji Legend

- 📋 Scheduler operations
- 🧠 AMS/Memory operations
- ✅ Success (single = step, triple = major milestone)
- ❌ Error (single = minor, triple = critical)
- ⚠️ Warning/Skip

---

**Quick Start:**
1. Start backend: `uv run aico backend start`
2. Watch for: `✅✅✅ Adaptive Memory System components initialized successfully!`
3. If you see it: **SUCCESS!** AMS is ready.
4. If you don't: Check for ❌ or ⚠️ messages above it.
