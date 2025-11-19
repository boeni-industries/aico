# EmotionEngine Sentiment Analysis Timeout Debugging Log

## Problem Statement
EmotionEngine requests sentiment analysis from modelservice but consistently times out after 25s, even though modelservice processes requests in 0.014-0.070s and publishes responses immediately.

## Symptoms
- ✅ Modelservice receives sentiment requests
- ✅ Modelservice processes in ~0.05s (sub-second)
- ✅ Modelservice publishes responses immediately
- ✅ EmotionEngine's MessageBusClient receives responses (confirmed by `📡 [BUS/emotion_processor] Received topic` logs)
- ❌ EmotionEngine times out after 25s
- ❌ Responses arrive AFTER timeout, in batches
- ❌ `_handle_sentiment_response` finds `pending=[]` and ignores responses

## Timeline of Investigation

### Hypothesis 1: Modelservice Too Slow ❌ DISPROVEN
**Theory:** Modelservice inference takes too long (60s initial model load)
**Evidence Against:**
- Modelservice logs show 0.014-0.070s processing time
- Model is preloaded at startup (no 60s delay)
- First request: 1.420s (includes model load)
- Subsequent requests: 0.014-0.088s

**Status:** ❌ DISPROVEN - Modelservice is fast

---

### Hypothesis 2: Message Bus Broker Delay ❌ DISPROVEN
**Theory:** Messages queued in ZMQ broker for ~25 seconds before forwarding
**Evidence Against:**
- Other services (ConversationEngine, embeddings) work fine with same broker
- No broker configuration issues
- Broker runs in same process, no network delay

**Status:** ❌ DISPROVEN - Broker works fine for other services

---

### Hypothesis 3: Subscription Pattern Mismatch ❌ DISPROVEN
**Theory:** Wildcard subscription not matching response topics
**Evidence Against:**
- Subscription: `modelservice/sentiment/response/v1/emotion_engine/`
- Response topic: `modelservice/sentiment/response/v1/emotion_engine/{correlation_id}`
- MessageBusClient logs show messages ARE received: `📡 [BUS/emotion_processor] Received topic`
- Subscription pattern is correct (prefix match)

**Status:** ❌ DISPROVEN - Subscription works, messages are received

---

### Hypothesis 4: Async Event Loop Blocking ❌ DISPROVEN
**Theory:** `asyncio.wait_for()` blocks event loop, preventing message processing
**Evidence Against:**
- `asyncio.wait_for()` does NOT block the event loop
- `_message_loop` runs concurrently in same event loop
- Messages ARE being received (confirmed by debug logs)
- Other async operations work fine

**Status:** ❌ DISPROVEN - Event loop is not blocked

---

### Hypothesis 5: Cleanup Race Condition ✅ PARTIALLY CONFIRMED
**Theory:** `finally` block in `_get_sentiment_analysis` deletes pending request before response arrives
**Evidence Supporting:**
- Timeout occurs at 25s
- `finally` block executes immediately, deleting `pending_sentiment_requests[request_id]`
- Response arrives shortly after (seen in logs)
- `_handle_sentiment_response` finds `pending=[]` because entry was already deleted
- Pattern unique to EmotionEngine (no other service uses this exact pattern)

**Fix Applied:**
1. On success: Clean up immediately after getting result
2. On timeout: DON'T clean up - leave pending request for late handler
3. In response handler: Clean up after processing response

**Files Modified:**
- `/Users/mbo/Documents/dev/aico/backend/services/emotion_engine.py`
  - Lines 461-470: Removed `finally` block, moved cleanup to success path
  - Line 298: Added cleanup in `_handle_sentiment_response`

**Test Results:**
```
🎭 [EMOTION_ENGINE] ⏱️  Sentiment analysis TIMEOUT after 25.0s - using neutral default
📡 [BUS/emotion_processor] Received topic='modelservice/sentiment/response/v1/emotion_engine/52af8ea3-58ee-4529-933e-ad4b5ae707c0'
🎭 [EMOTION_ENGINE] 🔎 Sentiment response received with correlation_id=52af8ea3-58ee-4529-933e-ad4b5ae707c0, pending=['52af8ea3-58ee-4529-933e-ad4b5ae707c0']
⏱️ [EMOTION_ENGINE] ✅ Response received after 25.003s total latency
🎭 [EMOTION_ENGINE] 📥 Received sentiment response after 25.0s!
🎭 [EMOTION_ENGINE] ✅ Sentiment: positive (confidence=0.42)
```

**Status:** ✅ PARTIALLY FIXED
- ✅ Response handler now finds pending request (`pending=['52af8ea3-58ee-4529-933e-ad4b5ae707c0']`)
- ✅ Response is processed and sentiment extracted
- ✅ Cleanup happens correctly in response handler
- ❌ **BUT** response still arrives exactly at 25.003s (just after timeout)
- ❌ Emotional state still uses neutral default (timeout occurred first)

**New Problem Identified:** Response arrives EXACTLY at 25s, suggesting it's being delayed/queued somewhere for exactly the timeout duration

---

## Key Questions Still Unanswered

1. **Why do responses arrive EXACTLY at 25s?** Modelservice publishes in 0.05s, but EmotionEngine receives after exactly 25.003s
2. ~~**Why do they arrive in batches?**~~ ✅ SOLVED - They were being ignored due to cleanup race condition
3. **What causes the EXACT 25s delay?** Response arrives precisely when timeout completes - suspicious coincidence

## Critical New Observation

**Response arrives at 25.003s - EXACTLY when timeout completes!**

This is NOT a coincidence. The response is arriving precisely when `asyncio.wait_for()` times out. This suggests:

1. **Possibility A:** Response is being held/buffered somewhere and only released when timeout occurs
2. **Possibility B:** The `await asyncio.wait_for()` is somehow blocking message reception until it completes
3. **Possibility C:** There's a synchronization issue where message processing waits for the timeout

**Evidence:**
- First request: `25.003s` total latency
- Modelservice processes in `0.05s`
- Gap of `~24.95s` unaccounted for
- Response arrives IMMEDIATELY after timeout (not minutes later)

## Next Steps

### Hypothesis 6: `recv_multipart()` Blocking Event Loop ✅ ROOT CAUSE FOUND!
**Theory:** `await self.subscriber.recv_multipart()` in `_message_loop` blocks the coroutine, preventing it from processing messages that arrive while `_get_sentiment_analysis` is waiting.

**Root Cause Analysis:**
```python
# In MessageBusClient._message_loop (line 379-381)
topic, message_data = await self.subscriber.recv_multipart()  # ❌ BLOCKS until message arrives
```

**The Problem:**
1. EmotionEngine publishes sentiment request
2. Modelservice responds in 0.05s
3. Response arrives at EmotionEngine's ZMQ socket buffer
4. **BUT** `_message_loop` is blocked in `recv_multipart()` waiting for the NEXT message
5. `_get_sentiment_analysis` waits with `asyncio.wait_for(response_event.wait(), timeout=25.0)`
6. After 25s timeout, `_get_sentiment_analysis` completes and returns
7. **NOW** event loop cycles back to `_message_loop`
8. `recv_multipart()` immediately returns with the message that's been in the buffer for 25s
9. Response is processed, but too late

**Why This Happens:**
- `recv_multipart()` is async but **blocks the coroutine** until data arrives
- While blocked, it doesn't yield to process messages already in the socket buffer
- The message sits in the ZMQ socket buffer waiting for `recv_multipart()` to be called
- Only when `_get_sentiment_analysis` timeout completes does the event loop return to `_message_loop`

**Evidence:**
- Response arrives EXACTLY at 25.003s (when timeout completes)
- Modelservice processes in 0.05s
- Gap of ~24.95s = time message sits in socket buffer
- Other services work fine (they don't have this blocking wait pattern)

**Files Modified for Testing:**
- `/Users/mbo/Documents/dev/aico/shared/aico/core/bus.py` - Added timing to `recv_multipart()` call

**Test Results - ROOT CAUSE 100% CONFIRMED:**
```
📡 [BUS/emotion_processor] Received topic='...' (recv_multipart took 0.000s)
⏱️ [EMOTION_ENGINE] ✅ Response received after 25.002s total latency
⏱️ [EMOTION_ENGINE] ✅ Response received after 75.016s total latency (3 × 25s)
⏱️ [EMOTION_ENGINE] ✅ Response received after 50.011s total latency (2 × 25s)
```

**PROOF:**
- `recv_multipart took 0.000s` = message was ALREADY in socket buffer
- Latencies are EXACT multiples of 25s timeout
- Messages queue up and process in batches when event loop returns to `_message_loop`

**Status:** ✅ ROOT CAUSE 100% CONFIRMED

---

## Architectural Analysis

### The Real Problem: Pattern Mismatch

**ConversationEngine (Correct Async Pattern):**
```python
# 1. Subscribe to response topic
await self.bus_client.subscribe(response_topic, self._handle_llm_response)
# 2. Publish request
await self.bus_client.publish(...)
# 3. Return immediately - callback handles response
# NO BLOCKING!
```

**EmotionEngine (Blocking Anti-Pattern):**
```python
# 1. Create asyncio.Event
response_event = asyncio.Event()
# 2. Publish request
await self.bus_client.publish(...)
# 3. BLOCK waiting for response
await asyncio.wait_for(response_event.wait(), timeout=25.0)  # ❌ BLOCKS!
```

### Why EmotionEngine Blocks
EmotionEngine needs sentiment result **synchronously** to continue processing emotional state. Can't fire-and-forget.

### Solution Options

**Option 1: Make EmotionEngine Async (RECOMMENDED ✅)**
- Follow ConversationEngine pattern
- Publish request, return immediately
- Process emotional state when sentiment callback arrives
- Architecturally sound, no blocking

**Option 2: Add Poller to MessageBusClient (Band-aid ⚠️)**
- Use ZMQ poller with timeout in `_message_loop`
- Allows processing queued messages
- Doesn't fix architectural mismatch
- Other services using `asyncio.wait_for` pattern will have same issue

**Option 3: Redesign Request-Response Pattern (Overkill 🔧)**
- Implement proper async request-response queue
- Too complex for this use case

### Recommendation
**Implement Option 1** - Refactor EmotionEngine to use async callback pattern like ConversationEngine. This is the proper architectural solution.

---

## Solution Implemented ✅

**Refactored EmotionEngine to async callback pattern (Option 1)**

### Changes Made

**1. Split Processing into Two Phases:**
- **Phase 1:** `_handle_conversation_turn()` → `_request_sentiment_analysis()` (non-blocking)
- **Phase 2:** `_handle_sentiment_response()` → `_complete_emotional_processing()` (callback)

**2. New Methods:**
- `_request_sentiment_analysis()` - Publishes request, stores context, returns immediately
- `_complete_emotional_processing()` - Completes appraisal when sentiment arrives
- `_process_emotional_response_with_sentiment()` - Renamed from `_process_emotional_response`, accepts sentiment as parameter

**3. Removed Blocking Code:**
- ❌ Deleted `asyncio.Event()` creation
- ❌ Deleted `asyncio.wait_for(response_event.wait(), timeout=25.0)` blocking wait
- ❌ Removed timeout handling and neutral defaults

**4. Context Storage:**
- `pending_sentiment_requests` now stores: `message_text`, `user_id`, `conversation_id`, `start_time`
- Callback uses this context to complete processing

### Impact on EmotionEngine

**Timing:**
- Emotional states will be published **after** sentiment arrives (not immediately)
- No change to ConversationEngine (already doesn't wait for EmotionEngine)
- Sentiment responses will be processed as they arrive (no more timeouts)

**Behavior:**
- Emotional state generation is now fully async
- No blocking of message loop
- Follows same pattern as ConversationEngine
- Architecturally sound and maintainable

### Expected Results
- ✅ Sentiment responses processed immediately when they arrive
- ✅ No more 25s timeouts
- ✅ No more queued messages in socket buffer
- ✅ Emotional states reflect actual sentiment (not neutral defaults)
- ✅ Message loop can process all messages without blocking

## Test Command
```bash
uv run python scripts/emotion/test_emotion_simulation.py 1e69de47-a3af-4343-8dba-dbf5dcf5f160 2375
```

## Expected Results After Fix
- Responses should still arrive (possibly late)
- `_handle_sentiment_response` should find pending request
- Should see: `⏱️ [EMOTION_ENGINE] ✅ Response received after X.XXXs total latency`
- Should see cleanup happening in response handler
- No more `pending=[]` messages
