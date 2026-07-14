# Shared Components

> **Spec:** 008-frontend  
> **Authority:** Reusable UI building blocks for the enterprise console

## Purpose

Define a small, consistent component set. Prefer shadcn/ui primitives + thin domain wrappers. Avoid a large design-system project.

## Design tokens (conceptual)

| Token | Intent |
| --- | --- |
| `--bg`, `--surface`, `--border` | Calm enterprise surfaces |
| `--text`, `--text-muted` | Primary / secondary text |
| `--accent` | Interactive focus (not purple-marketing default; follow app theme tokens) |
| `--success`, `--warning`, `--danger`, `--info` | Status tones |
| `--radius-sm/md` | Modest radius; no pill-heavy chrome |
| `--font-sans`, `--font-mono` | UI + IDs/JSON |

Support light and dark token modes per frontend rules. Do not hard-code theme colors in feature CSS.

## Layout components

| Component | Used by | Notes |
| --- | --- | --- |
| `AppShell` | All | Header + sidebar + outlet |
| `PageHeader` | All modules | Title, description, primary actions |
| `Breadcrumbs` | Nested routes | |
| `TwoPane` / `ThreePane` | Knowledge, Chat | Collapses per RESPONSIVE |
| `EmptyState` | Lists | Title, description, optional CTA |
| `ErrorState` | Lists/panels | Message + Retry |
| `Skeleton` | All | Table/card placeholders |

## Data display

| Component | Notes |
| --- | --- |
| `DataTable` | Sort optional in v1; pagination required for lists |
| `StatusChip` | Text label + tone; never color-only |
| `MetricStat` | Label, value, optional hint; used by Evaluation/Experiments |
| `KeyValueList` | Settings / config snapshots |
| `CodeBlockReadonly` | Prompts, JSON config |

## Domain components

| Component | Module | Notes |
| --- | --- | --- |
| `FolderTree` | Knowledge | Expand/collapse; keyboard arrows |
| `DocumentInspector` | Knowledge | Metadata summary |
| `ProcessingStatusBadge` | Knowledge | Maps `processing_status` enum |
| `UploadDropzone` | Knowledge | |
| `MessageThread` | Chat | User / assistant / system-status |
| `PromptComposer` | Chat | KB-gated send |
| `EvidencePanel` | Chat | Citations + chunks + latency |
| `CitationCard` | Chat | Marker, score, excerpt |
| `ChunkRow` | Chat | Similarity bar + text |
| `ExperimentConfigForm` | Experiments | |
| `ResultsTable` | Experiments | Per-question outcomes |
| `MetricDiffTable` | Experiments | Compare |

## Feedback

| Component | Notes |
| --- | --- |
| `Toast` | Success/failure acknowledgements |
| `ConfirmDialog` | Destructive or start-run confirmations |
| `InlineAlert` | Abstention, warnings, adapter-pending |
| `LiveRegion` | Polite status for processing poll / chat pending |

## Form primitives

Reuse shadcn: `Button`, `Input`, `Select`, `Textarea`, `Dialog`, `Drawer`, `Tabs`, `Tooltip`, `Checkbox`, `Label`.

Domain forms wrap these with explicit typed props—**do not pass raw API DTOs** through the tree.

## Accessibility baseline

| Rule | Requirement |
| --- | --- |
| Focus | Visible focus ring on all interactive controls |
| Keyboard | Trees, tables, dialogs operable without mouse |
| Names | Buttons/icon-only controls have accessible names |
| Status | Not color-only; include text |
| Motion | Honor `prefers-reduced-motion` |

## State pattern (all feature screens)

Every data-bound view implements:

1. **Loading** — skeleton or spinner in context  
2. **Empty** — explanation + CTA when useful  
3. **Error** — message + retry  
4. **Success** — content  

Prevent duplicate submissions on mutating actions.

## Non-goals

- Custom chart kit
- Animation-heavy marketing components
- Parallel component library outside `src/components`
