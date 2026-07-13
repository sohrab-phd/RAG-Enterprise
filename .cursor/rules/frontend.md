# Frontend Rules

## Stack and quality gates

- Use React, Vite, TypeScript, Tailwind CSS, and shadcn/ui as selected in ADR-004.
- TypeScript remains strict. Do not introduce `any`, non-null assertions, or
  `@ts-ignore` without a narrow documented justification.
- Required gates: `npm run lint`, `npm run format:check`, `npm run test`, and
  `npm run build`.
- Use `@/` aliases for application imports; avoid deep relative traversal.

## Structure and components

- Organize feature-specific UI, hooks, types, and tests by capability. Put only
  reusable design-system primitives in `src/components/ui`.
- Components render UI and coordinate interactions; move reusable business
  decisions and side effects into typed hooks or services.
- Prefer composition over configuration-heavy components and boolean prop growth.
- Props are explicit readonly interfaces. Do not pass transport DTOs through the
  component tree.
- Keep render functions pure. Never initiate network calls during render.
- Use stable keys from domain IDs, never array indexes for mutable collections.

## State and data access

- Keep state at the narrowest owner. Derive values instead of storing duplicates.
- Distinguish server state, URL/navigation state, form state, and ephemeral UI
  state. Add a global state library only through an ADR.
- All HTTP calls go through a centralized typed client with timeout, cancellation,
  normalized errors, and correlation support.
- Validate untrusted API responses at the boundary when correctness or security
  depends on runtime shape.
- Present explicit loading, empty, error, and success states. Prevent duplicate
  submissions and stale-response races.

## Accessibility and UX

- Use semantic HTML and native controls before ARIA.
- Every interactive element is keyboard operable, has a visible focus state, and
  has an accessible name. Inputs have associated labels and errors.
- Dialogs manage focus and keyboard dismissal; dynamic status uses appropriate live
  regions.
- Meet WCAG 2.2 AA contrast and respect reduced-motion preferences.
- Do not rely on color alone to communicate state.

## Styling

- Use Tailwind utilities and shared design tokens; avoid arbitrary values when a
  token exists.
- Extend shadcn/ui primitives rather than copying or forking them without reason.
- Support light and dark token modes; do not hard-code theme-specific colors.
- Keep layout responsive from the smallest supported viewport upward.
- Avoid inline styles except for truly data-driven values.

## Security and tests

- Never render untrusted HTML. Any exceptional HTML rendering requires sanitization
  and security review.
- Do not store secrets or long-lived credentials in frontend code or browser
  storage.
- Test user-visible behavior with Vitest and Testing Library; query by role/name
  before test IDs and do not assert component internals.
