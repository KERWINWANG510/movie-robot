# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** Movie Robot
**Updated:** 2026-10-09
**Category:** Media Library + File Ops (Hybrid)
**Design Dials:** Variance 5/10 (Balanced / Modern) | Motion 3/10 (Subtle) | Density 6/10 (Standard)

---

## Global Rules

### Color Palette（深色影院风）

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#F59E0B` | `--color-primary` |
| On Primary | `#111113` | `--color-on-primary` |
| Secondary | `#FBBF24` | `--color-secondary` |
| On Secondary | `#111113` | `--color-on-secondary` |
| Accent/CTA | `#FB7185` | `--color-accent` |
| On Accent/CTA | `#111113` | `--color-on-accent` |
| Background | `#0C0C0E` | `--color-background` |
| Foreground | `#F4F4F5` | `--color-foreground` |
| Card | `#18181B` | `--color-card` |
| Card Foreground | `#F4F4F5` | `--color-card-foreground` |
| Muted | `#27272A` | `--color-muted` |
| Muted Foreground | `#A1A1AA` | `--color-muted-foreground` |
| Border | `#3F3F46` | `--color-border` |
| Destructive | `#F87171` | `--color-destructive` |
| On Destructive | `#111113` | `--color-on-destructive` |
| Ring | `#F59E0B` | `--color-ring` |

**Color Notes:** Near-black cinema canvas + amber ticket gold for primary actions; rose accent only for wish/star highlights. UI chrome stays quiet so posters dominate.

### Typography

- **Heading Font:** Plus Jakarta Sans
- **Body Font:** Plus Jakarta Sans
- **Mood:** cinematic, calm, content-first, modern
- **Google Fonts:** [Plus Jakarta Sans](https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 6/10 — Standard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `4px` / `0.25rem` | Tight gaps |
| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |
| `--space-md` | `16px` / `1rem` | Standard padding |
| `--space-lg` | `24px` / `1.5rem` | Section padding |
| `--space-xl` | `32px` / `2rem` | Large gaps |
| `--space-2xl` | `48px` / `3rem` | Section margins |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--mr-shadow-sm` | `0 2px 8px rgba(0,0,0,0.35)` | Subtle lift |
| `--mr-shadow-md` | `0 8px 24px rgba(0,0,0,0.45)` | Cards, hover |
| `--el-box-shadow` | `0 8px 24px rgba(0,0,0,0.45)` | Modals, overlays |

---

## Component Specs

### Buttons

```css
.btn-primary {
  background: #F59E0B;
  color: #111113;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 180ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.94;
}

.btn-secondary {
  background: transparent;
  color: #F59E0B;
  border: 1px solid #3F3F46;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
}
```

### Cards

```css
.card {
  background: #18181B;
  border: 1px solid #3F3F46;
  border-radius: 12px;
  transition: border-color 180ms ease, transform 180ms ease, box-shadow 180ms ease;
}

.card:hover {
  border-color: color-mix(in srgb, #F59E0B 40%, #3F3F46);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #3F3F46;
  border-radius: 8px;
  background: #18181B;
  color: #F4F4F5;
  font-size: 16px;
}

.input:focus {
  border-color: #F59E0B;
  outline: none;
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.18);
}
```

---

## Style Guidelines

**Style:** Dark Cinema + Content-first Minimal

**Keywords:** near-black canvas, amber accent, poster-forward, quiet chrome, subtle motion

**Best For:** Media discovery, watchlists, file ops beside media tools

**Key Effects:** Soft amber hover tints, 150–220ms transitions, poster scale on card hover, respect `prefers-reduced-motion`

### Implementation Notes

- Root: `html.dark` + Element Plus `dark/css-vars.css`
- Primary button text uses `--color-on-primary` (dark ink on amber)
- Wish/star uses `--color-accent` sparingly; do not paint whole chrome with accent
- Avoid mint/teal washes and purple entertainment palettes

---

## Anti-Patterns (Do NOT Use)

- ❌ Teal/mint full-page backgrounds
- ❌ Purple-on-white SaaS gradients
- ❌ Emojis as icons
- ❌ Missing cursor:pointer on clickables
- ❌ Layout-shifting hovers
- ❌ Low contrast text (< 4.5:1 for body)
- ❌ Instant state changes without transition
- ❌ Invisible focus states

---

## Pre-Delivery Checklist

- [ ] Dark canvas tokens applied via `global.css`
- [ ] Element Plus dark css-vars loaded
- [ ] Amber primary + dark on-primary on buttons
- [ ] Media cards remain poster-first
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No horizontal scroll on mobile
