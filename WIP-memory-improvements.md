# WIP: Memory / Context Improvements
 
 ## Scope
 
 This document tracks observed working-memory / context issues and the corresponding fixes we implement.

**Non-goals:** Do not change AICO’s multi-tier memory architecture (Working Memory LMDB, Semantic Memory + KG, Behavioral Learning). This document focuses on *mechanics and integration quality*.

 ## Observed issues (from conversation transcript)

- **Identity / role confusion**
  - Assistant addresses the user as `Eve`.
  - Assistant swaps identities (“You are Eve, I am Adam”) even after explicit correction (“You are Eve, I am Michael”).

- **Current-message not being answered (context contamination)**
  - Replies sometimes correspond to an earlier question/topic rather than the latest user input.
  - Example: user provides new facts (daughters, client), assistant responds with unrelated earlier topic (e.g., “serenity” etymology / tingling narrative).

- **Thread / timeline discontinuities**
  - Conversation appears to jump in time and/or across threads while dragging prior metaphors and assumptions.

- **Topic attractor / looping metaphors override new intent**
  - “Flame / cosmos / darkness” theme repeatedly overrides practical intents (meditation advice, etymology question, work context).

- **Weak correction retention / grounding stability**
  - When corrected (e.g., geographic detail), assistant acknowledges but quickly returns to an unrelated monologue, indicating corrections aren’t being stabilized into constraints.

 - **Safety/tone instability (secondary, but impacts perceived coherence)**
   - Tone escalates in intensity in ways that can conflict with user intent and can amplify violent framing.

## Target behavior ("bleeding edge" quality)

- **Answer-the-latest-turn reliability**
  - The response is grounded in the current user message and only uses prior context when relevant.
- **Deterministic context assembly**
  - Prompt context is built from budgeted blocks (not a raw transcript dump).
- **Compression over truncation**
  - Older context is represented via rolling/thread summaries and stable facts/preferences.
- **Corrections persist**
  - User corrections override prior facts; contradictions are handled explicitly.
- **Observability + eval**
  - Each response can be audited: what context was injected, why, and what it cost.

 ## Code touchpoints (where context becomes the final LLM input)

- **Final assembly (backend)**
  - `backend/services/conversation_engine.py` → `_generate_llm_response()`
  - Builds `messages[]` (system + recent history + current user message)
  - Publishes `CompletionsRequest(messages=...)` to `AICOTopics.MODELSERVICE_CHAT_REQUEST`

 - **LLM call (modelservice → Ollama)**
   - `modelservice/core/zmq_handlers.py` → `handle_chat_request()`
   - Forwards to `POST /api/chat` with `messages[]`

## Implementation plan (step-by-step)

### Step 0 — Observability baseline (must-have)

- Ensure backend logs report, per request:
  - model name
  - number of messages
  - system prompt size
  - per-block sizes (see Step 1)
  - number of retrieved items per tier and top scores
- Ensure logs do **not** dump full prompt content at INFO (keep that gated behind DEBUG if ever needed).

### Step 1 — Introduce “memory blocks” and budgets (no summarization yet)

Goal: stop treating context as a single stream.

- Define the blocks used for prompt assembly:
  - System identity & policies
  - Recent turn buffer (Working Memory)
  - Retrieved episodic snippets (Semantic segments)
  - Stable facts & preferences (KG / semantic facts)
  - Behavioral constraints (style preferences / guardrails)
- Allocate explicit budgets (tokens or chars) per block.
- Enforce budgets deterministically.

Acceptance criteria:
- Prompt assembly produces consistent sizes.
- The current user message always has guaranteed budget.

### Step 2 — Fix “answer-the-latest-message” drift

Goal: prevent wrong-thread history and attractor loops from dominating.

- Reduce verbatim history injection to:
  - last 1–2 user/assistant turns max
- Everything older must be either:
  - retrieved (semantic/KG) because it matches the current turn, or
  - summarized (Step 3).
- Add a lightweight “thread gate”:
  - if retrieval confidence is low, inject less context, not more.

Acceptance criteria:
- New user facts/questions are answered directly.
- Identity remains stable even after corrections.

### Step 3 — Add rolling / thread summaries (compression)

Goal: replace truncation with compression.

- Maintain a rolling summary per conversation (and optionally per thread) that is:
  - short, factual
  - updated incrementally
  - stored in memory (working + semantic/KG as appropriate)
- Inject thread summary as a dedicated memory block with its own budget.

Acceptance criteria:
- Older context remains available via summary without injecting raw text.

### Step 4 — Consolidation loop (flush working → long-term)

Goal: keep working memory lightweight and push stable artifacts into long-term stores.

- During idle/background processing:
  - extract stable facts/preferences from recent turns
  - upsert into KG/semantic with provenance
  - update rolling/thread summaries

Acceptance criteria:
- Working memory retrieval can be smaller/faster.
- Long-term recall improves without bloating prompts.

### Step 5 — Conflict-aware updates + correction retention

Goal: treat memory as mutable.

- Implement explicit “update semantics” for facts/preferences:
  - newest correction overrides previous
  - retain provenance (which turn introduced/updated it)
  - decay confidence for old, unconfirmed facts
- Optional: version history for debugging.

Acceptance criteria:
- When the user corrects a fact, the assistant stops repeating the old one.

### Step 6 — Retrieval quality improvements (precision > recall)

Goal: stop injecting irrelevant semantic matches.

- Introduce metadata/type filtering where possible (entity types, relation types).
- Consider two-stage retrieval:
  - fast hybrid search
  - optional reranker for top-N

Acceptance criteria:
- Fewer false positives (“favorite movie” vs “favorite author”).

### Step 7 — Evaluation harness (automate regression detection)

- Add tests/benchmarks for:
  - needle-in-haystack recall
  - “answers latest user turn” drift metric
  - correction retention
  - latency/token cost per response

Acceptance criteria:
- Memory/context changes are measurable and do not regress silently.

 ## Progress log

 - 2026-02-12
   - Added: this tracking document.
  - Next: implement Step 0 (observability baseline) and Step 1 (memory blocks + budgets).
