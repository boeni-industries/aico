# AICO UI/UX Design Principles

This document integrates all previous guidance—including your latest preference to use **soft purple as a stylistic accent, not as a large-area base**—and provides a full, ready-to-copy markdown spec for creating a modern, minimal, adaptive, emotionally-present, and consistent AICO interface.

***

## 1. Core Design Rules

**Minimalism:**

  - Use ample whitespace; remove visual clutter and superfluous decoration.
  - Typography is kept crisp, simple, and unobtrusive.

**Intuitive, Zero-Barrier Start:**  

  - All interactions are immediately understandable; no up-front instructions.
  - Key actions are visually prominent and consistently placed.
  - Users explore and discover depth over time—never confronted with complexity up front.

**Progressive Disclosure:**

  - Information hierarchy reveals complexity gradually based on user needs and expertise.
  - Primary functions are immediately visible; advanced features discoverable through natural exploration.
  - Context-sensitive help appears when needed, not as persistent clutter.

**System Transparency:**

  - Users always understand what the system is doing and why.
  - Long-running operations show clear progress with meaningful status updates.
  - System constraints (network, CPU, capabilities) are communicated contextually without alarm.
  - Overall system health visible through subtle, non-intrusive indicators.

**Responsiveness:**  

  - App loads and reacts instantly, with smooth feedback via subtle, purposeful micro-interactions.

**Adaptive & Embodiment-Ready:**  

  - Design is fully responsive—from mobile to desktop to mixed/AR devices.
  - Layout and key components adapt to available space, embodiment, or modality.

***

## 2. Color Concepts

### Base Palette

- `Background`: `#F5F6FA` (soft white-neutral)
- `Surface` (cards/panels): `#FFFFFF`
- `Shadow`: `rgba(36,52,85,0.09)`
- **Never use purple or any accent as a large background color.**

### Brand & Accents

- `Primary Accent`: **Soft Lavender** `#B8A1EA`  
  - Use strictly for emphasis: buttons, highlights, interactive states, mood/status rings, avatar glows, progress bars, etc.
- `Secondary Accents` (optional/limited):  
  - Mint `#8DD6B8` (good for success, activity tags)
  - Coral `#ED7867` (error/warning only)
  - Muted Green `#8DD686` (confirmation)
- `Dark Mode Equivalents`: Mirror above, always keeping high contrast (background: `#181A21`, surface: `#21242E`, accent: `#B9A7E6`)

### Color Application Rules

- Large backgrounds stay neutral.
- **Purple accents are consistent and restrained—used for CTAs, focus, avatar emotion, and highlight elements.**
- Maintain color contrast for accessibility (WCAG AA+ for interactive/text).

***

## 3. Shape & Gestalt Concepts

**Shape Language:**  

  - Rounded, soft rectangles for cards, panels, buttons (`16–24px` radius).
  - Circular/elliptical zones for avatars and key emotion/status elements.
  - Avoid sharp, angular geometry.

**Gestalt:**  

  - Clear 1–2 level groupings; do not visually nest deeply.
  - Action controls are horizontally clustered (at the bottom of cards or panels).
  - Use soft drop shadows or gentle elevation—no harsh borders.

**Element Consistency:**  

  - All highlight states (focus, selected, pulsing) use the **soft purple accent**.
  - Animated micro-interactions use breathing/pulse effects—never distracting.

***

## 4. Typography

| Type         | Font             | Size      | Weight |
|--------------|------------------|-----------|--------|
| Headline 1   | Inter, Sans-Serif| 2.0rem    | 700    |
| Headline 2   | Inter, Sans-Serif| 1.5rem    | 600    |
| Subtitle     | Inter, Sans-Serif| 1.125rem  | 500    |
| Body Main    | Inter, Sans-Serif| 1.0rem    | 400    |
| Caption      | Inter, Sans-Serif| 0.875rem  | 400    |
| Button Text  | Inter, Sans-Serif| 1.0rem    | 600    |

- **Spacing:** 1.5× font size line-height.
- **Letter Spacing:** 0.02em on titles/headlines.

***

## 5. Spacing & Sizing

- **Unit grid:** 8px multiples.
- **Container max-width:** 1200px (desktop), 100% (mobile).
- **Padding:** Cards/panels: 24px; buttons: 24px horizontal, 12px vertical.
- **Avatar Sizes:** Main: 96px; Mini: 32px.

***

## 6. Components

### Buttons

- Types: `primary`, `secondary`, `minimal`, `destructive`
- Primary uses **soft purple** for background and focus states
- All have rounded corners, clear elevation on hover; spinner for loading

### Input Fields

- Types: `text`, `voice`, `dropdown`, `emotion selector`
- Rounded, with subtle purple focus/active underline or ring
- States: active, error (coral border), disabled (dimmed)

### Avatar

- Always central, circular, animates with mood/states (idle, thinking, speaking, attention)
- Mood/status rings in **soft purple** or derivative hues

### Cards & Panels

- Rounded, airy, subtle elevation (shadow)
- Bottom-aligned horizontal action row

### Navigation

- Flat structure: 4–5 root items only
- Mobile: bottom navigation; Desktop: vertical sidebar
- No deep nesting; back/forward always visible and accessible

### System Status & Feedback

- **Progress Indicators**: Clear visual feedback for long-running operations with meaningful status text
- **System Health**: Subtle indicators for connectivity, performance, and capability status
- **Contextual Constraints**: Non-alarming communication of limitations (offline mode, reduced performance)
- **Activity Transparency**: Users always know what the system is processing or waiting for

### Tooltip/Feedback

- Minimal, appears on (focus|hover|repeat usage)
- Caption font, gentle fade in/out; non-intrusive

***

## 7. Interaction Patterns

- **Micro-interactions:** Button pulse, avatar expression, input shake (error), selection glow—all use **soft purple accent** where appropriate.
- **Transitions:** Slide-in for panels; fade between states/views.
- **Error/Success:** Coral for errors, mint/green for success; always pair color with icon/text.
- **Autonomy Feed:** Proactive suggestions as swipeable card stack, using soft purple border/highlight for AICO prompts.

***

## 8. Accessibility

- All text/interactive color contrast meets WCAG AA+.
- No color is the sole indicator; always pair with icon/label/animation.
- Full keyboard navigation (focus outlines in purple), ARIA roles on interactives, logical tab order.

***

## 9. Layout

- **Grid:** Responsive flex-box/grid—1–2 columns desktop, single column mobile.
- **Avatar** is primary visual focus on home.
- **Main input** always persistently accessible, beneath/overlaying avatar as space allows.

***

## 10. Theming & Adaptivity

- **Tokenized colors and spacing** for easy theme updates (JSON/YAML).
- Avatar and controls modular; layout adapts gracefully across device types.
- **Embodiment mode:** Larger touch targets for AR/VR, rearranged navigation and input for spatial/modal environments.

***

## 11. Content & Tone

- **Voice:** Warm, friendly, direct. Never clinical.
- **Messaging:** Helpful and actionable; errors are gentle, not alarming.
- **Language:** Inclusive, jargon-free, clear.

***

## 13. Copy-Paste Reference Table

| Section      | Principle/Rule                                                        |
|--------------|-----------------------------------------------------------------------|
| Color        | White base, soft purple highlights, minimal color elsewhere           |
| Shape        | Rounded rects/circles, soft elevation, no harsh borders               |
| Gestalt      | 1–2 grouping levels, horizontal action rows, distinct layers          |
| Typography   | Inter, minimal weights, spaced for clarity                            |
| UI Flow      | No-barrier start, flat navigation, immediate affordances              |
| Responsiveness| Modular for web/mobile/AR, avatar-centric, input always at hand      |
| Feedback     | Subtle confirmations, avatar expression, micro-interactions highlight |
| Accessibility| Color contrast, icons+labels, focus outlines, ARIA roles              |

***

## 14. Sample UI Structure Outline

```text
[Avatar Centerpiece]
    | 
[Primary Input (conversation, voice, mood)]
    |
[Emotion/Status Bar]     [Quick Actions Row]
    |
[Relationship Timeline]  [Memory/Privacy Drawer]
    |
[Autonomy/Suggestions Feed]

[Optional: Extensions/Admin slide-in; minimalist menu hides behind gesture or icon]
```

