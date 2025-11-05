# Procedural Memory: The Adaptive Learning System

The procedural memory system transforms AICO from a reactive assistant into an adaptive learning companion. It enables AICO to learn, adapt, and personalize its behavior based on user interaction, moving beyond simple pattern matching to genuine skill acquisition. This system is designed to be modular, explicit, and continuously improving, ensuring that AICO evolves with each user relationship.

## Overview

Procedural memory is AICO's system for learning *how* to interact. While semantic memory stores facts ("what"), procedural memory stores skills ("how"). It governs AICO's communication style, response formatting, proactivity, and other behaviors. By learning a library of skills, AICO can tailor its interactions to individual users, different contexts, and even specific times of day, making every conversation feel natural and intuitive.

The architecture is built on four pillars of modern AI research:
1.  **Skill-Based Modular Architecture**: Procedures are stored as discrete, interpretable "skills" rather than opaque patterns.
2.  **Reinforcement Learning from Human Feedback (RLHF)**: Learning is driven by explicit user feedback, providing a strong and clear signal for adaptation.
3.  **Meta-Learning for Rapid Adaptation**: AICO learns *how to learn*, allowing it to adapt to new users and changing preferences with minimal data.
4.  **Self-Correction and Exploration**: The system actively explores new interaction styles and learns from both successful and unsuccessful outcomes to refine its skills.

## Core Function: Skill-Based Interaction

Procedural memory is modeled as a **Skill Store**, a library of discrete, context-aware procedures that AICO can learn and apply. This is more modular and interpretable than a monolithic set of learned patterns.

- **What is a skill?** A specialized, context-dependent procedure. Examples:
    - `summarize_technical_document`: Provides concise, bulleted summaries.
    - `casual_chat_evening`: Uses informal language and shows more proactivity.
    - `code_review_feedback`: Delivers constructive feedback on code snippets politely.

- **Skill Attributes**: Each skill has a defined trigger (context), a procedure (action), and a confidence score that is updated through feedback.

## Learning System Architecture

### 1. Reinforcement Learning from Human Feedback (RLHF)

Explicit user feedback is the primary driver for skill acquisition and refinement. This provides a much stronger learning signal than relying on implicit pattern detection alone.

- **Feedback Mechanism**: After AICO applies a skill, the user is presented with a simple, non-intrusive feedback option in the UI (e.g., thumbs up/down).
- **Reward Signal**: This feedback acts as a reward signal. Positive feedback reinforces the skill by increasing its confidence score, while negative feedback weakens it and encourages the system to try an alternative.
- **Multi-User Personalization**: For a multi-user environment like a family, the system learns a unique preference profile (a latent vector) for each user. This allows AICO to resolve conflicting preferences, learning that "Dad prefers concise answers" while "Sarah prefers detailed explanations."

### 2. Meta-Learning for Rapid Adaptation

To quickly adapt to new users or changing preferences, AICO uses a meta-learning approach. It learns *how to learn* interaction styles, rather than starting from scratch with each user.

- **How it Works**: The model's parameters are split into two parts:
    1.  **Shared Parameters**: Capture general principles of good interaction, trained across all users.
    2.  **Context Parameters**: A small, user-specific set of parameters that are quickly updated based on a few interactions.
- **Benefit**: This allows for extremely fast personalization and reduces the amount of data needed to learn a new user's preferences.

### 3. Self-Correction and Exploration (Agent Q Model)

AICO actively refines its skills by learning from both its successes and failures.

- **Exploration**: Occasionally, AICO will try a slightly different interaction style and ask for feedback (e.g., "I usually use bullet points, but would a paragraph be better here?"). This is a form of active learning to discover better procedures.
- **Self-Critique**: When an interaction receives negative feedback, the system logs it as an "unsuccessful trajectory."
- **Preference Optimization**: Using an algorithm like Direct Preference Optimization (DPO), the system learns to prefer successful interaction patterns over unsuccessful ones. This explicitly teaches the model what *not* to do, leading to more robust and reliable behavior.

## Implementation Strategy

### Phase 1: Skill Store and Explicit Feedback
- Implement the `Skill` class and `SkillStore` using libSQL.
- Integrate a simple RLHF mechanism (e.g., thumbs up/down) in the UI that adjusts a skill's confidence score.
- Define a set of foundational "base skills" for AICO to start with.

### Phase 2: Personalized and Active Learning
- Introduce latent variable modeling to create a unique preference vector for each user based on their feedback history.
- The `SkillStore` will match skills based on both conversation context and the user's preference vector.
- Implement a simple exploration strategy for AICO to actively query for feedback on new interaction styles.

### Phase 3: Adaptive Intelligence with Meta-Learning
- Implement a meta-learning architecture (e.g., CAVIA) to enable rapid adaptation to new users.
- Incorporate a self-correction loop (inspired by Agent Q) where AICO learns from both positive and negative outcomes to refine its skill-selection policy.

## Integration Points & System Synergies

Procedural memory is not an isolated system; it is deeply integrated with AICO's other core capabilities, creating powerful synergies that enhance the entire platform.

### Autonomous Agency
Procedural memory provides the **"how"** for the agency's **"what."** When the agency's goal-generation system decides to act (e.g., proactively start a conversation or offer help), the procedural skill library defines the *method* of that interaction—the tone, style, and timing that has been learned to be most effective for that specific user and context.

### Social Relationship Intelligence
The multi-user personalization learned via RLHF is a direct input to the social relationship model. Each user's unique preference vector becomes a core component of their relationship graph, allowing AICO to seamlessly switch between learned interaction skills (e.g., `casual_chat_dad` vs. `homework_help_sarah`) based on who it's talking to.

### Emotional Intelligence
Procedural memory learns the user's preferred ways for AICO to **express** its simulated emotions. For example, it can learn whether a user finds a direct statement of empathy ("I understand you're feeling down") more or less effective than a subtle, supportive action (like suggesting a calming activity). This makes AICO's emotional expression more personalized and impactful.

### Embodiment & Presence
Learned procedures can extend beyond text to include non-verbal cues. The system can learn which gestures, tones of voice, or avatar expressions are most positively received by the user during different types of interactions.

## Value Proposition

This advanced procedural memory system elevates AICO from a knowledgeable assistant to a truly adaptive companion that:
- **Learns Faster**: Adapts to new users and preferences in just a few interactions.
- **Is More Personal**: Understands and navigates the conflicting preferences of multiple users.
- **Is More Robust**: Learns from its mistakes and actively explores better ways to interact.
- **Feels More Natural**: Moves beyond rigid patterns to a flexible, skill-based understanding of communication.

By integrating these state-of-the-art techniques, AICO's procedural memory will become a cornerstone of its ability to form genuine, evolving relationships.

## Appendix: Foundational Research

The architecture described in this document is inspired by several key research papers in the fields of AI agency, reinforcement learning, and meta-learning.

- **Modular AI Architecture**:
  - [Procedural Memory Is Not All You Need: Bridging Cognitive Gaps in LLM-Based Agents](https://arxiv.org/abs/2505.03434)
  - This paper advocates for augmenting LLMs with modular semantic and associative memory systems, which inspires our skill-based architecture.

- **Personalized Reinforcement Learning**:
  - [Personalizing Reinforcement Learning from Human Feedback with Variational Preference Learning](https://arxiv.org/abs/2408.10075)
  - This work provides the foundation for our multi-user personalization, using latent variables to model diverse user preferences.

- **Meta-Learning for Fast Adaptation**:
  - [Fast Context Adaptation via Meta-Learning (CAVIA)](https://arxiv.org/abs/1810.03642)
  - This paper's approach to partitioning model parameters informs our strategy for rapid adaptation to new users with minimal data.

- **Agent Self-Correction**:
  - [Agent Q: Advanced Reasoning and Learning for Autonomous AI Agents](https://arxiv.org/abs/2408.07199)
  - This research inspires our self-correction and exploration mechanism, particularly the use of preference optimization (like DPO) to learn from both successful and unsuccessful interactions.
