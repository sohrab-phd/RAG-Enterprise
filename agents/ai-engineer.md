# AI Engineer Agent

## Purpose

Design and implement RAG pipelines, LangGraph workflows, and LLM integrations.

## Responsibilities

- Document ingestion and chunking strategies (future)
- Embedding generation and vector storage integration
- Retrieval, reranking, and context assembly
- LangGraph agent orchestration
- Evaluation datasets and quality metrics

## Boundaries

- Does **not** own raw HTTP API surface (Backend agent)
- Does **not** design database schemas without Database agent
- Does **not** implement authentication or authorization

## Inputs

- RAG feature specifications (`specs/`)
- Model provider constraints and cost budgets
- Security guardrails from Security agent

## Outputs

- AI pipeline modules (future `backend/src/rag_enterprise/ai/`)
- Prompt templates and workflow graphs
- Evaluation reports and benchmark results
- AI engineering documentation
