# AICO Studio – Current Theme Specification

> **Version:** 1.0  
> **Last Updated:** January 2026  
> **Scope:** Complete visual styling specification for the current AICO Studio glassmorphic theme

This document provides exact color values, gradients, spacing, typography, and implementation patterns for the current AICO Studio theme. Use this as the single source of truth for maintaining visual consistency.

---

## 1. Color System

### 1.1 Base Colors

**Light Theme:**
- Background: `#F5F6FA`
- Primary Surface: `#FFFFFF`
- Elevated Surface: `#ECEDF1`
- Primary Text: `#1F2937`
- Secondary Text: `#6B7280`
- Border: `rgba(0, 0, 0, 0.1)`

**Dark Theme:**
- Background: `#181A21`
- Primary Surface: `#21242E`
- Elevated Surface: `#2F3241`
- Primary Text: `#F9FAFB`
- Secondary Text: `#9CA3AF`
- Border: `rgba(255, 255, 255, 0.1)`

### 1.2 Domain Colors

Each navigation domain has dedicated colors for visual hierarchy:

| Domain | Light Theme | Dark Theme | Gradient Light | Gradient Dark |
|--------|-------------|------------|----------------|---------------|
| **Overview** | `#6B7280` | `#9CA3AF` | `rgba(107, 114, 128, 0.03)` | `rgba(156, 163, 175, 0.15)` |
| **Operations** | `#2563EB` | `#3B82F6` | `rgba(37, 99, 235, 0.03)` | `rgba(59, 130, 246, 0.15)` |
| **Emotion** | `#DB2777` | `#EC4899` | `rgba(219, 39, 119, 0.03)` | `rgba(236, 72, 153, 0.15)` |
| **Memory & AMS** | `#7C3AED` | `#8B5CF6` | `rgba(124, 58, 237, 0.03)` | `rgba(139, 92, 246, 0.15)` |
| **Agency** | `#FF6B6B` | `#FF8787` | `rgba(255, 107, 107, 0.03)` | `rgba(255, 135, 135, 0.15)` |
| **System** | `#0891B2` | `#06B6D4` | `rgba(8, 145, 178, 0.03)` | `rgba(6, 182, 212, 0.15)` |

### 1.3 Semantic Colors

**Success/Healthy:**
- Light: `#059669`
- Dark: `#10B981`

**Warning/Degraded:**
- Light: `#D97706`
- Dark: `#F59E0B`

**Error/Critical:**
- Light: `#DC2626`
- Dark: `#EF4444`

**Info/Neutral:**
- Light: `#6B7280`
- Dark: `#9CA3AF`

### 1.4 Accent Colors

**Primary Accent (Lavender):**
- Light: `#B8A1EA`
- Dark: `#B8A1EA`
- Used for: Studio actions, selection, focus states

**Destructive (Coral):**
- Light: `#ED7867`
- Dark: `#ED7867`
- Used for: Delete, remove, destructive actions

---

## 2. Gradients

### 2.1 Domain Card Gradients

**Light Theme Pattern:**
```css
background: radial-gradient(circle at top right, {domain-color-light-gradient} 0%, transparent 70%),
            linear-gradient(135deg, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0.01) 100%),
            #FFFFFF;
```

**Dark Theme Pattern:**
```css
background: radial-gradient(circle at top right, {domain-color-dark-gradient} 0%, transparent 70%),
            linear-gradient(135deg, {domain-color-dark-gradient} 0%, rgba(59, 130, 246, 0.05) 100%),
            rgba(255, 255, 255, 0.02);
```

### 2.2 Hero Section Gradients (Knowledge Graph Pattern)

**Advanced Layering for High-Impact Panels:**

```css
/* Light Theme */
background: radial-gradient(circle at top right, rgba(139, 92, 246, 0.05) 0%, transparent 70%),
            linear-gradient(135deg, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0.01) 100%);

/* Dark Theme */
background: radial-gradient(circle at top right, rgba(139, 92, 246, 0.20) 0%, transparent 70%),
            linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%);
```

**Gradient Accent Colors:**
- Purple: `rgba(139, 92, 246, 0.1)` (10% opacity)
- Blue: `rgba(59, 130, 246, 0.05)` (5% opacity)
- Success: `rgba(16, 185, 129, 0.1)` (10% opacity)
- Warning: `rgba(245, 158, 11, 0.1)` (10% opacity)
- Error: `rgba(239, 68, 68, 0.1)` (10% opacity)

---

## 3. Shape & Spacing

### 3.1 Border Radius Scale

- **XLarge**: `36px` - Studio shell containers, main cards, modals, drawers
- **Large**: `28px` - Metric cards, overview cards
- **Medium**: `20px` - Buttons, small panels
- **Small**: `12px` - Tags, chips, pills

### 3.2 Spacing Scale

**Viewport Padding:**
- Desktop: `24-40px` from edges
- Tablet: `16-24px` from edges
- Mobile: `12-16px` from edges

**Card Spacing:**
- Between cards: `16-24px`
- Between sections: `32-48px`
- Internal padding (large cards): `24-32px`
- Internal padding (small cards): `16-20px`

### 3.3 Glassmorphism

**Primary Cards (Studio Home, Dashboards):**
- Backdrop blur: `20-30px`
- Border: `1.5px solid rgba(255, 255, 255, 0.1)` (dark) / `rgba(0, 0, 0, 0.1)` (light)
- Border opacity: `10-30%`

**Secondary Cards (Tables, Forms):**
- Backdrop blur: `10-15px`
- Border: `1px solid rgba(255, 255, 255, 0.08)` (dark) / `rgba(0, 0, 0, 0.08)` (light)
- Higher contrast for text legibility

**Context Panel:**
- Backdrop blur: `30px`
- Border: `1.5px solid rgba(255, 255, 255, 0.1)` (dark) / `rgba(0, 0, 0, 0.1)` (light)
- Same radius as primary cards (36px)

---

## 4. Typography

### 4.1 Font Family

- **Primary**: Inter
- **Monospace**: JetBrains Mono (for code, data, technical content)

### 4.2 Type Scale

| Style | Size | Weight | Line Height | Use Case |
|-------|------|--------|-------------|----------|
| **H1** | `2.5rem` (40px) | 800 | 1.2 | Page titles (rare) |
| **H2** | `2rem` (32px) | 700 | 1.3 | Domain titles |
| **H3** | `1.5rem` (24px) | 700 | 1.4 | Section headers |
| **H4** | `1.25rem` (20px) | 600 | 1.4 | Subsection headers |
| **H5** | `1.125rem` (18px) | 600 | 1.5 | Card titles |
| **H6** | `1rem` (16px) | 600 | 1.5 | Small headers |
| **Body** | `1rem` (16px) | 400 | 1.6 | Default text |
| **Body Small** | `0.875rem` (14px) | 400 | 1.5 | Secondary text |
| **Caption** | `0.75rem` (12px) | 400 | 1.4 | Labels, metadata |
| **Overline** | `0.75rem` (12px) | 700 | 1.4 | Section labels (uppercase) |

### 4.3 Font Weights

- **Regular**: 400
- **Medium**: 500
- **Semibold**: 600
- **Bold**: 700
- **Extrabold**: 800

---

## 5. Shadows

### 5.1 Elevation System

**Light Theme:**
```css
/* Level 1 - Cards */
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.08);

/* Level 2 - Elevated Cards */
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);

/* Level 3 - Modals, Drawers */
box-shadow: 0 10px 15px rgba(0, 0, 0, 0.1), 0 4px 6px rgba(0, 0, 0, 0.05);

/* Level 4 - Overlays */
box-shadow: 0 20px 25px rgba(0, 0, 0, 0.15), 0 10px 10px rgba(0, 0, 0, 0.04);
```

**Dark Theme:**
```css
/* Level 1 - Cards */
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3), 0 1px 2px rgba(0, 0, 0, 0.2);

/* Level 2 - Elevated Cards */
box-shadow: 0 4px 6px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.3);

/* Level 3 - Modals, Drawers */
box-shadow: 0 10px 15px rgba(0, 0, 0, 0.5), 0 4px 6px rgba(0, 0, 0, 0.4);

/* Level 4 - Overlays */
box-shadow: 0 20px 25px rgba(0, 0, 0, 0.6), 0 10px 10px rgba(0, 0, 0, 0.5);
```

### 5.2 Glow Effects

**Data Visualization:**
```css
/* Progress circles */
filter: drop-shadow(0 0 8px rgba({color}, 0.5));

/* Status dots */
box-shadow: 0 0 8px rgba({color}, 0.5);
```

---

## 6. Animations & Transitions

### 6.1 Timing Functions

- **Standard**: `cubic-bezier(0.4, 0, 0.2, 1)` - Default transitions
- **Decelerate**: `cubic-bezier(0, 0, 0.2, 1)` - Enter animations
- **Accelerate**: `cubic-bezier(0.4, 0, 1, 1)` - Exit animations
- **Sharp**: `cubic-bezier(0.4, 0, 0.6, 1)` - Attention-grabbing

### 6.2 Duration Scale

- **Instant**: `100ms` - Hover states, focus rings
- **Fast**: `200ms` - Button clicks, checkbox toggles
- **Normal**: `300ms` - Card expansions, drawer slides
- **Slow**: `500ms` - Page transitions, modal fades
- **Very Slow**: `1000ms+` - Data visualizations, progress animations

### 6.3 Common Transitions

```css
/* Hover states */
transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);

/* Card expansion */
transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1),
            box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);

/* Progress animations */
transition: stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1);
```

---

## 7. Interactive States

### 7.1 Buttons

**Primary Button (Lavender):**
```css
/* Light Theme */
background: #B8A1EA;
color: #FFFFFF;
border: none;
box-shadow: 0 2px 4px rgba(184, 161, 234, 0.3);

&:hover {
  background: #A88FDB;
  box-shadow: 0 4px 8px rgba(184, 161, 234, 0.4);
}

/* Dark Theme */
background: #B8A1EA;
color: #1F2937;
border: none;
box-shadow: 0 2px 4px rgba(184, 161, 234, 0.4);

&:hover {
  background: #C9B3F0;
  box-shadow: 0 4px 8px rgba(184, 161, 234, 0.5);
}
```

**Destructive Button (Coral):**
```css
background: #ED7867;
color: #FFFFFF;

&:hover {
  background: #E55F4D;
}
```

### 7.2 Focus States

```css
/* Keyboard focus ring */
outline: 2px solid #B8A1EA;
outline-offset: 2px;
```

### 7.3 Hover States

```css
/* Cards */
&:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
}

/* Links */
&:hover {
  color: #B8A1EA;
  text-decoration: underline;
}
```

---

## 8. Implementation Examples

### 8.1 Domain Card (Operations - Blue)

```tsx
<Box
  sx={{
    p: 3,
    borderRadius: '28px',
    background: (theme) => theme.palette.mode === 'light'
      ? 'radial-gradient(circle at top right, rgba(37, 99, 235, 0.03) 0%, transparent 70%), linear-gradient(135deg, rgba(0,0,0,0.02) 0%, rgba(0,0,0,0.01) 100%), #FFFFFF'
      : 'radial-gradient(circle at top right, rgba(59, 130, 246, 0.15) 0%, transparent 70%), linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(16, 185, 129, 0.05) 100%), rgba(255, 255, 255, 0.02)',
    border: '1.5px solid',
    borderColor: (theme) => theme.palette.mode === 'light' ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)',
    backdropFilter: 'blur(20px)',
    boxShadow: (theme) => theme.palette.mode === 'light'
      ? '0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06)'
      : '0 4px 6px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.3)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    '&:hover': {
      transform: 'translateY(-2px)',
      boxShadow: (theme) => theme.palette.mode === 'light'
        ? '0 8px 16px rgba(0, 0, 0, 0.15)'
        : '0 8px 16px rgba(0, 0, 0, 0.5)',
    },
  }}
>
  {/* Card content */}
</Box>
```

### 8.2 Status Badge

```tsx
<Chip
  label="Healthy"
  size="small"
  sx={{
    bgcolor: (theme) => theme.palette.mode === 'light' ? '#059669' : '#10B981',
    color: '#FFFFFF',
    fontWeight: 600,
    fontSize: '0.75rem',
    borderRadius: '12px',
  }}
/>
```

---

## 9. Light Theme Readability Guidelines

### 9.1 Contrast Requirements

**WCAG AA+ Minimum:**
- Body text: 4.5:1 minimum
- Large text (≥18pt): 3:1 minimum
- Interactive elements: 3:1 minimum

### 9.2 Text Color Adjustments

Use **darker, saturated versions** of accent colors on light backgrounds:
- Purple: `#7C3AED` (not `#8B5CF6`)
- Blue: `#2563EB` (not `#3B82F6`)
- Green: `#059669` (not `#10B981`)
- Amber: `#D97706` (not `#F59E0B`)
- Red: `#DC2626` (not `#EF4444`)

### 9.3 Gradient Opacity

**Light theme gradients must be more subtle:**
- Reduce opacity to 3-5% (half of dark theme)
- Use neutral gray gradients for data-heavy sections
- Increase font weight (600-700) for colored text on gradients

---

## 10. Accessibility Checklist

- [ ] All color combinations meet WCAG AA+ contrast (4.5:1 minimum)
- [ ] Color is never the only indicator (always paired with icons/labels)
- [ ] Focus states are clearly visible (2px outline, 2px offset)
- [ ] Interactive elements have 48px minimum tap targets on mobile
- [ ] Animations respect `prefers-reduced-motion`
- [ ] Text remains readable at 200% zoom
- [ ] All icons have meaningful alt text or ARIA labels

---

This theme specification ensures visual consistency across all AICO Studio components. When implementing new features, always reference these exact values rather than approximating.
