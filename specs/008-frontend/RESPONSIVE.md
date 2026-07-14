# Responsive Behavior

> **Spec:** 008-frontend  
> **Authority:** Layout breakpoints and module adaptations  
> **Policy:** Desktop first · Tablet supported · Mobile optional

## Breakpoints

| Name | Width | Support level |
| --- | --- | --- |
| Desktop | ≥1280px | **Primary** — full three-pane layouts |
| Laptop | 1024–1279px | Full workflows; side panels may narrow |
| Tablet | 768–1023px | Supported — progressive collapse |
| Mobile | <768px | **Optional** — read/lightweight actions only |

## Global shell

| Viewport | Behavior |
| --- | --- |
| Desktop / Laptop | Persistent left sidebar (expandable/collapsible) |
| Tablet | Sidebar collapses to icon rail or drawer |
| Mobile | Bottom or hamburger drawer nav; header compact |

## Knowledge

| Viewport | Layout |
| --- | --- |
| Desktop | Tree \| List \| Inspector (3 panes) |
| Tablet | Tree drawer + List; Inspector as slide-over |
| Mobile | List-only; tap opens full-screen detail; upload via simple file picker |

## Chat

| Viewport | Layout |
| --- | --- |
| Desktop | Conversations \| Thread \| Evidence (3 panes); evidence **always** visible |
| Laptop | Evidence may be a right drawer default-open |
| Tablet | Thread + Evidence tabs; conversations in drawer |
| Mobile (optional) | Thread first; Evidence behind “Evidence” sheet; discourage as primary surface |

**Rule:** On desktop, never hide evidence behind a tooltip-only control.

## Evaluation / Experiments

| Viewport | Layout |
| --- | --- |
| Desktop | Full tables + metric grids |
| Tablet | Horizontal scroll allowed on tables; metric grid → 2 columns |
| Mobile | Stacked metric cards; tables as card lists |

## Settings

| Viewport | Layout |
| --- | --- |
| All | Single column forms/cards; hub as stack on small screens |

## Typography & density

- Desktop: comfortable enterprise density (not consumer-chat spacing).
- Tablet: same type scale; reduce padding ~10–15%.
- Mobile: increase tap targets (min ~44px); accept less density.

## Interactions

| Concern | Desktop | Tablet / Mobile |
| --- | --- | --- |
| Tree expand | Click + keyboard | Tap |
| Tables | Hover row actions | Explicit “…” menu |
| Upload | Drag-drop + browse | Browse only is acceptable |
| Compare experiments | Side-by-side | Stacked A then B |

## What we deliberately skip on mobile

- Experiment configuration heavy forms (redirect CTA: “Use desktop”)
- Three-pane Knowledge editing marathon
- Side-by-side experiment compare

Show a concise banner: “Best experienced on desktop.”

## Testing checklist

- [ ] Desktop 1440px: Chat evidence visible without scrolling horizontally
- [ ] Tablet 768px: Knowledge inspector reachable; Chat evidence via tab/sheet
- [ ] Mobile 390px: Nav works; Chat can send and open evidence sheet
- [ ] No critical action only available via hover
