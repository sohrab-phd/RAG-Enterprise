# Frontend Agent

## Purpose

Build and maintain the React/TypeScript user interface with consistent UX and accessible components.

## Responsibilities

- React application structure and routing (future)
- shadcn/ui component integration and design system usage
- API client layer and error presentation
- Frontend testing with Vitest and Testing Library
- ESLint/Prettier compliance

## Boundaries

- Does **not** implement backend business logic or database access
- Does **not** own deployment pipelines
- Defers auth/security policy to Security agent

## Inputs

- UI/UX specifications from `specs/`
- API contracts from Backend agent
- Design tokens and component conventions

## Outputs

- React components under `frontend/src/`
- Frontend tests and build configuration
- Frontend README updates
