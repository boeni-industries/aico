# Progressive Disclosure & Thinking Process Indicator Design (2025)

**Version:** 1.0  
**Date:** October 21, 2025  
**Status:** Design Proposal  
**Research-Based:** 2025 UX Best Practices, Award-Winning Visual Fidelity

---

## Executive Summary

This document proposes a complete redesign of AICO's progressive disclosure system with specific focus on **thinking process indication when the right drawer is collapsed**. The design integrates 2025 best practices from industry leaders (ChatGPT, Claude, Perplexity), award-winning visual fidelity principles, and AICO's core design philosophy of **immersive, emotionally-present AI companionship**.

**Core Challenge:** How do we indicate AICO's thinking process when the right drawer (which shows streaming inner monologue) is collapsed, while maintaining immersion, clarity, and emotional connection?

**Design Philosophy:** Transform system state indicators from technical notifications into **ambient storytelling elements** that enhance the companion relationship rather than interrupt it.

---

## 1. Research Foundation (2025 Best Practices)

### 1.1 Progressive Disclosure Principles (LogRocket, IxDF 2025)

**Key Findings:**

1. **Layered Disclosure Strategy:**
   - **Level 1 (Ambient):** Subtle, non-intrusive presence indicators
   - **Level 2 (Contextual):** Hover/focus reveals preview information
   - **Level 3 (Full):** Explicit expansion shows complete detail
   - **Maximum 3 levels** to avoid cognitive overload

2. **Conditional Disclosure:**
   - Information appears only when conditions are met
   - Active streaming vs. completed thoughts require different treatments
   - Empty states should invite interaction, not feel broken

3. **Best Practice Guidelines:**
   - Keep disclosure levels below 3 for optimal usability
   - Use consistent patterns throughout interface
   - Prioritize simplicity over feature exposure
   - Test with real users to validate effectiveness

### 1.2 AI Assistant Thinking Indicators (2025 Industry Analysis)

**ChatGPT o1 Reasoning Display:**
- Collapsible "Thought" sections with clear visual hierarchy
- Streaming indicator shows active processing
- Purple accent for reasoning sections (matches AICO)

**Claude Artifacts Pattern:**
- Side panel for extended thinking/artifacts
- Clear separation between conversation and meta-content
- Smooth expand/collapse animations
- Ambient glow indicates active processing

**Perplexity Search Reasoning:**
- Inline reasoning cards that expand on demand
- Progressive loading with skeleton states
- Clear "thinking" vs "complete" states

**Key Insights:**
- **Dual-state design:** Active streaming requires prominent indication; completed thoughts use subtle presence
- **Spatial separation:** Thinking content lives in dedicated space
- **Progressive animation:** Breathing/pulsing effects indicate active processing
- **Clear affordances:** Users must understand how to access full thinking content

### 1.3 2025 UI Trends (Storify Agency, Inkbot Design)

**Award-Winning Visual Fidelity Principles:**

1. **Progressive Blur Techniques:** Guided focus through selective blur, layered depth without clutter
2. **AI-Aware Design Language:** Subtle indicators for AI-generated content, breathing animations show "alive" systems
3. **Microinteractions:** Sub-100ms response times, personality through motion
4. **Ambient Notification Design:** Non-intrusive presence indicators, contextual emergence

---

## 2. Current Implementation Analysis

### 2.1 Existing Right Drawer System

**Current Collapsed Indicator:**
- Vertical bar (6px wide) with gradient purple glow
- Breathing animation when streaming
- Multi-layer shadows for depth
- Static presence when thoughts exist but not streaming

**Strengths:**
- ✅ Clear visual distinction between streaming vs. static states
- ✅ Breathing animation aligns with AICO's "alive" design principle
- ✅ Soft purple accent maintains brand consistency

**Limitations:**
- ❌ **No preview of thinking content** when collapsed
- ❌ **No indication of thought count** or history depth
- ❌ **No hover interaction** to peek at content
- ❌ **No visual cue** that drawer can be expanded
- ❌ **Vertical bar alone lacks semantic meaning**

---

## 3. Proposed Solution: Multi-Layer Ambient Thinking Indicator

### 3.1 Three-Layer Disclosure System

#### **Layer 1: Ambient Presence (Always Visible)**

**Visual Elements:**

1. **Enhanced Vertical Bar (Right Edge - Thinking Drawer)**
   - Width: 8px (increased from 6px)
   - Gradient: Vertical purple with breathing animation
   - States: Active streaming (prominent pulse) vs. Recent thought (subtle glow) vs. Idle (invisible)
   - **Position:** Left edge of the RIGHT drawer (thinking/inner monologue drawer)

2. **Thought Count Indicator (Top of Bar)**
   - Small circular badge with glassmorphic background
   - Shows number of thoughts in history (e.g., "3")
   - Pulses gently when new thought added
   - Fades to 50% opacity after 3 seconds

3. **Streaming Status Icon (Middle of Bar)**
   - Animated sparkles icon (auto_awesome_rounded)
   - Visible only during active streaming
   - Rotates slowly (360° over 3 seconds)
   - Pulses in sync with bar breathing

#### **Layer 2: Contextual Preview (Hover/Long-Press)**

**Interaction:**
- Desktop: Hover over vertical bar (300ms delay)
- Mobile: Long-press (500ms) on bar area

**Preview Card Design:**
- Floating tooltip card (280px width, max 400px height)
- Heavy glassmorphism (30px blur, semi-transparent)
- **Slides in from RIGHT edge**, overlaying conversation area
- Shows last 2-3 thoughts (truncated to ~60 characters)
- Streaming thought shows live updates
- "Expand for full history →" action hint
- Smooth slide-in animation from right (200ms)

#### **Layer 3: Full Disclosure (Expanded Drawer)**

- Current `ThinkingDisplay` widget (keep as-is)
- Timeline view with all thoughts
- Streaming content with live updates
- Scrollable history

### 3.2 State Transitions & Animations

**State Machine:**
```
IDLE (no thoughts, invisible)
  ↓ Thought added
STATIC (subtle glow, thought count visible)
  ↓ Streaming starts
STREAMING (prominent breathing, icon visible)
  ↓ Streaming ends
STATIC (return to subtle presence)
```

**Animation Specifications:**
- Breathing Pulse: 3000ms, easeInOut, 0.6 → 1.0 opacity
- Thought Count Pulse: 600ms, elasticOut, scale 1.0 → 1.2 → 1.0
- Preview Slide-In: 200ms, easeOut, +20px → 0px translation (from RIGHT)
- Drawer Expansion: 300ms, easeOutCubic, 80px → 320px width

**Performance Targets:**
- All animations: 60fps minimum
- Hover response: <100ms
- Preview card: <200ms to visible
- Drawer expansion: <300ms total

---

## 4. Implementation Specifications

### 4.1 Widget Architecture

**New Components:**

1. **`AmbientThinkingIndicator`** - Layer 1 ambient presence
2. **`ThinkingPreviewCard`** - Layer 2 preview tooltip
3. **`ThinkingIndicatorController`** - State management

**Modified Components:**

1. **`HomeScreen._buildRightDrawer()`** - Integrate new indicator
2. **`ThinkingDisplay`** - No changes (already implements Layer 3)

### 4.2 Visual Specifications

**Colors (Dark Mode):**
```dart
purpleAccent: Color(0xFFB9A7E6)
glassBackground: Colors.white.withValues(alpha: 0.04)
glassBorder: Colors.white.withValues(alpha: 0.20)
textSecondary: Colors.white.withValues(alpha: 0.60)
```

**Dimensions:**
```dart
barWidth: 8.0
previewWidth: 280.0
previewMaxHeight: 400.0
drawerExpandedWidth: 320.0
```

### 4.3 Accessibility

**Keyboard Navigation:**
- Tab to focus bar → Enter/Space to expand → Escape to collapse

**Screen Readers:**
```dart
Semantics(
  label: 'Thinking indicator',
  hint: isStreaming 
    ? 'AICO is actively thinking. Press to view reasoning.'
    : 'AICO has $thoughtCount thoughts. Press to view.',
  button: true,
)
```

**Reduced Motion:**
- Disable breathing animations
- Use static opacity instead of pulse
- Instant transitions

---

## 5. User Experience Flows

### Flow 1: Active Streaming Discovery

1. User asks question → Avatar enters "thinking" mode
2. **Right drawer** ambient bar begins breathing purple
3. Streaming icon appears and rotates on right edge
4. User hovers over right edge → Preview card slides in from right showing live thinking
5. User clicks preview → Right drawer expands to full display

**Key Moments:** Ambient awareness → Progressive reveal → Intentional expansion

### Flow 2: Returning to Accumulated Thoughts

1. User opens app → **Right edge** ambient bar visible with thought count "5"
2. User hovers over right edge → Preview slides in from right showing last 2-3 thoughts
3. Preview shows "⋮ 3 more thoughts"
4. User clicks "Expand" → Right drawer expands to full timeline

**Key Moments:** Information scent → Preview sampling → History awareness

### Flow 3: New User Onboarding

1. First message → Ambient bar appears on **right edge**
2. Subtle tooltip: "AICO's inner monologue" (first-time only, near right edge)
3. User hovers over right edge → Preview slides in from right revealing thinking content
4. User clicks → Right drawer expands, discovers full thinking feature

**Key Moments:** Gentle onboarding → Discovery through interaction → Aha moment

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- Create `AmbientThinkingIndicator` widget
- Implement Layer 1 with breathing animation
- Add thought count badge and streaming icon
- Update `HomeScreen` integration

### Phase 2: Preview Layer (Week 2)
- Create `ThinkingPreviewCard` widget
- Implement hover/long-press detection
- Build preview content truncation
- Add slide-in animation

### Phase 3: Polish & Refinement (Week 3)
- Add smooth drawer expansion
- Implement reduced-motion support
- Add first-time user tooltip
- Optimize performance

### Phase 4: Documentation & Launch (Week 4)
- Update design system docs
- Create implementation guide
- Record demo videos
- Monitor analytics

---

## 7. Success Metrics

**Quantitative:**
- 80% thinking feature discovery rate
- 60% preview card usage rate
- 60fps animation performance
- <100ms hover response time

**Qualitative:**
- 4.0+ satisfaction scores
- "I understand what AICO is thinking"
- "The indicator is helpful and non-intrusive"
- "Animations feel natural and smooth"

---

## 8. Design Rationale

**Alignment with 2025 Best Practices:**
- ✅ 3-layer progressive disclosure (LogRocket 2025)
- ✅ Conditional disclosure for different states (IxDF)
- ✅ Ambient notification design (UI Trends 2025)
- ✅ AI-aware design language (Inkbot 2025)
- ✅ Microinteractions with personality (Industry standard)

**AICO's Unique Approach:**
- Ambient storytelling vs. technical notifications
- Emotional coherence with companion personality
- Preview layer for quick context (industry gap)
- Three-layer disclosure vs. binary expand/collapse

---

## Conclusion

This design transforms AICO's thinking indicator from a simple status bar into an **award-winning progressive disclosure system** that:

1. **Maintains immersion** through ambient storytelling
2. **Preserves flow** with non-intrusive presence
3. **Enables discovery** through progressive revelation
4. **Builds trust** through transparency
5. **Follows 2025 best practices** from industry leaders

The three-layer system (Ambient → Preview → Full) provides the perfect balance between **awareness and detail**, allowing users to stay connected to AICO's reasoning process without interrupting their conversation flow.

---

## Alternative Design Concept (Future Exploration)

**Stacked Thought Boxes Approach:**

Instead of a single ambient indicator, display **individual thought boxes** stacked vertically on the right edge:

```
┌─────────────────────────────────────────┐
│                             ╭─╮         │  ← Thought #3 (newest)
│                             │✨│        │     Sparkle = actively streaming
│                             ╰─╯         │
│                             ╭─╮         │  ← Thought #2 (completed)
│   [Conversation Area]       │ │         │     Hover shows preview
│                             ╰─╯         │
│                             ╭─╮         │  ← Thought #1 (oldest)
│                             │ │         │
│                             ╰─╯         │
└─────────────────────────────────────────┘
```

**Key Features:**
- New box appears from top for each thought AICO makes
- Each box individually hoverable for thought-specific preview
- Sparkle icon appears on currently active/streaming thought
- Click individual box → Expand that specific thought
- Click stack → Expand full drawer with all thoughts

**Advantages:**
- Direct access to individual thoughts without opening drawer
- Visual representation of thought count (no badge needed)
- More tangible/discoverable interaction model
- Users can quickly scan recent thinking activity

**Challenges:**
- Vertical space consumption (could get cluttered with many thoughts)
- Need smart stacking/collapsing logic (e.g., show last 5, collapse older)
- More complex animation choreography
- Requires careful spacing and sizing for mobile

**Potential Hybrid:**
- Show last 3-5 thoughts as stacked boxes
- Older thoughts collapse into "⋮ N more" indicator
- Maintains direct access while preventing clutter

**Status:** Documented for future iteration. Current single-indicator approach prioritizes minimalism and follows industry patterns (ChatGPT, Claude). Stacked approach could be explored in V2 based on user feedback and usage patterns.
