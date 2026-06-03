# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use `uv run` to ensure the project's virtual environment is used. Plain `python`/`uvicorn`/`streamlit` will use the wrong environment.

```bash
# Install dependencies
uv sync

# Run the FastAPI backend (required before starting Streamlit)
uv run uvicorn api:app --reload --port 8000

# Run the Streamlit frontend
uv run streamlit run streamlit_app.py

# Run a single query via CLI (bypasses API/UI)
uv run python main.py

# One-time setup: generate policy PDFs then ingest into ChromaDB
uv run python scripts/generate_docs.py
uv run python pipelines/ingest_docs.py
```

No test suite or linter is configured in this project.

## Architecture

This is a two-process application: a **FastAPI backend** (`api.py`) and a **Streamlit frontend** (`streamlit_app.py`). They communicate via HTTP — the frontend POSTs to `/chat` and receives a Server-Sent Events stream of tokens.

### LangGraph pipeline (`src/`)

The core logic is a LangGraph `StateGraph` built in `src/graph.py`. Every request flows through the same pipeline:

```
guardrail → [BLOCK → END] or [PASS → intent_router]
intent_router → rag | tool_call | chitchat
rag / tool_call / chitchat → response_generator → END
```

`GraphState` (defined in `src/state.py`) is the single shared dict passed between all nodes. Key fields: `query`, `intent`, `retrieved_docs`, `tool_output`, `guardrail_decision`, `final_response`.

**Critical pattern — lazy LLM initialisation:** Every node file uses `@lru_cache(maxsize=1)` on a `_get_llm()` / `_get_retriever()` factory instead of creating `ChatOpenAI` / `OpenAIEmbeddings` at module level. This is required because `src/graph.py` is imported before `load_dotenv()` runs in `api.py`. Breaking this pattern will cause `openai.OpenAIError: Missing credentials` on startup.

### Streaming (api.py)

`POST /chat` uses `graph.astream_events(state, version="v2")` to stream events. Only `on_chat_model_stream` events from nodes `response_generator` and `chitchat` are forwarded as tokens — guardrail and intent_router LLM outputs are filtered out by checking `event["metadata"]["langgraph_node"]`. Guardrail blocks are emitted as a single token from the `on_chain_end` event of the `guardrail` node.

### Vector store

ChromaDB persists locally at `chroma_db/` (relative to project root). The collection is named `support_docs`. Documents come from PDFs in `data/docs/` chunked at 1000 chars. The RAG node retrieves top-3 chunks.

### Streamlit sidebar (known behaviour)

Streamlit 1.58 hides the sidebar via a CSS transform when `aria-expanded="false"` on `section[data-testid="stSidebar"]`. The fix in `streamlit_app.py` uses:
```css
section[data-testid="stSidebar"][aria-expanded="false"] {
  margin-left: 0 !important;
  transform: none !important;
}
```
The collapse button is hidden via `div[data-testid="stSidebarCollapseButton"] { display: none !important; }`. Do not set `background-color` or `color` on sidebar elements — it causes invisible (white-on-white) text.

## Environment

Requires a `.env` file at the project root:
```
OPENAI_API_KEY=sk-...
```

Model used throughout: `gpt-4o-mini`. Embeddings: `text-embedding-3-small`.
