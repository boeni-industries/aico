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

### Surface Elevation & Visual Hierarchy

**Research-Based Approach** (Material Design 3, Spotify, NN/G):

**Light Mode Elevation:**
- `Background`: `#F5F6FA` (base layer - soft white-neutral)
- `Surface`: `#FFFFFF` (cards, drawers, panels)
- `Elevated`: `#ECEDF1` (hover states, active elements)
- `Shadow`: `rgba(36,52,85,0.09)` (subtle depth)
- `Dividers`: Black at 12% opacity (subtle separation)

**Dark Mode Elevation:**
- `Background`: `#181A21` (base layer - darkest, elevation 0)
- `Surface`: `#21242E` (cards, drawers, panels - elevation 1)
- `Elevated`: `#2F3241` (hover states, active elements - elevation 2, lighter = closer)
- `Surface Tint`: `#B9A7E6` (primary color for Material Design 3 overlays)
- `Borders`: White at 12-20% opacity (visible separation, NOT shadows)
- `Shadow`: **NONE** - shadows don't work in dark mode (research-based)

**High Contrast Modes:**
- Use pure black/white for all surfaces
- Solid dividers (100% opacity) for maximum visibility
- No surface variants (accessibility priority)

**Implementation Strategy:**
1. **Lighter surfaces = higher elevation** (Material Design 3: #181A21 → #21242E → #2F3241)
2. **Visible borders in dark mode** (white at 12-20% opacity, NOT shadows)
3. **Shadows ONLY in light mode** (dark shadows don't work on dark backgrounds)
4. **Surface tint overlays** (optional: blend primary color for elevation)

**Key Principles:**
- **CRITICAL:** Never use shadows in dark mode - they blend into dark backgrounds
- Lighter colors on top in dark mode = closer to viewer (reverse of light mode)
- Use visible borders (white at 20%) instead of shadows for separation
- Dividers adapt: subtle in light (12%), visible in dark (20%), solid in high-contrast (100%)
- All approaches maintain WCAG AA+ compliance

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

**Core Navigation Principles:**
- **Maximum 2-level hierarchy** - Never exceed two levels of navigation depth
- **Eliminate third-level navigation** - Use alternative patterns instead of nested tabs/menus
- **Single-level primary navigation** - 4–5 root items maximum in main navigation
- Mobile: bottom navigation; Desktop: vertical sidebar
- Back/forward always visible and accessible

**Anti-Pattern: Avoid Nested Tabs**
```
❌ BAD: Tab > Sub-Tab > Sub-Sub-Tab
✅ GOOD: Tab > Card Grid > Modal/Dialog
```

**Recommended Navigation Patterns:**

1. **Card-Based Selection Pattern** (for tool/utility selection):
   - Replace nested tabs with visual card grids
   - Fixed card dimensions (280px × 140px recommended)
   - Use `Wrap` layout for responsive behavior
   - Open tools in focused modals/dialogs

2. **Modal Dialog Pattern** (for focused tasks):
   - Use for developer tools, diagnostics, one-off utilities
   - Maintains context while providing focused interaction
   - Prevents navigation stack complexity

3. **Horizontal Tab Pattern** (for main sections):
   - Maximum 4-6 tabs for primary content areas
   - Use `TabController` with `TabBar` and `TabBarView`
   - Each tab contains complete content area, not sub-navigation

### Admin & Settings UI Patterns

**Core Principle: Context-Aware Placement**

- **Primary Rule**: Admin/settings content uses the **main content area** as default, with overlays reserved for specific use cases
- **Three-Pane Layout**: `[Sidebar Nav] [Main Content Area] [Optional Right Panel]`
- **Desktop (≥1024px)**: Persistent sidebar with admin sections in main content area
- **Tablet/Mobile**: Collapsible sidebar, full-width content area

**Content Area Usage:**
- Settings/Preferences, Admin Dashboards, Data Management
- Complex Workflows, Multi-step processes, Detailed forms
- Primary Admin Tasks where users spend significant time

**Overlay Usage (Exceptions):**
- Quick Actions: Simple confirmations, single-field edits
- Contextual Tools: Actions related to specific list/table items  
- Interrupting Workflows: Critical warnings, destructive confirmations
- Developer/Diagnostic Tools: Infrequent utilities like encryption testing
- Progressive Disclosure: Breaking complex tasks into steps

**Implemented Navigation Hierarchy:**
```
Admin (Sidebar Section)
├── Dashboard (Horizontal Tab → Main Content)
├── User Management (Horizontal Tab → Main Content)
├── System Settings (Horizontal Tab → Main Content)
└── Developer Tools (Horizontal Tab → Card Grid)
    ├── Encryption Test (Card → Modal Dialog)
    ├── API Testing (Card → Modal Dialog)
    ├── System Diagnostics (Card → Modal Dialog)
    └── Application Logs (Card → Modal Dialog)
```

**Implementation Details:**
- **Primary Navigation**: Single `TabController` with 4 tabs (Dashboard, User Management, System Settings, Developer Tools)
- **Developer Tools Section**: Uses `Wrap` widget with fixed-size cards (280px × 140px)
- **Tool Access**: Each card opens focused content in modal dialogs
- **Layout**: `SingleChildScrollView` with `Wrap` for responsive card arrangement
- **Hover Effects**: Proper z-index handling with `Material` widget wrapping

**Benefits**: Predictable UX, scalable navigation, context preservation, efficient scanning, platform consistency with desktop application conventions

### System Status & Feedback

- **Progress Indicators**: Clear visual feedback for long-running operations with meaningful status text
- **System Health**: Subtle indicators for connectivity, performance, and capability status
- **Contextual Constraints**: Non-alarming communication of limitations (offline mode, reduced performance)
- **Activity Transparency**: Users always know what the system is processing or waiting for

### Tooltip/Feedback

- Minimal, appears on (focus|hover|repeat usage)
- Caption font, gentle fade in/out; non-intrusive

***

## 7. Navigation Implementation Patterns

### Flutter Implementation Guidelines

**TabController Pattern for Admin Sections:**
```dart
class AdminScreen extends StatefulWidget with TickerProviderStateMixin {
  late TabController _tabController;
  
  @override
  void initState() {
    _tabController = TabController(length: 4, vsync: this);
  }
  
  // Use TabBar with TabBarView for main sections
  TabBar(
    controller: _tabController,
    tabs: [
      Tab(text: 'Dashboard'),
      Tab(text: 'User Management'), 
      Tab(text: 'System Settings'),
      Tab(text: 'Developer Tools'),
    ],
  )
}
```

**Card Grid Pattern for Tool Selection:**
```dart
Widget _buildDeveloperTools(BuildContext context, ThemeData theme) {
  return Padding(
    padding: const EdgeInsets.all(24),
    child: SingleChildScrollView(
      child: Wrap(
        spacing: 16,
        runSpacing: 16,
        children: [
          _buildDeveloperToolCard(/* ... */),
          // More cards...
        ],
      ),
    ),
  );
}

Widget _buildDeveloperToolCard(/* params */) {
  return SizedBox(
    width: 280,
    height: 140,
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(/* card content */),
      ),
    ),
  );
}
```

**Modal Dialog Pattern for Focused Tasks:**
```dart
void _showEncryptionTest(BuildContext context) {
  showDialog(
    context: context,
    builder: (context) => Dialog(
      child: Container(
        width: 800,
        height: 600,
        child: /* embedded tool content */,
      ),
    ),
  );
}
```

***

## 8. Interaction Patterns

- **Micro-interactions:** Button pulse, avatar expression, input shake (error), selection glow—all use **soft purple accent** where appropriate.
- **Transitions:** Slide-in for panels; fade between states/views.
- **Error/Success:** Coral for errors, mint/green for success; always pair color with icon/text.
- **Autonomy Feed:** Proactive suggestions as swipeable card stack, using soft purple border/highlight for AICO prompts.

***

## 9. Accessibility

- All text/interactive color contrast meets WCAG AA+.
- No color is the sole indicator; always pair with icon/label/animation.
- Full keyboard navigation (focus outlines in purple), ARIA roles on interactives, logical tab order.

***

## 10. Layout

- **Grid:** Responsive flex-box/grid—1–2 columns desktop, single column mobile.
- **Avatar** is primary visual focus on home.
- **Main input** always persistently accessible, beneath/overlaying avatar as space allows.

***

## 11. Theming & Adaptivity

- **Tokenized colors and spacing** for easy theme updates (JSON/YAML).
- Avatar and controls modular; layout adapts gracefully across device types.
- **Embodiment mode:** Larger touch targets for AR/VR, rearranged navigation and input for spatial/modal environments.

***

## 12. Content & Tone

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
| Navigation   | Max 2-level hierarchy, card grids + modals, no nested tabs            |
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

