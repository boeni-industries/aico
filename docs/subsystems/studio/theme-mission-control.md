# AICO Studio – Sci-Fi Mission Control Theme Specification

> **Version:** 1.0  
> **Last Updated:** January 2026  
> **Scope:** Complete visual styling specification for the System Health sci-fi mission control theme  
> **Status:** Experimental - Currently applied to System Health page only

This document provides exact specifications for the sci-fi mission control aesthetic developed for the System Health page. This theme can be extended to other high-stakes, technical interfaces where a more advanced, purposeful visual language is appropriate.

---

## 1. Design Philosophy

### 1.1 Core Principles

**Purposeful, Not Decorative:**
- Every visual element serves a functional purpose
- No "bogus information" for visual interest
- Data-driven aesthetics

**Mission-Critical Aesthetic:**
- Inspired by AAA sci-fi films (*The Expanse*, *Interstellar*, *Arrival*)
- Clean, advanced, purposeful
- Technical precision without mystification

**Information Hierarchy:**
- ~90% purposeful data
- ~10% aesthetic framing
- Clear visual escalation path for severity levels

---

## 2. Color System

### 2.1 Base Colors

**Both Themes:**
- Background: Dark with subtle cyan/teal tint
- Primary Surface: Transparent with backdrop blur
- Text: High contrast white/light gray
- Monospace font for all data

**Light Theme Adaptation:**
- Increase contrast ratios to 5:1 minimum
- Use darker, more saturated accent colors
- Reduce gradient opacity to 3-5%
- Add subtle text shadows for critical metrics

### 2.2 Status Colors

**Healthy/Operational:**
- Color: `#06D6A0` (cyan-green)
- Glow: `rgba(6, 214, 160, 0.4)`
- Label: "OPERATIONAL"
- Use: System running normally

**Degraded/Advisory:**
- Color: `#FFB627` (amber)
- Glow: `rgba(255, 182, 39, 0.3)`
- Label: "ADVISORY" (not "WARNING")
- Use: Predictive issues, needs attention
- Pulse: 2s slow pulse

**Error:**
- Color: `#FF4444` (bright red)
- Glow: `rgba(255, 68, 68, 0.4)`
- Label: "ERROR"
- Use: Actual failures happening now
- Pulse: 1s fast pulse
- Icon pulses rapidly

**Critical (Reserved):**
- Color: Brighter red, more intense
- Use: Catastrophic system-wide failures
- **Not currently used** - maintains escalation headroom

### 2.3 Severity Hierarchy

**Visual Escalation Path:**

| Level | Color | Border Pulse | Icon Animation | Background Intensity | Glow Strength | Use Case |
|-------|-------|--------------|----------------|---------------------|---------------|----------|
| **Advisory** | Amber `#FFB627` | 2s slow | None | 08 opacity | Normal | Predictive warnings |
| **Error** | Red `#FF4444` | 1s fast | 1s pulse | 12 opacity | Strong | Active failures |
| **Critical** | Bright Red | <1s rapid | Rapid pulse | 20 opacity | Very strong | System-wide emergencies |

---

## 3. Typography

### 3.1 Font Family

**Primary:** Monospace (system default or JetBrains Mono)
- All data, labels, and technical content
- Creates technical, command-center aesthetic

**Fallback:** Inter (for long-form descriptions only)

### 3.2 Type Scale

| Style | Size | Weight | Letter Spacing | Transform | Use Case |
|-------|------|--------|----------------|-----------|----------|
| **Status Label** | `0.7rem` (11.2px) | 700 | `0.15em` | UPPERCASE | Section headers |
| **Primary Metric** | `1.8-2rem` (28.8-32px) | 700 | `0.05em` | Normal | Main status display |
| **Secondary Metric** | `1.1-1.2rem` (17.6-19.2px) | 600 | `0.02em` | Normal | Component values |
| **Data Label** | `0.65rem` (10.4px) | Normal | `0.1em` | UPPERCASE | Metric labels |
| **Data Value** | `0.9rem` (14.4px) | 600 | Normal | Normal | Metric values |
| **Caption** | `0.7-0.75rem` (11.2-12px) | Normal | `0.05em` | Normal | Impact statements |
| **Timestamp** | `0.55-0.6rem` (8.8-9.6px) | Normal | `0.05em` | Normal | Last checked, timestamps |

---

## 4. Shape & Composition

### 4.1 Angular Geometry

**Clip Paths (No Rounded Corners):**

```css
/* Large containers */
clip-path: polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px));

/* Medium containers */
clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%);

/* Small containers */
clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px));

/* Buttons */
clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%);

/* Badges */
clip-path: polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%);
```

### 4.2 Corner Brackets

**Decorative Framing (Functional Purpose: Visual Containment):**

```tsx
{/* Corner Brackets */}
<Box sx={{ position: 'absolute', top: 8, left: 8, width: 20, height: 20, borderTop: '2px solid', borderLeft: '2px solid', borderColor: statusColor, opacity: 0.6 }} />
<Box sx={{ position: 'absolute', top: 8, right: 8, width: 20, height: 20, borderTop: '2px solid', borderRight: '2px solid', borderColor: statusColor, opacity: 0.6 }} />
<Box sx={{ position: 'absolute', bottom: 8, left: 8, width: 20, height: 20, borderBottom: '2px solid', borderLeft: '2px solid', borderColor: statusColor, opacity: 0.6 }} />
<Box sx={{ position: 'absolute', bottom: 8, right: 8, width: 20, height: 20, borderBottom: '2px solid', borderRight: '2px solid', borderColor: statusColor, opacity: 0.6 }} />
```

### 4.3 Spacing

- Section gaps: `4` (32px)
- Subsection gaps: `2.5` (20px)
- Component grid gap: `2` (16px)
- Internal padding (large): `3` (24px)
- Internal padding (medium): `2.5` (20px)
- Internal padding (small): `1.5` (12px)

---

## 5. Visual Effects

### 5.1 Scan Lines

**Subtle Horizontal Lines (Functional Purpose: Depth Perception):**

```css
&::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(255,255,255,0.03) 2px,
    rgba(255,255,255,0.03) 4px
  );
  pointer-events: none;
}
```

### 5.2 Radial Glow

**Ambient Background Glow (Functional Purpose: Focal Point):**

```css
/* Fixed background glow */
&::before {
  content: "";
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 50% 0%, rgba(6, 214, 160, 0.03) 0%, transparent 50%);
  pointer-events: none;
  z-index: 0;
}

/* Localized glow on containers */
&::after {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(circle at 50% 50%, rgba(6, 214, 160, 0.05) 0%, transparent 70%);
  pointer-events: none;
}
```

### 5.3 Rotating Grid Overlay

**Holographic Scanning Effect (Functional Purpose: Live Data Indicator):**

```tsx
<g style={{ animation: 'rotate 60s linear infinite', transformOrigin: '60px 60px' }}>
  <line x1="60" y1="6" x2="60" y2="20" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
  <line x1="60" y1="100" x2="60" y2="114" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
  <line x1="6" y1="60" x2="20" y2="60" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
  <line x1="100" y1="60" x2="114" y2="60" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />
</g>

<style>
  @keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
```

### 5.4 Pulsing Borders

**Alert Attention Grabber:**

```css
&::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  background: {statusColor};
  box-shadow: 0 0 10px {statusGlow};
  animation: pulse 2s ease-in-out infinite; /* Slow for advisory */
  /* animation: pulse-fast 1s ease-in-out infinite; */ /* Fast for error */
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes pulse-fast {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
```

---

## 6. Component Patterns

### 6.1 Holographic Central Display

**Purpose:** Primary system status overview

**Structure:**
- Circular health meter with rotating grid overlay
- Status label (OPERATIONAL/DEGRADED/CRITICAL)
- Component count, alert count, uptime
- Live timestamp (updates every second)
- Corner brackets for framing

**Implementation:**
```tsx
<Box sx={{
  position: 'relative',
  p: 3,
  background: 'linear-gradient(135deg, rgba(6, 214, 160, 0.03) 0%, rgba(59, 130, 246, 0.03) 100%)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  clipPath: 'polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px))',
  /* Scan lines overlay */
  /* Corner brackets */
  /* Circular meter with rotating grid */
  /* Status info with monospace typography */
  /* Live timestamp */
}}>
```

### 6.2 Transmission Alert (Issue Notification)

**Purpose:** Actionable problem notification

**Structure:**
- Severity badge (ADVISORY/ERROR)
- Pulsing left border (speed varies by severity)
- Icon with optional pulse animation
- Title with service tag
- Metrics summary (inline, bullet-separated)
- Impact statement
- Action button with shine effect

**Visual Hierarchy:**
- Advisory: Amber, slow pulse, no icon animation
- Error: Red, fast pulse, icon pulses

**Implementation:**
```tsx
<Box sx={{
  position: 'relative',
  p: 2.5,
  background: `linear-gradient(90deg, ${color}08 0%, transparent 100%)`, /* Advisory */
  /* background: `linear-gradient(90deg, ${color}12 0%, transparent 100%)`, */ /* Error */
  border: '1px solid',
  borderColor: statusColor,
  borderLeft: `3px solid ${statusColor}`,
  clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)',
  /* Pulsing border */
  /* Severity badge */
  /* Icon (pulses for errors) */
  /* Metrics: value • trend • Critical in X hours */
  /* Impact statement */
  /* Action button with shine */
}}>
```

### 6.3 Component Status Tile

**Purpose:** Individual service health display

**Structure:**
- Pulsing status dot (top-right)
- Trend indicator arrow (up/down/stable)
- Icon in angular container
- Service name
- Dependency count (if applicable)
- Primary metric value
- Metric label
- Micro sparkline (recent history)
- Last checked timestamp

**Implementation:**
```tsx
<Box sx={{
  position: 'relative',
  p: 1.5,
  background: 'linear-gradient(135deg, rgba(255, 255, 255, 0.02) 0%, rgba(255, 255, 255, 0.01) 100%)',
  border: '1.5px solid rgba(255, 255, 255, 0.1)',
  clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))',
  /* Pulsing status dot */
  /* Trend arrow */
  /* Icon container (angular clip-path) */
  /* Service name + dependency count */
  /* Metric value (large, bold, colored) */
  /* Metric label (small, uppercase) */
  /* Sparkline (60x16px) */
  /* Timestamp (tiny, low opacity) */
}}>
```

---

## 7. Data Visualization

### 7.1 Micro Sparklines

**Purpose:** Show recent trend history

**Specifications:**
- Width: `60px`
- Height: `16px`
- Stroke width: `1.5px`
- Stroke color: Status color
- Opacity: `0.5`
- Data points: 12 recent values

**Implementation:**
```tsx
const MicroSparkline: React.FC<{ data: number[]; color: string }> = ({ data, color }) => {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const width = 60;
  const height = 16;
  
  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * width;
    const y = height - ((value - min) / range) * height;
    return `${x},${y}`;
  }).join(' ');
  
  return (
    <svg width={width} height={height}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.5"
      />
    </svg>
  );
};
```

### 7.2 Arc Progress Indicators

**Purpose:** Show percentage metrics visually

**Specifications:**
- Size: `36px` diameter
- Stroke width: `3px`
- Background circle: `rgba(255,255,255,0.1)`
- Progress circle: Status color
- Stroke linecap: `round`
- Rotation: `-90deg` (start at top)

**Implementation:**
```tsx
const ArcProgress: React.FC<{ percentage: number; color: string; size?: number }> = ({ percentage, color, size = 36 }) => {
  const strokeWidth = 3;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  
  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={strokeWidth} />
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth} strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" />
    </svg>
  );
};
```

### 7.3 Circular Health Meter

**Purpose:** Primary system health visualization

**Specifications:**
- Size: `120px` diameter
- Background circle: `rgba(255,255,255,0.1)`, stroke `2px`
- Progress circle: Status color, stroke `3px`
- Glow effect: `drop-shadow(0 0 8px {statusGlow})`
- Rotating grid overlay (60s rotation)
- Center text: Health percentage + label

---

## 8. Animations

### 8.1 Pulse Animations

**Slow Pulse (Advisory):**
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
animation: pulse 2s ease-in-out infinite;
```

**Fast Pulse (Error):**
```css
@keyframes pulse-fast {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
animation: pulse-fast 1s ease-in-out infinite;
```

**Icon Pulse (Error Only):**
```css
@keyframes pulse-icon-fast {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
animation: pulse-icon-fast 1s ease-in-out infinite;
```

### 8.2 Rotation Animation

**Rotating Grid (Holographic Display):**
```css
@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
animation: rotate 60s linear infinite;
```

### 8.3 Shine Effect

**Button Hover Shine:**
```css
&::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
  transition: left 0.5s;
}

&:hover::before {
  left: 100%;
}
```

### 8.4 Smooth Transitions

**Health Circle:**
```css
transition: stroke-dasharray 1s ease-in-out;
```

**Hover States:**
```css
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
```

**Glow Intensity:**
```css
&:hover {
  box-shadow: 0 0 30px {statusGlow}; /* Error */
  /* box-shadow: 0 0 20px {statusGlow}; */ /* Advisory */
}
```

---

## 9. Purposeful Information Guidelines

### 9.1 Data Requirements

**Every displayed element must answer:**
1. What is the current state?
2. How is it trending?
3. What action should I take?
4. What happens if I don't act?

**Prohibited:**
- Decorative metrics with no decision value
- Duplicate information in different formats
- Visual effects without functional purpose

### 9.2 Predictive Information

**Time-to-Critical Calculations:**
- Based on actual trend rate (e.g., +12%/hour)
- Displayed in context: "Critical in ~1.4 hours"
- Color: Status color (amber for advisory, not red)
- Clearly a prediction, not current state

**Failure Mode Context:**
- Integrated into impact statement
- Not displayed in alarming red
- Example: "Write operations will fail at 95%"

### 9.3 Dependency Information

**Component Dependencies:**
- Show count: "↑ 2 dependents"
- Indicates blast radius of failures
- Helps understand cascading impacts
- Displayed subtly below service name

---

## 10. Light Theme Adaptation

### 10.1 Color Adjustments

**Status Colors (Darker for Light Theme):**
- Healthy: `#059669` (darker than `#06D6A0`)
- Advisory: `#D97706` (darker than `#FFB627`)
- Error: `#DC2626` (darker than `#FF4444`)

**Background:**
- Base: `#F5F6FA` or `#FFFFFF`
- Gradients: 3-5% opacity (half of dark theme)
- Borders: `rgba(0, 0, 0, 0.1)` (not white)

### 10.2 Contrast Requirements

**WCAG AA+ Minimum:**
- Body text: 4.5:1 against background
- Large text: 3:1 against background
- Interactive elements: 3:1 minimum

**Text Adjustments:**
- Increase font weight to 600-700 for colored text
- Add subtle text shadows: `text-shadow: 0 1px 2px rgba(255,255,255,0.8)`
- Use solid backgrounds for badges/chips

### 10.3 Visual Effects

**Reduced Intensity:**
- Backdrop blur: 10-15px (vs 20-30px dark)
- Glow effects: 30% opacity (vs 50% dark)
- Scan lines: `rgba(0,0,0,0.02)` (vs white in dark)

---

## 11. Implementation Checklist

### 11.1 Required Elements

- [ ] Monospace typography for all data
- [ ] Angular clip-paths (no rounded corners)
- [ ] Status-based color coding (cyan/amber/red)
- [ ] Pulsing animations for alerts
- [ ] Micro sparklines for trends
- [ ] Arc indicators for percentages
- [ ] Live timestamps (updating every second)
- [ ] Dependency indicators
- [ ] Predictive time-to-critical
- [ ] Corner brackets on primary containers
- [ ] Scan line overlays
- [ ] Rotating grid on health meter

### 11.2 Accessibility

- [ ] All animations respect `prefers-reduced-motion`
- [ ] Color never the only indicator (icons + labels)
- [ ] Keyboard navigation fully supported
- [ ] Focus states clearly visible
- [ ] Screen reader friendly (ARIA labels)
- [ ] Contrast ratios meet WCAG AA+

### 11.3 Performance

- [ ] Animations use CSS transforms (GPU-accelerated)
- [ ] SVG elements optimized
- [ ] No layout thrashing from live updates
- [ ] Smooth 60fps animations

---

## 12. Extension Guidelines

### 12.1 When to Use This Theme

**Appropriate for:**
- System health and diagnostics
- Real-time monitoring dashboards
- Mission-critical operations interfaces
- Technical troubleshooting tools

**Not appropriate for:**
- General content pages
- User-facing features
- Marketing or onboarding flows
- Casual administrative tasks

### 12.2 Adaptation Principles

When extending to new pages:
1. Maintain the purposeful information philosophy
2. Use monospace typography for data
3. Apply angular geometry consistently
4. Reserve red for actual failures
5. Ensure clear severity escalation
6. Include predictive/contextual information
7. Test in both light and dark themes

---

This theme represents a departure from the standard AICO Studio glassmorphic aesthetic. It should be used selectively for interfaces where technical precision and mission-critical decision-making are paramount.
