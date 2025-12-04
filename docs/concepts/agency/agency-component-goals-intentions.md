---
title: Agency Component – Goal & Intention System
---

# Goal & Intention System

## Component Description

## 1. Purpose

The Goal & Intention System maintains AICO’s **ongoing goals, intentions, and open loops** across different time horizons. It is the central registry of “what AICO is currently trying to achieve”.

- Long‑term themes (e.g., deepen relationship, understand user’s world).  
- Mid‑term projects (e.g., support the user through a stressful week).  
- Short‑term tasks (e.g., send a check‑in tonight, summarize today’s chat).

It integrates signals from personality, memory/AMS, social modeling, and emotion to:

- Maintain a graph of **goals, sub‑goals, and dependencies** (projects, tasks, maintenance activities).
- Track **status, priority, and ownership** per goal (user‑initiated vs AICO‑initiated).
- Expose APIs for **creating, updating, pausing, and retiring** goals and intentions.
- Feed the **Planning System** with selected intentions to be decomposed into executable plans.

The system must support not only user‑related goals but also a small set of **agent‑self goals and hobbies**: recurring projects and interests AICO pursues for her own curiosity and development (e.g., learning domains, conversational styles, organizing her 3D living space), as long as they remain aligned with user wellbeing and value/ethics constraints.

Future iterations of this document will specify data models, APIs, and update rules in detail.
