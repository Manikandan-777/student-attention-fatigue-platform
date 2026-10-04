# UI Design System — Attention & Fatigue Monitoring Frontends

> **Doc ID:** `UI` · **Applies to:** Operator Console (web, phases 17–20) and Mobile App (phases 21–23).
> **Depends on:** `README.md` (D3, D4, D6, D8) · **Status names/enums:** `contracts.md` §1 · **Screens:** `application_behavior.md` · **Build order:** `implementation.md`
> **Origin:** tokens were extracted from the TailAdmin demo (https://demo.tailadmin.com/, an eCommerce dashboard). **Only the tokens and rules are reused; none of its eCommerce content** (orders, products, sales) is part of this product. Sections are referenced as `UI-n`.

---

## UI-1 Overview

**Surface type:** data-dense monitoring dashboard (web) and a simplified companion app (mobile).
**Audience:** teachers and admins.
**Character:** calm, data-forward, sentence-case, labels over sentences.

### Design principles
- **Data visibility** — the most important metric (students attentive / distracted / fatigued, open alerts) is visible without interaction.
- **Progressive disclosure** — summaries first, detail on demand (student → details → report).
- **Efficiency over decoration** — every pixel communicates state or enables action; no decorative shadows on data-dense layouts.
- **Honest status** — show `Unknown`/offline explicitly; never hide critical status behind interaction (APP-21).
- **Indicators, not verdicts** — copy says "indicator" / "possible" (D8).

## UI-2 Design Tokens (single source — no raw values in components)

Implement once as `tokens.ts` (+ Tailwind theme extension for web, `theme.ts` for mobile). Components reference **token names only**.

### Colors

| Token | Value | Semantic name | Role |
|-------|-------|---------------|------|
| color-12 | `#FFFFFF` | `bg.surface` | Card/page background |
| color-10 | `#ECF3FF` | `bg.info` | Tinted background (blue) |
| color-11 | `#ECFDF3` | `bg.success` | Tinted background (green) |
| color-1 | `#101828` | `text.primary` | Headings, key numbers |
| color-2 | `#344054` | `text.body` | Body text |
| color-3 | `#667085` | `text.secondary` | Secondary text |
| color-7 | `#98A2B3` | `text.muted` | Captions, disabled text |
| color-4 | `#465FFF` | `accent.primary` | Primary actions, links, focus ring |
| color-5 | `#D92D20` | `accent.danger` | Errors, danger |
| color-6 | `#039855` | `accent.success` | Success |
| color-8 | `#D0D5DD` | `border.strong` | Input borders |
| color-9 | `#E4E7EC` | `border.subtle` | Dividers, card borders |

### Typography
**Font stack:** `Outfit, -apple-system, system-ui, sans-serif` (always include the fallback). **Weights:** 400 · 500 · 600 · 700.

| Level | Size | Usage |
|-------|------|-------|
| text-xs | 11px | Captions, metadata |
| text-sm | 13px | Labels, secondary text |
| text-base | 16px | Body (default) |
| text-lg | 18px | Subheadings, emphasis |
| text-xl | 30px | Section headings / big numbers |

Line heights in use: 16, 18, 20, 24, 28, 38 px (pair with the size; don't invent others).

### Spacing (base unit 4px)
`space-1: 2` · `space-2: 4` · `space-3: 5` · `space-4: 6` · `space-5: 7` · `space-6: 8` · `space-7: 10` · `space-8: 12` · `space-9: 16` · `space-10: 24` · `space-11: 44` · `space-12: 48` · `space-13: 56` (px). Prefer the 4/8/12/16/24 steps; use 5/6/7/10 only for tight inline gaps. Mobile: same numbers as dp.

### Radius
| Token | Value | Use |
|-------|-------|-----|
| radius-md | 4px | small controls, chips |
| radius-lg | 6px | inputs, buttons |
| radius-xl | 8px | cards, panels |
| radius-full | 16px | large rounded containers |
| radius-pill | `9999px` | badges, status dots (the source value `2.68435e+07px` is a "fully round" artifact; use `9999px`) |

Do not mix radii outside this set.

### Elevation
`shadow-sm` = `0 1px 2px 0 rgba(16,24,40,0.05)` (cards only). `shadow-none` everywhere else. No decorative shadows on data-dense layouts.

### Motion
`transition: color, background-color, border-color, fill, stroke 150ms cubic-bezier(0.4,0,0.2,1)`. Respect `prefers-reduced-motion` (disable transitions and chart animation).

## UI-3 Status Color Mapping (domain-specific; uses only existing tokens)

Status must **never rely on color alone**: always pair color with an icon and a text label (accessibility + color-blind safety).

| Status (contracts §1) | Text/icon | Background | Border | Icon |
|-----------------------|-----------|------------|--------|------|
| `Attentive` | `accent.success` (color-6) | `bg.success` (color-11) | `accent.success` | check-circle |
| `Distracted` | `accent.primary` (color-4) | `bg.info` (color-10) | `accent.primary` | eye-off / arrow-left-right |
| `Fatigued` | `accent.danger` (color-5) | `bg.surface` (color-12) | `accent.danger` | alert-triangle |
| `Unknown` / no face | `text.muted` (color-7) → use `text.secondary` for contrast | `bg.surface` | `border.subtle` | help-circle |
| Service `Online` | `accent.success` | — | — | dot + "Online" |
| Service `Offline` | `accent.danger` | — | — | dot + "Offline" |

Canvas bounding boxes use the same mapping via `tokens.ts` constants (no literal hex in drawing code).
**Gap / open decision:** the palette has no amber/warning color and no red tint background. Do not add colors without approval; if the project owner approves, add tokens to `UI-2` first, then use them.

## UI-4 Component Inventory (what to build and where it is used)

| Component | Purpose | Screens / phases |
|-----------|---------|------------------|
| `StatCard` | One big metric + label (Students, Attentive, Distracted, Fatigued, Open alerts) | Dashboards — 18, 19, 22, 23 |
| `StatusBadge` | Status per UI-3 | everywhere |
| `StudentRow` / `StudentCard` | `S003`, statuses, confidence | Student lists — 18, 22 |
| `LiveGrid` + `FaceTile` | Annotated video grid or privacy-mode tile grid | Operator Console — 18 |
| `AttentionTrendChart`, `FatigueTimelineChart`, `DistributionChart` | Recharts/Victory views | 19, 22 |
| `AlertFeed` / `AlertItem` | Reverse-chronological alerts with status actions | 20, 22 |
| `SessionReportCard`, `ReportList` | Session summary and history | 16 (export UI), 22 |
| `SystemStatusPanel` | AI server / DB / API / camera states | 23 (and admin web) |
| `ConnectionBanner` | Offline / AI down / camera offline messages | 21–23 |
| `DataTable`, `FormField`, `Button`, `Dialog`, `Tabs` | shadcn/ui primitives themed with tokens | admin CRUD — 17, 23 |

## UI-5 Component Requirements (every component)

1. Uses **tokens only** — no hex, px or font literals outside `tokens.ts`.
2. Defines states: default, hover, focus-visible, active, disabled, loading, error, **empty**.
3. Specifies behavior at the smallest (mobile ~360 px) and largest (desktop ≥ 1440 px) breakpoint.
4. Handles edge cases: no students, 100+ tracks, long names, truncation with tooltip, stale data, `Unknown`.
5. Keyboard: Tab order, Enter/Space to activate, Escape to close dialogs, arrow keys in tabs/lists/menus.
6. ARIA: roles/labels; live regions (`aria-live="polite"`) for alert feed and connection banner; charts have a text summary or data table alternative.
7. Contrast: body text ≥ 4.5:1, large text/UI components ≥ 3:1, focus ring (`accent.primary`, 2 px, offset 2 px) visible at ≥ 3:1.
8. Touch targets ≥ 44×44 px on mobile.

## UI-6 Authoring Workflow & Required Output for New Component Guidelines

When writing a guideline for a component, follow: (1) state intent in one sentence → (2) map tokens → (3) define anatomy → (4) specify states → (5) describe interactions (keyboard, pointer, touch; overflow/truncation) → (6) accessibility pass/fail checks → (7) anti-patterns → (8) QA checklist.

Required sections, in order: **Overview** · **Tokens and foundations** · **Anatomy and variants** · **States and interactions** · **Accessibility** · **Content guidelines** · **Anti-patterns**.

### Content guidelines
- Sentence case; ALL CAPS only for acronyms (EAR, PERCLOS, CSV, PDF).
- Labels over sentences: "Attentive", "Open alerts", "Session duration".
- Alert copy: informational, e.g. "Repeated fatigue indicators" — never "sleeping", "sick", "lazy", "misbehaving" (D8).
- Always show units and timestamps in the user's locale (24 h or 12 h consistently).

### Anti-patterns
- Introducing colors outside UI-2, or mixing radii/arbitrary spacing.
- Conveying status by color only.
- Decorative shadows/gradients on data-dense screens.
- Showing raw AI internals (attention weights, probabilities, embeddings) to teachers (APP-9).
- Showing face imagery or video on mobile (D4).
- Hiding the AI/camera offline state inside a menu.
- Shipping a component without hover, focus-visible and disabled states.

## UI-7 Platform Mapping

**Web (Operator Console):** extend `tailwind.config` `theme.extend.colors/fontSize/spacing/borderRadius` from `tokens.ts`; font loaded with `font-display: swap`; shadcn/ui components themed through CSS variables that point at these tokens; add a CI lint that fails on hex/`px` literals outside the token file.

**Mobile (Expo):** `theme.ts` exports the same tokens (px → dp); use the system font if Outfit is not bundled via `expo-font`; bottom-tab navigation per APP-22; a minimum of 44 dp touch targets; status uses icon + text.

**Responsive layout (web):** ≤ 640 px single column; 641–1024 px two columns; ≥ 1025 px sidebar + 12-col grid; live grid columns adapt to track count.

## UI-8 Definition of Done (component)

- [ ] Renders correctly in default state (smoke test).
- [ ] All states documented and visually verified: hover, focus-visible, active, disabled, loading, error, empty.
- [ ] Zero hardcoded visual values (token lint passes).
- [ ] Keyboard navigation works without a pointer.
- [ ] No critical accessibility violations (contrast, ARIA, focus order) — automated check (axe/jest-axe) plus manual pass.
- [ ] Tested at smallest and largest breakpoint.
- [ ] Anti-patterns section lists at least one concrete misuse.
- [ ] Docs cover purpose, props/API, limitations.
- [ ] Status displays match `contracts.md` §1 enum names exactly.
