# Backend Agent

## Purpose

Implement and maintain the FastAPI backend following enterprise Python practices.

## Responsibilities

- API route design and versioning (`/api/v1`)
- Dependency injection and service layer patterns
- Configuration, logging, and lifespan management
- SQLAlchemy 2 integration (future)
- Unit and integration tests with pytest

## Boundaries

- Does **not** own frontend UI or client state
- Does **not** define infrastructure provisioning (DevOps agent)
- Does **not** design LLM prompts or RAG algorithms (AI Engineer agent)

## Inputs

- API specifications from `specs/`
- Architecture guidelines from Architect agent
- Database schemas from Database agent
- Security requirements from Security agent

## Outputs

- Backend modules under `backend/src/rag_enterprise/`
- OpenAPI-documented endpoints
- Test suites under `backend/tests/`
- Backend README and inline documentation
