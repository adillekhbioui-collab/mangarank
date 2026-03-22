# ManhwaRank — Light Mode Implementation Prompt

> **Skill to invoke:** `@frontend-design`
> **File:** `light_mode_prompt\plan.md`
> **Project:** ManhwaRank — Manhwa & Manhua Discovery App
> **Stack:** React · CSS Variables · localStorage

---

## Project Context

ManhwaRank is a manhwa and manhua discovery and ranking web application.
The UI was recently redesigned around a concept called **"The Archive"** —
an editorial dark theme inspired by prestigious ranking publications.

Design language established in dark mode:
- **Fonts:** Playfair Display (headings/titles) · DM Mono (data/labels) · Inter (body)
- **Layout:** Full-width horizontal strip cards with large rank watermark numbers
- **Accent:** `#C1121F` crimson red — the single brand color, used sparingly
- **Philosophy:** Editorial authority, not manga catalog. Every decision reinforces that ManhwaRank is the definitive ranking source.

The dark mode is complete and deployed. This task adds a **light mode** and a **toggle button** to switch between them.

---

## Design Brief — Light Mode Concept: "The Print Edition"

> If dark mode is *"The Archive at night — a private vault of rankings"*,
> light mode is *"The Archive in print — an editorial magazine laid out on warm paper."*

Reference aesthetic: Criterion Collection print catalog · Monocle magazine · The Paris Review.

**Non-negotiables:**
- Must feel **warm**, not clinical. Off-white and cream, never pure `#FFFFFF`.
- Must feel **inky**, not flat. Near-black text, never pure `#000000`.
- The `--accent-red` stays **identical** to dark mode — it is the brand identity.
- Typography is **unchanged** between themes — fonts are brand, not theme.
- Light mode is a different *expression* of the same publication, not a different app.

---

## CSS Design Tokens — Light Mode

All light mode overrides live inside `[data-theme="light"]`.
Dark mode remains the `:root` default.

```css
:root {
  /* DARK MODE — already exists, do not change */
  --bg-primary:     #0D0B0E;
  --bg-secondary:   #141118;
  --bg-elevated:    #1C1822;
  --accent-red:     #C1121F;
  --accent-gold:    #C9A84C;
  --accent-muted:   #6B4E71;
  --text-primary:   #F0EBF4;
  --text-secondary: #9B8FA8;
  --text-ghost:     #3D3545;
  --border:         #2A2330;
}

[data-theme="light"] {
  /* LIGHT MODE — "The Print Edition" */
  --bg-primary:     #F5F0EB;   /* warm cream, paper-like            */
  --bg-secondary:   #EDE8E1;   /* slightly darker cream for cards   */
  --bg-elevated:    #E4DED5;   /* hover states, active elements     */
  --accent-red:     #C1121F;   /* UNCHANGED — brand identity        */
  --accent-gold:    #A07C20;   /* deeper gold for light background  */
  --accent-muted:   #6B4E71;   /* UNCHANGED                         */
  --text-primary:   #1A1410;   /* warm near-black, ink quality      */
  --text-secondary: #5C5248;   /* warm medium gray                  */
  --text-ghost:     #B8AFA6;   /* watermark rank numbers            */
  --border:         #D4CEC7;   /* warm light gray dividers          */
}
```

---

## Component-by-Component Specifications

### Header

| Element | Light Mode Value |
|---|---|
| Background | `--bg-primary` + 1px `--border` bottom |
| Logo "MANHWA" | `--text-primary` |
| Logo "RANK" | `--accent-red` (unchanged) |
| Active nav tab underline | `--accent-red` 2px |
| Search input underline on focus | `--accent-red` |
| Toggle button | `DM Mono` uppercase, `--text-secondary`, no border |

---

### Category Strip

| Element | Light Mode Value |
|---|---|
| Card background | `--bg-secondary` |
| Card left accent bars | Individual colors unchanged |
| Active card | `--accent-red` background, `--bg-primary` text |
| Hover | `--bg-elevated` background |
| Category name text | `DM Mono` uppercase, `--text-primary` |

---

### Manga Strip Cards

| Element | Light Mode Value |
|---|---|
| Strip background | `--bg-secondary` |
| Strip bottom border | 1px `--border` |
| Rank watermark number | `--text-ghost` |
| Title | `Playfair Display` bold, `--text-primary` |
| Author | `DM Mono`, `--text-secondary` |
| Genres | Uppercase `DM Mono`, `--text-secondary`, separated by · |
| Score 90–100 | `--accent-gold` |
| Score 75–89 | `--text-primary` |
| Score below 75 | `--text-secondary` |
| Hover background | `--bg-elevated` |
| Hover left border | 3px solid `--accent-red` |
| Cover image | Add `box-shadow: 0 1px 4px rgba(26,20,16,0.15)` in light only |

---

### Filter Sidebar

| Element | Light Mode Value |
|---|---|
| Background | `--bg-primary` (no panel — same as page) |
| Right border | 1px `--border` |
| Section labels | `DM Mono` uppercase, `--text-ghost` |
| Status option inactive | `--text-secondary` |
| Status option active | `--accent-red` |
| Genre chip neutral | `--text-secondary`, 1px `--border` border |
| Genre chip included | `--accent-red` text, 1px `--accent-red` border, `rgba(193,18,31,0.06)` bg |
| Genre chip excluded | `--text-ghost` text, 1px dashed `--border`, strikethrough |

---

### Manga Detail Page

| Element | Light Mode Value |
|---|---|
| Completion bar fill | `--accent-red` |
| Completion bar track | `--border` |
| Genre tag chips | `--text-secondary`, 1px `--border`, transparent bg |
| Score high | `--accent-red` |
| Source attribution | `--text-ghost` |
| Synopsis text | `--text-secondary`, Inter, line-height 1.7 |

---

### Skeleton Loading

```css
/* Light mode shimmer */
[data-theme="light"] .skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-secondary) 25%,
    var(--bg-elevated) 50%,
    var(--bg-secondary) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

---

### Pagination

| Element | Light Mode Value |
|---|---|
| Active page | `--text-primary` + 2px `--accent-red` bottom border |
| Inactive pages | `--text-secondary` |
| PREV / NEXT | `DM Mono` uppercase, `--text-secondary` |
| Ellipsis | `--text-ghost` |

---

## Theme Toggle Button

**Placement:** Far right of the header, between search input and edge. On mobile: inside filter drawer header.

**Design philosophy:** Pure CSS and Unicode characters only. No icon libraries. No sun/moon emojis. Consistent with editorial typography identity.

```
Dark mode shows:  ○ LIGHT
Light mode shows: ● DARK
```

```css
.theme-toggle {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-secondary);
  background: none;
  border: none;
  cursor: pointer;
  transition: color 120ms ease;
  padding: 0;
}

.theme-toggle:hover {
  color: var(--text-primary);
}
```

---

## Implementation Instructions

### 1 — CSS Variables Architecture

All color tokens must already be CSS variables from the dark mode implementation.
Add the `[data-theme="light"]` block as a separate override section.
Typography variables (`font-family`, `font-size`, `letter-spacing`) are defined
once in `:root` and **never** overridden between themes.

---

### 2 — Anti-Flash Script (Critical)

Add this inline `<script>` in `<head>` **before** any CSS or JS loads.
This prevents a flash of dark mode before React hydrates:

```html
<head>
  <script>
    (function() {
      const t = localStorage.getItem('manhwarank-theme');
      if (t === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
      }
    })();
  </script>
  <!-- CSS loads after this -->
</head>
```

---

### 3 — useTheme React Hook

Create `src/hooks/useTheme.js`:

```javascript
import { useState, useEffect } from 'react';

const STORAGE_KEY = 'manhwarank-theme';
const THEMES = { DARK: 'dark', LIGHT: 'light' };

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || THEMES.DARK;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === THEMES.LIGHT) {
      root.setAttribute('data-theme', 'light');
    } else {
      root.removeAttribute('data-theme');
    }
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev =>
      prev === THEMES.DARK ? THEMES.LIGHT : THEMES.DARK
    );
  };

  return { theme, toggleTheme, isDark: theme === THEMES.DARK };
}
```

Use this hook in the Header component to drive the toggle button label and click handler.

---

### 4 — Smooth Theme Transition

Add to the root stylesheet. This produces a smooth 200ms color fade when switching themes:

```css
html {
  transition: background-color 200ms ease, color 200ms ease;
}

*,
*::before,
*::after {
  transition:
    background-color 200ms ease,
    border-color 200ms ease,
    color 200ms ease;
}
```

**Exception:** Do not apply this transition to cover images or any element where
a color transition would look unnatural (e.g. SVG icons that should switch instantly).

---

### 5 — Cover Image Light Mode Treatment

In dark mode cover images blend naturally against dark backgrounds.
In light mode add a subtle shadow to prevent harsh edges against cream:

```css
[data-theme="light"] .manga-cover {
  box-shadow: 0 1px 4px rgba(26, 20, 16, 0.15);
}
```

No shadow in dark mode.

---

## Contrast Verification Requirements

Before shipping, verify these contrast ratios meet WCAG AA (4.5:1 minimum):

| Element | Light Mode Colors | Required |
|---|---|---|
| Body text on bg-primary | `#1A1410` on `#F5F0EB` | ≥ 4.5:1 |
| Secondary text on bg-secondary | `#5C5248` on `#EDE8E1` | ≥ 4.5:1 |
| Accent red on bg-primary | `#C1121F` on `#F5F0EB` | ≥ 3:1 |
| Accent gold on bg-secondary | `#A07C20` on `#EDE8E1` | ≥ 3:1 |

If `--accent-gold` fails on `--bg-secondary`, deepen it to `#8B6518` until the ratio passes.

---

## Verification Checklist

After implementation confirm each item manually:

- [ ] Toggle switches dark ↔ light with smooth 200ms color transition
- [ ] No layout shift occurs during theme switch
- [ ] Refreshing in light mode stays in light mode — no flash of dark before React loads
- [ ] Main browse page correct in light mode
- [ ] Manga detail page correct in light mode
- [ ] Charts page correct in light mode
- [ ] Category tabs (Top Action, Romance, etc.) correct in light mode
- [ ] Genre chip grid in filter sidebar correct in light mode
- [ ] Skeleton loading screens use warm cream shimmer in light mode
- [ ] Pagination bar correct in light mode
- [ ] Similar manga section correct in light mode
- [ ] Mobile filter drawer background is `--bg-primary` cream, not white
- [ ] `--accent-red` is visually identical in both themes
- [ ] Toggle button shows `○ LIGHT` in dark mode and `● DARK` in light mode
- [ ] Score gold color is readable against cream background

---

## What Must Not Change

| Element | Reason |
|---|---|
| Typography: Playfair Display, DM Mono, Inter | Part of brand identity |
| Layout: strips, sidebar, header height, category strip | Structure is theme-agnostic |
| All functionality: filters, URL state, pagination, API | No logic changes |
| `--accent-red: #C1121F` | Same in both themes — brand color |
| Editorial design identity | Light is the same publication, different time of day |

---

## Expected Output from Agent

1. Updated root CSS file with `[data-theme="light"]` token block
2. Anti-flash inline script in `index.html` `<head>`
3. `src/hooks/useTheme.js` hook file
4. Updated `Header` component with toggle button using the hook
5. Global transition CSS rule in root stylesheet
6. Light mode cover shadow CSS rule
7. Confirmation that all checklist items pass
