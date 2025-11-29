# AICO by Boeni Industries – Go-To-Market (GTM) Strategy

## 1. Positioning & Narrative

**Core positioning (external tagline)**  
AICO by Boeni Industries is an open-source, local-first AI companion that’s emotionally present, privacy-preserving, and technically serious enough for researchers and builders.

**Three pillars (repeat everywhere):**
- **Companion, not chatbot** – emotional intelligence, relationship evolution (Companion → Confidante → Sidekick → Co‑Adventurer).
- **Local-first & encrypted** – CurveZMQ, SQLCipher, key management, no cloud lock‑in.
- **Serious architecture** – message bus, modelservice, memory system (working + semantic + KG + AMS).

**Founder positioning (Michael):**  
Founder-engineer at Boeni Industries, researching long-term AI companionship, memory, and embodiment, building AICO as a reference architecture and real product.

Use this in bios, talks, and social profiles.

**Current assets:**
- **Website (primary landing, Squarespace):** https://boeni.industries/aico – AICO by Boeni Industries
- **GitHub (code + issues + discussions):** https://github.com/boeni-industries/aico
- **LinkedIn (company):** https://www.linkedin.com/company/boeni-industries/
- **Community (real-time chat):** Discord server for the AICO community (to be created, linked from README and website)

---

## 2. Product Line

**AICO Core (MIT, open-source)**  
Open-source, local-first AI companion platform by Boeni Industries. For builders, tinkerers, and researchers who want full control and are happy to self-host and self-support.

- Full platform as in this repo: backend, modelservice, CLI, Flutter frontend, memory system, knowledge graph.
- Community docs and community support (issues, future Discord/Matrix).
- DIY install, configuration, monitoring, and backups.

**AICO Pro (paid, serious individuals & small teams)**  
Ready-to-use AICO with assisted setup, curated configuration, and priority support for power users and small teams.

- Guided setup and recommended production defaults (models, security, backups).
- Opinionated deployment recipes and upgrade guidance.
- Priority support (e.g. email/Slack with response targets).
- Additional convenience features that don’t require heavy infra: more polished Studio/admin flows for single-instance setups, enhanced Memory Album UX, extra evaluation/diagnostic tools.

**AICO Enterprise (paid, high-touch)**  
Enterprise-grade AICO with advanced governance, integrations, and SLAs for organizations embedding AICO into products or workflows.

- Architecture and integration support (on-prem, VPC, hybrid).
- Enterprise features: SSO/SAML/OIDC, RBAC, audit trails, multi-team/tenant management.
- Advanced AMS/KG/Studio views for governance and analytics.
- Commercial license (OEM/embedding rights), SLAs, security reviews, and dedicated support.
- Optionally: fully managed AICO operated by Boeni Industries.

---

## 3. Commercial Model

**AICO Core**  
- Free (MIT, open-source).  
- Monetization role: top-of-funnel for adoption, contributors, and credibility.

**AICO Pro**  
- Paid subscription aimed at serious individuals and small teams.  
- Revenue components:
  - Recurring subscription for support and “production-ish” guidance.
  - Optional one-time onboarding fee for white-glove setup and configuration.
- Value proposition: “Make AICO actually run reliably for you without weeks of yak shaving.”

**AICO Enterprise**  
- High-touch consulting + annual contract for organizations.  
- Revenue components:
  - Initial project/engagement for architecture, integration, and rollout support.
  - Annual support + commercial license (and optionally managed operation) with SLAs.
- Value proposition: “Embed AICO in your product or organization with governance, compliance, and a vendor that stands behind it.”

This model lets AICO Core stay genuinely open-source while Pro and Enterprise monetize your time, expertise, and higher-value features instead of restricting the core.

---

## 4. Launch Phases (6–12 Weeks)

### Phase 1 – Foundation (Weeks 1–2)

**Goal:** Create canonical URLs and “explainers” you can point to for months.

**Long-form cornerstone posts (publish on your own site as the source of truth, optionally cross-post):**
1. **Why I’m building a local-first AI companion (AICO)**
   - Vision: companion vs tool, family angle, embodiment.
   - Privacy, autonomy, local-first architecture.
2. **Inside AICO’s architecture: message bus, memory, and modelservice**
   - System → Domain → Module → Component hierarchy.
   - CurveZMQ-encrypted message bus, FastAPI gateway, modelservice + Ollama.
   - Memory: LMDB working memory, ChromaDB, knowledge graph, AMS.
3. **Designing an AI that remembers you: AICO’s memory system**
   - Working vs semantic vs KG vs AMS + Memory Album.
   - Concrete user stories: how AICO recalls details and evolves.

Publishing order of precedence:
- Primary: **https://boeni.industries/aico** (or a dedicated `/blog`/`/articles` path under that domain).
- Optional distribution: cross-post to Medium/Substack/Dev.to *with canonical link* back to your own site.

**Repo & docs polish:**
- Add a **“Start here”** section to README:
  - For users: requirements, install, “what works today”.
  - For contributors: how to run, 3–5 good-first-issue links.
- Add architecture diagram and link to docs/architecture.
- Ensure links to website, docs, Discord/Matrix (if used) are prominent.

---

### Phase 2 – Distribution & Awareness (Weeks 2–6)

**Goal:** Be consistently visible where builders, researchers, and potential partners are.

**Twitter/X (primary for reach among AI/builders):**
- 3–5 posts/week.
- Formats:
  - Threads: e.g. “How AICO’s memory system works (and why I didn’t just use a vector DB).”
  - Short code/architecture snippets (CurveZMQ, LMDB, AMS, KG diagrams).
  - UI gifs (glassmorphism, skeleton loader, connection rings).
- Reuse phrases: *local-first*, *private AI companion*, *CurveZMQ-encrypted*, *hybrid memory*.

**LinkedIn (credibility, future enterprise buyers):**
- 1–2 posts/week.
- Focus:
  - Milestones: “AICO v1.0.0 core released”, “Memory evaluation framework live”.
  - Thought pieces: privacy, AI companionship, ethical agency.

**GitHub & docs (conversion to contributors):**
- Maintain clear issues with labels (good first issue, roadmap, help wanted).
- Keep README + docs index in sync with public narrative.
- Add basic project board for visibility (Now / Next / Later).

**HN & Reddit (traffic spikes + early adopters):**
- Prepare **Show HN**:
  - Title: `Show HN: AICO – a local-first AI companion with serious memory and security`.
  - Content: what it is, what works today, architecture highlights, how to try it.
- Cross-post explanations to:
  - r/MachineLearning, r/LocalLLaMA, r/selfhosted, r/homelab.
- Answer every serious comment with technical depth.

---

### Phase 3 – Deep Dives & Authority (Weeks 4–12)

**Goal:** Establish you + AICO as reference for local-first AI companions, memory systems, and secure AI infra.

**Deep-dive articles / posts (blog + cross-post):**
- CurveZMQ & Security:
  - “CurveZMQ in production: 100% encrypted message bus for AI systems.”
- Memory & Retrieval:
  - “Hybrid memory for AI companions: LMDB + ChromaDB + Knowledge Graph + AMS.”
  - “Evaluating long-term memory in AI companions (AICO’s evaluation framework).”
- Frontend & Embodiment:
  - “Designing an emotionally-aware Flutter UI for an AI companion.”
  - “From Thermion to Three.js: building AICO’s 3D avatar pipeline.”

**Talks & conferences:**
- Turn best articles into talk proposals:
  - Python/FastAPI conferences (message bus, memory, modelservice).
  - Flutter conferences (companion UI & offline-first). 
  - ML / HCI events (AI companionship, emotional intelligence).

**YouTube (optional but powerful):**
- 10–20 minute videos:
  - “AICO architecture overview (whiteboard).”
  - “Implementing CurveZMQ in Python: a tour of AICO’s message bus.”
  - “AICO’s memory system: from user input to hybrid retrieval.”
- Cut short clips for X/LinkedIn.

---

## 3. Channels & Formats Overview

**Primary channels:**
- **GitHub** – truth source (code, issues, Discussions, releases), conversion to contributors.
- **Website (Squarespace, https://boeni.industries/aico)** – canonical marketing/landing page.
- **Twitter/X** – day-to-day visibility, networking.

**Secondary channels:**
- **Discord** – real-time community chat (support, dev discussion).
- **GitHub Discussions** – asynchronous, searchable Q&A and design discussions.
- **LinkedIn** – credibility, future enterprise partners.
- **Hacker News & Reddit** – spikes of attention, early OSS users.
- **YouTube** – deep dives and “face of the project”.
- **Conferences / meetups** – high-leverage authority and relationships.

**Formats per channel:**
- GitHub: README, architecture docs, issues, project board.
- Blog: essays, technical deep dives, case studies.
- X: threads, diagrams, short code snippets, milestone posts.
- LinkedIn: narrative posts, milestone announcements, thought pieces.
- HN/Reddit: “Show” posts, technical writeups, AMA-style comment replies.
- YouTube: architecture walkthroughs, coding sessions, demos.

---

## 4. Monetization Strategy (OSS-Compatible)

AICO stays open-source but provides multiple monetizable layers.

### 4.1 Product / Services Lines

**1) AICO Pro – Managed / Assisted Deployments**
- For users/companies who want the local-first privacy guarantees without operational burden.
- Offer:
  - Assisted or fully managed deployment (on their hardware or their cloud, keys under their control).
  - Pro tier with:
    - Automatic updates & security patches.
    - Optional managed modelservice with heavier models (licensing handled by you).
    - Monitoring, backup, recovery recipes.

**2) Commercial License / Enterprise Features**
- Keep core AICO under a permissive or strong copyleft OSS license.
- Offer **commercial licensing** for:
  - Companies embedding AICO in proprietary products.
  - Organizations needing SLAs, long-term support, compliance.
- Optionally keep some advanced features as **enterprise add-ons**:
  - Multi-device roaming & P2P sync.
  - Advanced AMS dashboards and behavior analytics.
  - Enterprise Studio features (user management, observability).

**3) Consulting & Customization**
- High-margin work for organizations wanting custom companions:
  - Custom personalities & Modelfiles (Eve-like characters for brands/products).
  - Domain-specific plugins (healthcare coach, team assistant, education companion).
  - Hardware and embodiment (desktop devices, robotics, AR/VR integrations).

**4) Paid Support & Training**
- Support subscriptions for companies using OSS AICO in production.
- Training/workshops:
  - “Building local-first AI companions using AICO.”
  - “Designing privacy-first AI architectures with CurveZMQ and encrypted databases.”

### 4.2 Align Content With Monetization

Every significant public artifact (article, talk, video) should have **two CTAs**:

- **OSS / community CTA:**
  - “Star AICO on GitHub, join the community, pick up a good-first issue.”

- **Commercial CTA:**
  - “If you want a private, local-first AI companion or to embed AICO in your product, reach out at michael@boeni.industries for consulting, integration, or commercial licensing.”

Place CTAs at the end of blog posts, talk slides, video descriptions, and repository README.

---

## 5. Concrete Next Actions (0–2 Weeks)

1. **Publish first cornerstone article**
   - “Why I’m building a local-first AI companion (AICO)” on your site.
   - Cross-post to Medium/Substack.

2. **Write and publish architecture deep dive**
   - “Inside AICO’s architecture: message bus, memory, and modelservice.”
   - Include diagrams and code snippets linked to the repo.

3. **Polish GitHub landing experience**
   - Add “Start here” section for users + contributors.
   - Link to docs, first issues, community channel.

4. **Start consistent Twitter/X presence**
   - 3–5 posts per week focused on specific parts of AICO (memory, security, UI).

5. **Draft and schedule Show HN**
   - Prepare the text and assets.
   - Launch once docs and quickstart are solid.

6. **Define first commercial offering page**
   - Simple page: “AICO Pro & Consulting” with 2–3 packages and clear contact.

This document should be treated as a living GTM artifact and refined as traction and feedback come in.

