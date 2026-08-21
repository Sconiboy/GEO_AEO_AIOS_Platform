# ⚙️ Antigravity - Core Development Backlog

## Overview
This file tracks core software architecture, local model integrations, and dashboard development tasks executed by **Antigravity**.

---

## Active Tasks

### Task A-1: Multi-LLM Query Connector (`src/engine/query_engine.py`)
- **Goal**: Implement async Python client connecting to OpenAI (ChatGPT Search API) and Perplexity (Sonar API).
- **Status**: Ready for development.

### Task A-2: Local Hermes 3 Parser Node (`src/engine/hermes_parser.py`)
- **Goal**: Implement local Ollama API bridge to pass raw LLM response text to Nous Hermes 3 for entity & citation extraction.
- **Status**: Pending Task A-1.

---

## Completed Tasks
- [x] Initial repository structure and inter-agent communication protocol setup.
