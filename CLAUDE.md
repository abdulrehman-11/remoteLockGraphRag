# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RemoteLock AI Assistant is a full-stack AI-powered customer support chatbot for RemoteLock documentation. The system uses a knowledge graph built with Neo4j, hybrid search (Cypher + vector embeddings), and LangGraph for agentic workflows.

**Tech Stack:**
- Backend: FastAPI (Python), Neo4j graph database, LangChain/LangGraph, Google Gemini LLM
- Frontend: React + Vite
- Deployment: Render (backend), separate frontend hosting
- Vector Store: Pinecone (for semantic search)
- Embeddings: SentenceTransformers

## Architecture

### Backend Structure (`/backend/app/`)

**Core Application Files:**
- `main.py` - FastAPI application with LangGraph agent implementation. Defines the conversational flow, tool calling, and the `/chat/` endpoint
- `query_with_llm_json.py` - `ProductionRetriever` class implementing hybrid search (Cypher graph queries + vector similarity)
- `scraper_json.py` - Playwright-based web scraper for RemoteLock documentation pages
- `embedding_generator_json.py` - Generates embeddings using SentenceTransformers for vector search
- `load_into_neo4j_json.py` - Loads scraped content into Neo4j graph database with hierarchical relationships
- `remotelock_knowledge_graph_builder_online.py` - Orchestrates the complete pipeline: scrape → embed → load into Neo4j
- `search_api.py` - Alternative/legacy search interface (if present)

**Data Flow:**
1. Documentation is scraped from RemoteLock support site using Playwright
2. Content is embedded using sentence-transformers model
3. Data is loaded into Neo4j with relationships: Category → Subcategory → Page → Content chunks
4. User queries trigger hybrid search: Cypher queries for structured data + vector search for semantic similarity
5. LangGraph agent orchestrates tool calling and response generation using Gemini

**Key Classes:**
- `ProductionRetriever` (query_with_llm_json.py) - Handles all retrieval logic
- `GraphState` (main.py) - LangGraph state containing messages and sitemap context
- Tool: `retrieve_documentation` - LangChain tool that wraps the retriever

### Frontend Structure (`/frontend/remotelock-assistant-frontend/`)

React application built with Vite:
- `App.jsx` - Main layout with search section, assistance options, and embedded chatbot
- `Chatbot.jsx` - Chat interface component that communicates with backend `/chat/` endpoint
- Uses Axios for API calls to the FastAPI backend

### Configuration Files

**Backend:**
- `requirements.txt` - Python dependencies (note: uses specific pinned versions for stability)
- `Procfile` - Render deployment config: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- `.env` - Required environment variables (see Environment Variables section)

**Frontend:**
- `package.json` - Node dependencies, includes Vite build scripts

**Deployment:**
- `render.yaml` - Render.com service configuration for backend deployment

## Common Development Commands

### Backend

**Start development server:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

**Run knowledge graph builder (full pipeline):**
```bash
cd backend
python -m app.remotelock_knowledge_graph_builder_online
```

**Test retrieval directly:**
```bash
cd backend
python -m app.test_query  # If test file exists
```

### Frontend

**Start development server:**
```bash
cd frontend/remotelock-assistant-frontend
npm run dev
```

**Build for production:**
```bash
cd frontend/remotelock-assistant-frontend
npm run build
```

**Preview production build:**
```bash
cd frontend/remotelock-assistant-frontend
npm run preview
```

**Install dependencies:**
```bash
cd frontend/remotelock-assistant-frontend
npm install
```

**Run linter:**
```bash
cd frontend/remotelock-assistant-frontend
npm run lint
```

## Environment Variables

Required backend environment variables (stored in `.env` or configured in Render):

- `GEMINI_API_KEY` - Google Gemini API key for LLM
- `NEO4J_URI` - Neo4j database URI (uses Neo4j Aura: `neo4j+s://d3db84ff.databases.neo4j.io`)
- `NEO4J_USER` - Neo4j username (typically `neo4j`)
- `NEO4J_PASSWORD` - Neo4j password
- `ALLOWED_ORIGINS` - Comma-separated list of CORS allowed origins for frontend
- `PYTHON_VERSION` - Python version for deployment (configured as `3.13` in render.yaml)

Optional:
- `PINECONE_API_KEY` - If using Pinecone for vector storage
- `PINECONE_ENVIRONMENT` - Pinecone environment

## Neo4j Graph Schema

The knowledge graph has the following structure:

```
Category (name, url)
  ├─ HAS_SUBCATEGORY → Subcategory (name, url)
  │   └─ CONTAINS_PAGE → Page (title, url, slug)
  │       └─ HAS_CONTENT → Content (text, chunk_index)
  └─ CONTAINS_PAGE → Page (title, url, slug)
      └─ HAS_CONTENT → Content (text, chunk_index)
```

**Node Types:**
- `Category` - Top-level documentation categories
- `Subcategory` - Sub-categories within categories
- `Page` - Individual documentation pages
- `Content` - Text chunks from pages (for better vector search granularity)

## LangGraph Agent Flow

The agent in `main.py` follows this pattern:

1. **call_llm node**: Invokes Gemini with system prompt + conversation history + sitemap context
2. **Conditional edge**: If LLM wants to call `retrieve_documentation` tool → go to tool node, else END
3. **tool node**: Executes retrieval (hybrid Cypher + vector search)
4. **Edge back to call_llm**: Processes tool results and generates final response

The agent uses a `GraphState` TypedDict with:
- `messages`: List of conversation messages (Human, AI, Function)
- `sitemap`: Complete sitemap structure for context

## Hybrid Search Strategy

The `ProductionRetriever.retrieve()` method implements:

1. **Cypher Search**: Graph queries to find pages by slug, title, category match
2. **Vector Search**: Semantic similarity using sentence embeddings
3. **Ranking**: Combines results with weighted scoring prioritizing exact matches
4. **Output**: Returns both `all_cypher_results` and `top_5_vector_results` for LLM processing

This ensures both structured navigation and semantic understanding.

## Important Implementation Notes

- The `SITEMAP_STRUCTURE` in `main.py` must match the actual RemoteLock site structure - update when documentation structure changes
- System prompt in `call_llm()` function is critical for agent behavior - it instructs the LLM when to use tools and how to format responses
- Retriever is initialized once at FastAPI startup (`retriever_instance`) to avoid repeated database connections
- CORS is configured for browser-based frontends - update `ALLOWED_ORIGINS` for production domains
- The scraper uses Playwright with stealth mode to avoid bot detection
- Content chunking is used to create manageable vector search units while preserving graph relationships

## Testing Changes

When modifying retrieval logic:
1. Test queries directly via `query_with_llm_json.py` to verify Cypher queries and vector results
2. Test via FastAPI endpoint: `curl -X POST http://localhost:8000/chat/ -H "Content-Type: application/json" -d '{"message":"How do I install 500 series lock?"}'`
3. Verify LangGraph flow in `main.py` handles tool calls correctly
4. Check that responses include proper article links from retrieved data

When modifying the knowledge graph:
1. Re-run the full pipeline with `remotelock_knowledge_graph_builder_online.py`
2. Verify graph structure in Neo4j browser
3. Test sample queries to ensure relationships are correct

## Common Pitfalls

- **Version conflicts**: `requirements.txt` has commented-out lines for packages with version conflicts (e.g., `fsspec`, `packaging`, `pinecone`). Use the uncommented versions
- **Neo4j connection**: Ensure Neo4j Aura database is accessible and credentials are correct
- **CORS errors**: Frontend must be in `ALLOWED_ORIGINS` or backend will reject requests
- **Empty responses**: Check that retriever initialized successfully on startup (look for "ProductionRetriever initialized successfully." log)
- **LangGraph errors**: If tool isn't called when expected, review system prompt in `call_llm()` function
