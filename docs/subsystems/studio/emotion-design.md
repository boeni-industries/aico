# Emotion – Layout & Content Design

## 1. Information Design Concept

Emotion is a **first-class domain** in Studio. It visualizes AICO&apos;s **internal emotional state** over time and its relationship to conversations, agency activity, and memory.

The design goals are:

- Expose the full richness of the C‑CPM-based emotion simulation without overwhelming the user.
- Provide **professional-grade tools** for inspecting emotional dynamics, crises, and regulation.
- Maintain **traceability** from any emotional state back to:
  - The conversation turns that triggered it.
  - Relevant goals, plans, and tasks.
  - Related memories and album entries.

Emotion views are organized around three synchronized perspectives:

1. **Time** – how emotion evolves (timeline strip).
2. **Space** – where emotion sits in valence–arousal space (circumplex).
3. **Distribution** – how often each label/state occurs.

## 2. Page Layout

### 2.1 Main Layout

- **Top band – Emotion strip (timeline)**
  - Full-width, low-height strip (40–60px) showing emotional state over a selectable time range.
  - X-axis = time, encoded through thin vertical segments.

- **Middle – Valence–arousal circumplex**
  - Compact 2D plot of recent states in Russell&apos;s circumplex space.
  - Points colored consistently with the strip.

- **Bottom – Label distribution & linked events**
  - Bar chart or donut of label frequencies.
  - Linked list of key episodes and transitions (stress episodes, resolutions, crisis regulation).

All three panels are **linked via brushing**: selecting a time range in the strip filters the circumplex points, label distribution, and event list.

## 3. Emotion Strip Design

### 3.1 Data Model

Each history sample provides:

- `timestamp`
- `valence` (−1.0 … 1.0)
- `arousal` (0.0 … 1.0)
- `intensity` (0.0 … 1.0)
- `label.primary` ∈ {neutral, calm, curious, playful, warm_concern, protective, focused, encouraging, reassuring, apologetic, tired, reflective}

### 3.2 Visual Encoding

- **X-axis (time)**
  - Strip segmented into uniform bins (per turn or fixed time interval, e.g. 30–60s).

- **Color = valence × arousal**
  - Hue encodes **valence**:
    - Negative → cooler indigo/blue.
    - Neutral → desaturated blue-gray.
    - Positive → teal/mint (aligned with Studio accent palette).
  - Saturation/brightness encodes **arousal**:
    - Low arousal → darker, more desaturated.
    - High arousal → brighter, more saturated.

- **Opacity/line weight = intensity**
  - Low intensity → faint, semi-transparent.
  - High intensity → fully opaque.

- **Episode overlays**
  - Stress episodes (sustained negative valence + high arousal) indicated by a subtle glow band.
  - Resolution episodes (sustained positive valence after stress) indicated by a different, calm band.

### 3.3 Interaction

- Hover on a segment:
  - Tooltip with timestamp, `label.primary`, valence, arousal, intensity.
- Drag to brush a time range:
  - Highlights the range in the strip.
  - Filters the circumplex and distribution views.
  - Opens a detail drawer with:
    - Conversation turns in that window.
    - Any goals, plans, or tasks active in that window.
    - Relevant memories and album entries.

## 4. Valence–Arousal Circumplex

- **Layout**
  - Circular or square plot representing valence (x-axis) and arousal (y-axis).
  - Recent emotion points plotted as small dots, colored with the same mapping as the strip.

- **Information**
  - Shows clusters of states (e.g. calm vs playful vs warm_concern) independent of exact time.
  - Optional hull/contour around dense regions to show typical operating zone.

- **Interaction**
  - Hover reveals aggregate stats for nearby points.
  - Clicking a cluster applies a filter back to the timeline (show only times in that region).

## 5. Distribution & Episode Panel

- **Label distribution**
  - Bar chart of frequency for each primary label over the current time range.
  - Optional grouping into families (calm/reflective vs playful/curious vs protective/warm_concern).

- **Episode list**
  - Table/timeline of key episodes:
    - Stress episodes (start, peak, resolution).
    - Crisis-regulated periods.
    - Long calm/reflective phases.
  - Each row links to a brushed region in the strip.

## 6. Navigation & Traceability

- From Emotion, users can:
  - Jump to **Conversation** views for specific time windows.
  - Jump to **Agency** for associated goals/plans active during an episode.
  - Jump to **Memory & AMS** for memories created or tagged during intense emotions.

- From other domains:
  - Goals, plans, and memories can link back to Emotion with pre-selected time ranges.

## 7. Metrics & Telemetry

Core metrics that feed this page (see `metrics.md` for full definitions):

- `intelligence.emotion.coverage` – coverage of emotion classification.
- `emotion.timeline.samples` – number of history samples in a given window.
- `emotion.labels.distribution` – distribution of primary labels over time.
- `emotion.episodes.count` – count of identified episodes (stress, resolution, crisis).

These metrics support performance tuning and long-term analysis without cluttering the main UI.

## 8. UX Notes

- Emotion views favor **smooth, calm visuals**; no harsh rainbow heatmaps.
- All colors respect Studio&apos;s contrast and accessibility rules.
- The strip and circumplex are optimized for expert interpretation but remain approachable:
  - Clear legends.
  - Tooltips and inline explanations.
  - Progressive disclosure of advanced diagnostic overlays.
