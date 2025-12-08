# Full Localisation Notes (WIP)

## 1. Agency System – Localisation Impact (Summary)

- **Language state & routing**
  - Per-user primary language and per-conversation active language must be available to ConversationEngine and AgencyPlugin.
  - Agency components use this to choose prompt templates and the language of all user-facing text.

- **Prompting & generation**
  - Internal reasoning prompts, rule identifiers, and enums remain in English as the canonical/master language.
  - All user-facing outputs (goal/plan summaries, explanations, consent prompts, reflection feedback) must be rendered in the active language.

- **Content metadata**
  - Optional `language` tags in memory items, lessons, and KG/world-model nodes/edges help with retrieval and explanation; not strictly required for v1.

- **Values & Ethics & Consents**
  - Policy rules and consents are stored in English as canonical structures.
  - User-facing consent descriptions and policy explanations need localised text per language (either via extra display fields or an external localisation layer keyed by rule/consent IDs).

- **Skills & Behavioural Learning**
  - Skills should carry supported_language metadata; selection must avoid skills that cannot operate in the current language, unless explicitly allowed.

- **Embodiment & Lifecycle**
  - Core lifecycle logic is language-agnostic; only room labels, activity names, and any spoken/visible comments require localisation.

- **Logging & Audit**
  - Logs and internal audit messages can remain English-only.

## 2. Non-Agency Localisation Gaps

- [x] **Conversation & prompts (core, non-agency)**
  - [x] Ensure ConversationEngine tracks per-user primary language and per-conversation active language.
  - [ ] Audit core system prompts and templates so user-facing text is generated in the active language (English-only internals allowed).

- [ ] **Memory UI / Memory Album**
  - [ ] Localise Memory Album labels, section titles, and user-facing explanations.
  - [ ] Optionally tag Memory Album entries with `language` to support language-aware browsing and summarisation.

- [ ] **Frontend & 3D Flat**
  - [ ] Localise room names, activity labels, tooltips, and any on-screen text in the 3D flat.
  - [ ] Ensure embodiment-related notifications/comments shown in UI follow the user’s language.

- [ ] **Onboarding, Help, and CLI Messages**
  - [ ] Keep CLI/tooling messages English-only for now, but document that assumption.
  - [ ] Localise onboarding flows, in-app help, and user-facing diagnostics in the primary supported languages.

- [ ] **Errors, Validations, and Status Messages**
  - [ ] Introduce a minimal localisation mechanism for user-visible error/validation messages returned by backend APIs.
  - [ ] Keep internal log messages and exception details in English; translate only the surfaced, user-facing summaries.

## 3. Implemented Localisation Prep (Current State)

- **Core schema migration (SchemaVersion 19)**
  - Added `users.primary_language`, `user_memories.language`, `kg_nodes.language`, and `skills.supported_languages` (all ISO/BCP-47 codes).
- **Conversation language signal**
  - `UserProfile.primary_language` populated via API and CLI (`user-create --language`).
  - `ConversationEngine.UserContext.conversation_language` initialized from `primary_language` and passed through to:
    - `MemoryManager.store_message(..., language=...)` (working + semantic memory)
    - Knowledge graph node creation (`kg_nodes.language`)
    - Skill metadata (`skills.supported_languages`) for future language-aware selection.
- **Frontend integration**
  - User networking models and domain entity now include `primaryLanguage`.
  - JSON (de)serialization maps `primaryLanguage` ↔ `primary_language` correctly.

