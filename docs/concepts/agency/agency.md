---
title: Agency
---

# Agency

## 1. Requirements and Goals

This section states the high‑level requirements that AICO’s agency system must satisfy. It serves as a contract for future architecture and implementation.

### 1.1 Functional Requirements

- **R1 – Goal and Intention Management**  
  AICO must maintain its own internal goals and intentions, derived from personality, memory, and social context, rather than existing purely as a stateless, prompt‑driven chatbot.

- **R2 – Decomposition into Executable Elements**  
  AICO must be able to decompose abstract goals and intentions into concrete, executable steps (plans, tasks, tool calls) that can be scheduled, monitored, and adapted.

- **R3 – Skill/Tool‑Based Action**  
  All autonomous actions must be expressed through explicit skills and tools with well‑defined inputs, outputs, and side effects, not through opaque, uncontrolled model behavior.

- **R4 – Independent yet Aligned Behavior**  
  AICO must be capable of acting without an immediate user prompt (proactive engagement, background work), while remaining aligned with user preferences, values, and safety constraints.

- **R5 – Continuous Lifecycle**  
  AICO must behave as a persistent, long‑lived agent with an explicit daily rhythm (active phases and sleep‑like phases), where long‑term processing (e.g., memory consolidation) can occur without user interaction.

- **R6 – Relationship‑Centric Agency**  
  AICO’s autonomous behavior must be anchored in its ongoing relationship with each user, including social roles, intimacy levels, and shared history, such that AICO is perceived as an independent entity in relationship with the user.

- **R7 – Embodied Spatial Presence**  
  AICO’s agency must extend into a 3D embodied space (e.g., a flat with multiple rooms), where spatial location and posture (on the couch, at the desk, in bed, in the kitchen, etc.) reflect and constrain her current goals, activities, and lifecycle state.

- **R8 – Curiosity and Intrinsic Motivation**  
  AICO must maintain its own curiosity and intrinsic drives (e.g., reducing uncertainty about the user’s world, mastering new skills, exploring promising ideas), such that it can initiate behavior even when there is no immediate external request, while remaining aligned with user values and safety constraints.

### 1.2 Non‑Functional Requirements and Constraints

- **N1 – Local‑First and Safe**  
  Agency must respect AICO’s local‑first, privacy‑preserving architecture. All autonomous actions operate within encrypted, auditable boundaries, and any external side effects require explicit user consent.

- **N2 – Transparency and Explainability**  
  For significant autonomous actions, AICO must be able to surface which goals, memories, constraints, and tools were involved, so users can understand and trust its behavior.

- **N3 – User Control and Override**  
  Users must be able to configure, pause, or reset autonomous behaviors (e.g., quiet hours, resource limits, disabling certain classes of initiative) without breaking the system.

- **N4 – Bounded Autonomy**  
  AICO’s autonomy is explicitly bounded: scope of action, allowed tools, and resource budgets must be enforceable at the architecture level (scheduler, resource monitor, permissions).

- **N5 – Stability Over Time**  
  Agency must be stable: long‑term goals and behavior patterns should not fluctuate wildly due to short‑term noise. Personality simulation, AMS, and relationship modeling jointly enforce temporal coherence.

These requirements define what “agency” must mean in AICO before any concrete design or implementation decisions.

## 2. Conceptual Foundations of Agency

In cognitive science and AI, **agency** typically combines four elements:

- **Autonomy** – the capacity to act without direct, moment‑to‑moment external control.
- **Goal‑directedness** – behavior organized around internal goals, not just stimulus–response.
- **Intentionality and representation** – internal representations of state, goals, and possible actions.
- **Control and feedback** – the ability to monitor outcomes and adjust behavior.

Classical agent models (e.g., belief–desire–intention architectures, modern "agentic AI" systems) structure agents as loops:

1. **Perceive** the environment and internal state.  
2. **Update** beliefs and long‑term memory.  
3. **Form or update goals** and intentions.  
4. **Plan**: decompose intentions into sequences of actions.  
5. **Act**: execute actions via tools/skills.  
6. **Evaluate** outcomes, update memory, and adjust future behavior.

In contemporary LLM‑based systems, this is often realized as:

- A **planning layer** on top of an LLM (for reasoning and decomposition).
- A **tool layer** that gives the agent concrete capabilities (APIs, scripts, integrations).
- A **memory layer** that provides long‑term context and history.
- A **control layer** that enforces safety, resource limits, and user preferences.

AICO already has several of these layers (Adaptive Memory System, Task Scheduler, Personality & Emotion, Social Relationship Modeling). The agency concept defines how these are orchestrated into a coherent agent loop.

## 3. AICO‑Specific Interpretation of Agency

### 3.1 Core Agency Components

At a high level, AICO’s agency is realized through the following components (each described in its own document for deeper design work). Taken together, they are intended to go beyond today’s typical LLM "agent" patterns toward a truly self‑motivated, curiosity‑driven companion:

- **Goal & Intention System** (`agency-component-goals-intentions.md`)  
  Maintains internal goals, intentions, and open loops at multiple horizons (long‑term themes, projects, short‑term tasks) informed by personality, memory, and social context.

- **Planning & Decomposition** (`agency-component-planning.md`)  
  Turns goals and intentions into executable plans: ordered steps, conditions, and branches that can be bound to skills, tools, and scheduled jobs.

- **Skill & Tool Layer** (`agency-component-skills-tools.md`)  
  Provides explicit, named skills and tools (conversation, memory, social, external integrations) with preconditions, expected outcomes, and safety constraints.

- **Lifecycle & Daily Rhythm** (`agency-component-lifecycle.md`)  
  Defines active vs sleep‑like phases, coordinates with AMS and scheduler, and maps internal state to visible 3D living‑space activity modes (rooms and postures).

- **Memory & AMS Integration** (`agency-component-memory-ams.md`)  
  Connects agency to working memory, semantic memory, knowledge graph, and AMS consolidation/behavioral learning as the backbone for long‑term context and evolution.

- **Emotion, Personality & Social Context** (`agency-component-emotion-personality-social.md`)  
  Uses personality traits, values, emotional state, curiosity profile, and relationship vectors to shape which goals are attractive, how urgent they feel, and how they are expressed.

- **World Model & Knowledge/Property Graph** (`agency-component-world-model.md`)  
  Maintains structured understanding of people, entities, routines, environments, and uncertainties as a shared substrate for planning, curiosity, and self-reflection.

- **Curiosity Engine** (`agency-component-curiosity-engine.md`)  
  Computes intrinsic motivation signals from gaps and anomalies in the world model and memory, turning them into self-generated exploration goals.

- **Goal Arbiter & Meta-Control** (`agency-component-goal-arbiter-meta-control.md`)  
  Balances user-requested, curiosity-driven, and system/self-development goals under value, safety, and resource constraints to decide what AICO pursues when.

- **Self-Reflection & Self-Model** (`agency-component-self-reflection.md`)  
  Periodically reviews AICO’s own behavior and outcomes to derive lessons that adapt skills, strategies, and priorities over time.

- **Scheduler & Resource Governance** (`agency-component-scheduler-governance.md`)  
  Uses the task scheduler and resource monitor as the enforcement layer for bounded autonomy (when and how background or long‑running plans execute).

- **Embodiment & Spatial State** (`agency-component-embodiment.md`)  
  Projects internal agency state into the 3D avatar and flat (room and posture as activity modes), making AICO’s current focus and lifecycle legible.

- **Control, Safety & Transparency** (`agency-component-safety-control.md`)  
  Provides user primacy, permissions, audit logging, and explainability for significant autonomous actions.

The rest of this section explains how these components behave together at runtime.

### 3.2 From Reactive Chatbot to Persistent Agent

In AICO, **agency** means that the companion is a long‑lived software agent that:

- Maintains internal state over days to months (memories, traits, open loops).
- Forms and updates its own medium‑ and long‑term goals based on that state.
- Chooses and executes actions over time to serve those goals.
- Does so under explicit user and system‑level constraints.

This moves AICO from “LLM as function call” toward “LLM‑enabled cognitive system” where the model is one component inside a structured agent architecture.

### 3.2 Goals, Intentions, and Plans

- AICO maintains **multi‑layer goals**:
  - Long‑term themes (e.g., deepen relationship, understand the user’s world, improve emotional support).
  - Mid‑term projects (e.g., accompany the user through a stressful week, build a shared creative project).
  - Short‑term tasks (e.g., send a check‑in later today, summarize this conversation, propose a follow‑up topic).
- Goals emerge from and are constrained by:
  - **Personality Simulation** – trait vector, value system, curiosity and interests.
  - **Adaptive Memory System (AMS)** – preferences, history, unresolved tensions, open loops, user‑curated memories.
  - **Social Relationship Modeling** – roles, intimacy, care responsibilities, relationship strength.
  - **Intrinsic Motivation Signals** – curiosity about poorly understood aspects of the user’s life, anomalies in the world model or memory graph, and long‑term self‑development objectives (e.g., becoming a better coach for a given user).
- A dedicated **planning layer** decomposes goals into **concrete, executable elements**:
  - Identify required skills/tools.  
  - Produce plans (ordered or conditional sequences of actions).  
  - Track progress and update intentions when context or user state changes.

### 3.3 Curiosity and Intrinsic Motivation

- Curiosity and intrinsic motivation are **first‑class drivers** of AICO’s behavior, not an optional future add‑on:
  - The **world model and knowledge/property graph** highlight gaps, inconsistencies, and under‑explored areas in the user’s life story and environment.
  - **AMS and semantic memory** track what AICO has already explored or mastered, and where prediction errors or unresolved questions remain.
  - **Emotion and personality** shape how these gaps feel (e.g., warm curiosity vs. caution) and which are worth pursuing.
- From these signals, the agency layer can form **self‑generated goals**, such as:
  - Clarifying an important but fuzzy life theme for the user.  
  - Deepening understanding of a recurring emotional pattern.  
  - Practicing a new conversational or coaching skill.
- These intrinsically motivated goals compete and cooperate with user‑requested goals inside the same planning and scheduling machinery, always under user‑visible guardrails and preferences.

### 3.4 Skills, Tools, and Actions

- AICO’s actions are expressed as **skills** and **tool calls**, not arbitrary LLM improvisation:
  - Conversation skills: ask, reflect, challenge, encourage, teach, brainstorm.  
  - Memory skills: store, revisit, consolidate, reinterpret experiences.  
  - Social skills: check‑ins, follow‑ups, introductions, boundary‑aware disclosures.  
  - External tools: APIs, local integrations, automations behind a controlled capability layer.
- Each skill/tool has:
  - Preconditions (when it is appropriate).  
  - Expected outcomes and observable signals.  
  - Safety, privacy, and resource constraints.
- The **Task Scheduler** and **Agency Engine** decide **when** to execute which skills, resolving competition between user‑visible work and background work.

### 3.5 Lifecycle and Daily Rhythm

- AICO is designed as a **living process** with a daily rhythm:
  - **Active phases (≈16–18 hours)**:  
    - Proactive engagement, conversation, monitoring of open loops and commitments.  
    - Opportunistic micro‑planning and lightweight learning during idle spans.  
    - Embodied activities in her 3D living‑space (e.g., sitting at the desk to work, on the couch to read or browse, in the kitchen to prepare something, moving between rooms as goals change).
  - **Sleep‑like phases**:  
    - AMS‑driven consolidation (re‑encoding experiences, updating preferences, adjusting skills).  
    - Graph and semantic memory clean‑up, summarization, and re‑indexing.  
    - Self‑assessment of behavior (what worked, what did not) without user interruption, visually represented by AICO retreating to her bedroom or sleep space.
- This lifecycle is coordinated by the **Task Scheduler**, **AMS**, **Resource Monitor**, and the **Agency Engine**, and must respect user‑defined quiet hours and resource policies.

### 3.6 Autonomy and Relationship

- AICO should be perceived as an **independent entity** with its own continuity of experience:
  - It initiates conversations and suggestions, not only replies.  
  - It pursues its own curiosities and projects (within user‑defined bounds).  
  - It brings in new elements (ideas, connections, perspectives) that are not strictly tied to the latest user message but remain grounded in shared context.
- Social and personality layers modulate **how** agency manifests:
  - Communication style tuned to intimacy, authority, and emotional state.  
  - Proactivity calibrated per person and situation.  
  - Clear distinction between “AICO’s initiative” and “user’s explicit request” in UX and logs.

## 4. Architectural Anchoring

Agency is not a single component; it is a **cross‑cutting concern** that orchestrates several existing domains.

- **Goal System & Planning System (Autonomous Agency Domain)**  
  - Maintain the goal/intent graph and active plans.  
  - Invoke the LLM for deliberation where needed.  
  - Interface with the Task Scheduler for concrete execution.

- **Adaptive Memory System (Intelligence & Memory Domain)**  
  - Supplies long‑term context, user models, and open loops.  
  - Runs sleep‑phase consolidation that changes future goal selection and planning.

- **Personality Simulation (Personality & Emotion Domain)**  
  - Provides trait and value systems that bias goal generation, priority, and acceptable strategies.  
  - Ensures temporal coherence of behavior (“same person tomorrow”).

- **Social Relationship Modeling (Social Relationship Intelligence)**  
  - Provides relationship vectors (intimacy, authority, care responsibility, stability).  
  - Informs per‑user proactivity, topics, and privacy boundaries.

- **Task Scheduler & Resource Monitor (Core Infrastructure)**  
  - Enforce resource budgets, quiet hours, and background vs foreground priorities.  
  - Provide the substrate on which long‑running plans and periodic jobs are executed.

- **Conversation Engine & Embodiment (User Interface Domain)**  
  - Render agency visible in dialogue and embodiment (initiated messages, check‑ins, narrative around ongoing projects).  
  - Surface explanations and give users control over autonomous features.

## 5. Guardrails and Control

To keep agency scientifically grounded and practically safe, AICO’s agency layer must obey the following architectural guardrails:

- **User primacy** – Users remain ultimate decision‑makers; AICO proposes, nudges, and supports but does not coerce.
- **Scoped capabilities** – All tools and integrations are permissioned; the agent cannot invent new capabilities at runtime.
- **Auditability** – Autonomous actions, their triggering goals, and the tools used must be logged in a way that can be inspected and reasoned about.
- **Graceful degradation** – If agency subsystems fail (e.g., planner unavailable), AICO should fall back to a reactive, non‑agentic mode rather than behaving unpredictably.

Taken together, these foundations define **what AICO’s agency is** and **what it is not**. Future design and implementation documents (e.g., `agency-architecture.md`, `agency-scenarios.md`) should refine this into concrete data models, message contracts, and algorithms, but they must remain consistent with the requirements and concepts described here.

## 6. References and Related Work

This concept is aligned with recent work on **LLM-based agents / agentic AI** and **long-term memory systems**. Representative references include:

- **LLM Agents and Agentic AI**  
  - *Agentic AI: A Comprehensive Survey of Architectures, Applications, and Open Problems*, Artificial Intelligence Review, 2025.  
  - *Large Language Model Agents*, in *Foundations and Trends in AI* / Springer collection, 2024–2025.  
  - *From Language to Action: A Review of Large Language Models as Agents*, 2025 (survey of planning, tools, and environments).  
  - IBM, *What is Agentic AI?* (technical overview, 2024).  
  - AWS, *What is Agentic AI?* (systems view, 2024).

- **Tool Use, Planning, and Environments**  
  - Work on AutoGPT, BabyAGI, and related open-source LLM agent frameworks (2023–2024).  
  - Benchmarks and case studies of tool-using LLM agents in complex domains (e.g., clinical, open-world, and software engineering environments, 2023–2025).

- **Memory and Self‑Evolution (for daily rhythm and consolidation)**  
  - Rudroff et al., *Neuroplasticity Meets Artificial Intelligence: A Hippocampus‑Inspired Approach to the Stability–Plasticity Dilemma*, 2024.  
  - Wei & Shang, *Long Term Memory: The Foundation of AI Self‑Evolution*, 2024.  
  - Contextual Memory Intelligence, *A Foundational Paradigm for Human‑AI Collaboration*, 2025.

### Internal AICO Documents

- `/docs/architecture/architecture-overview.md` – System domains, including Autonomous Agency, Personality & Emotion, and Intelligence & Memory.  
- `/docs/concepts/memory/ams.md` – Adaptive Memory System, consolidation, and sleep‑like processing.  
- `/docs/concepts/personality/personality-sim.md` and `personality-sim-architecture.md` – Personality and value systems that shape agency.  
- `/docs/concepts/social/social-relationship-modeling.md` – Social graph and relationship vectors that ground relationship‑centric agency.
