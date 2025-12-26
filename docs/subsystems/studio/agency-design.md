# Agency – Layout & Content Design

## 1. Information Design Concept

The Agency section visualizes AICO's **autonomous behavior**:

- Goals and intentions.
- Plans and steps.
- Skills and executed tasks.
- Curiosity/interest and proactive engagements.

Conceptually, Agency is a **time-evolving decision system**. The goal is to make this complexity:

- **Understandable** to non-technical users.
- **Fully traceable** for developers and researchers.

Information is organized along two axes:

- **Lifecycle axis**: proposed → active → paused → completed → dropped.
- **Structure axis**: goal → plan → steps → tasks.

The primary views must let users see **what AICO is trying to achieve** and how it flows through concrete actions.

## 2. Page Layout

### 2.1 Main Layout

- **Top row – Current intentions**
  - Intention bar: N most important active goals with status, priority, and origin.

- **Middle – Goal & Plan board**
  - Kanban-style board with columns for lifecycle states.
  - Each column shows goal cards; clicking a goal opens a drawer with its plan.

- **Bottom – Task queues & history**
  - Queue utilization charts (per scheduler queue).
  - Timeline of major agency events (goal creation, plan changes, follow-ups).

## 3. Content Design

### 3.1 Intention Bar

- **Visuals**
  - Horizontal chips/cards representing **current intentions**.
  - Each chip shows title, origin (user/self/curiosity/system), and a short phrase.

- **Functions**
  - Hover/Click → detail drawer with:
    - Full goal description.
    - Linked memories and observations from AMS.
    - Related conversations.

### 3.2 Goal & Plan Board

- **Columns**
  - Proposed, Active, Paused, Completed, Dropped.

- **Goal Cards**
  - Title, origin, priority score, age.
  - Tiny bar indicating progress (steps completed/total).

- **Plan Drawer**
  - Tree or nested list of plan steps.
  - Each step shows:
    - Status (pending/running/done/failed).
    - Bound skill/tool.
    - Linked scheduler tasks.

### 3.3 Task Queues & History

- **Visuals**
  - Bar charts of current queue lengths and throughput per queue.
  - Timeline of key events (goal activations, plan revisions, proactive messaging).

- **Functions**
  - Clicking a bar or event opens a filtered view of associated tasks and goals.

## 4. Navigation & Traceability

- From Agency you can trace:
  - From a goal → its plan → its steps → underlying tasks (scheduler) → logs.
  - From an action back to the **memories and perceptions** that informed it.
- Links to other sections:
  - **Memory & AMS**: for memory references.
  - **Operations**: for task execution and errors.
  - **Emotion** (future): for emotional context during decisions.

## 5. UX Notes

- Strong guardrails against clutter: always limit visible goals per column by default, with filters and search for deep dives.
- Emphasize **plain-language descriptions** of goals and plans to keep Agency human-understandable.
