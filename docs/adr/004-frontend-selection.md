# ADR-004: Frontend Selection

**Status:** Accepted  
**Date:** 2026-07-13

## Context

RAG-enterprise needs a maintainable, accessible web application with strong static
typing, rapid local feedback, testable components, and a consistent design system.
The current scope is a client-rendered application skeleton; server-side rendering,
public content discovery, and edge rendering are not established requirements.

## Decision

Use React, Vite, and strict TypeScript for the frontend. Use Tailwind CSS for
token-based styling and shadcn/ui/Radix primitives for accessible component
foundations. Use ESLint and Prettier for static quality and formatting, and Vitest
with Testing Library for behavioral tests.

- Organize code by feature capability with reusable primitives in `components/ui`.
- Use functional components, semantic HTML, and WCAG 2.2 AA as the accessibility
  target.
- Centralize typed API transport and normalized errors.
- Keep state local by default and introduce routing, server-state, form, or global
  state libraries only when a specification establishes the requirement.
- Use design tokens and preserve light/dark theme compatibility.

## Alternatives considered

### Next.js

Provides routing, server rendering, and full-stack conventions, but adds server/runtime
complexity before SSR, SEO, or React Server Components are required. It may be
reconsidered if those become product needs.

### Vue or Svelte

Both provide productive typed UI ecosystems, but React has broad enterprise adoption,
component ecosystem maturity, and alignment with shadcn/ui and current team assumptions.

### A fully packaged component framework

Could accelerate standard screens, but creates stronger visual and runtime coupling.
shadcn/ui provides accessible source-level primitives that can be governed by the
project design tokens.

## Consequences

- Frontend builds are fast and local development remains simple.
- The project owns routing and data-state selections until requirements justify them.
- shadcn/ui components become maintained application source and must be reviewed,
  tested, and updated deliberately.
- Client rendering does not provide SSR/SEO benefits; adopting them later may require
  framework migration and a new ADR.
- Accessibility remains an engineering responsibility despite accessible primitives.
