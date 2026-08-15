# 0pening fused design

A night-ops dashboard: SpaceX canvas, Apple Silicon air, Vercel chrome.

**Canvas:** SpaceX night — `#000000` / `#0a0a0a`, hairline `#3a3a3f`.
**Ink:** Apple `#f5f5f7` / `#ffffff`, muted `#888` / `#7a7a7a`.
**Accent:** Vercel link blue `#0070f3` (primary). Success may stay that blue or a quiet white. Error `#ee0000`.
**Type:** Geist Variable for UI. Tight negative tracking on display. Uppercase 11–12px micro labels with SpaceX letter-spacing. Geist Mono for numbers and XP.
**Space:** Apple Silicon — generous padding, lots of air. No cramped gold-editorial look. No Instrument Serif. No warm oklch gold tokens.
**Chrome:** Vercel precision — 6–8px radius, hairline rings, almost no drop shadows. Ghost outlined pills for secondary (SpaceX). Filled black/white primary buttons.
**Motion:** page enter fade+rise 400ms, number count-up, ring fill, hover lift 1–2px. Honor `prefers-reduced-motion`.
**Do not** use the old warm gold primary (`oklch 0.82 0.14 82`).

## Voice
- Product name is **0pening** (leading digit 0). Never “Opening”.
- Marketing brand is AskTheHR.
- Headlines can be sentence-case and period-terminated (Vercel) at SpaceX scale.
- Micro labels are uppercase, tracked out.

## Surfaces
- Page body: `#000000`.
- Cards / insets: `#0a0a0a` with a 1px `#3a3a3f` ring.
- Primary CTA: filled white on black (or filled black on a light island).
- Secondary CTA: ghost outline pill.
- Links, rings, XP fill: `#0070f3`.
