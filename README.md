# ShopEasy Agentic RAG — Aria Customer Support

An agentic Retrieval-Augmented Generation (RAG) system for ShopEasy, an Indian e-commerce platform. Aria is a context-aware AI customer support agent built with LangGraph, served via a FastAPI streaming backend, and presented through a Streamlit chat interface.

---

## Features

- **Safety guardrails** — classifies and blocks harmful, out-of-scope, or advice-seeking queries before they reach the LLM
- **Intent routing** — automatically routes queries to the right handler: RAG, live tool calls, or chitchat
- **RAG pipeline** — retrieves relevant policy excerpts from a ChromaDB vector store using OpenAI embeddings
- **Live tool calls** — fetches order status, shipment tracking, account info, and return status via function calling
- **Streaming responses** — tokens stream token-by-token from FastAPI to the Streamlit UI via Server-Sent Events (SSE)
- **Aria persona** — consistent, warm, mobile-optimised responses in British English with Indian currency formatting

---

## Architecture

```
User Query
    │
    ▼
┌─────────────┐
│  Guardrail  │──── BLOCK ──▶ Blocked response (PASS-through)
└──────┬──────┘
       │ PASS
       ▼
┌──────────────┐
│ Intent Router│
└──────┬───────┘
       ├── rag ──────▶ RAG Node ──────▶ Response Generator ──▶ Final Response
       ├── tool_call ▶ Tool Call Node ▶ Response Generator ──▶ Final Response
       └── chitchat ─▶ Chitchat Node ─────────────────────────▶ Final Response
```

### Components

| Component | Description |
|---|---|
| `api.py` | FastAPI app — `POST /chat` streams SSE tokens, `GET /health` |
| `streamlit_app.py` | Streamlit frontend — Aria chat UI with streaming support |
| `src/graph.py` | LangGraph `StateGraph` — wires nodes and routing logic |
| `src/state.py` | `GraphState` TypedDict — shared state across all nodes |
| `src/nodes/guardrail.py` | Safety classifier — PASS / BLOCK_HARMFUL / BLOCK_ADVICE / BLOCK_SCOPE |
| `src/nodes/intent_router.py` | Intent classifier — rag / tool_call / chitchat |
| `src/nodes/rag.py` | ChromaDB retriever — top-3 semantic search over policy docs |
| `src/nodes/tool_call.py` | Function calling — order, shipment, account, return tools |
| `src/nodes/chitchat.py` | Conversational response node |
| `src/nodes/response_generator.py` | Final answer synthesis using Aria persona |
| `pipelines/ingest_docs.py` | One-time pipeline — chunks and embeds PDFs into ChromaDB |
| `scripts/generate_docs.py` | One-time script — generates 5 ShopEasy policy PDFs |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM & Embeddings | OpenAI GPT-4o-mini + text-embedding-3-small |
| Vector Store | ChromaDB (local persistence) |
| API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Package Manager | UV |

---

## Project Structure

```
├── api.py                  # FastAPI backend
├── streamlit_app.py        # Streamlit frontend
├── main.py                 # CLI entrypoint
├── pyproject.toml          # Project dependencies
├── requirements.txt        # Pip-compatible dependencies
├── .env                    # Environment variables (not committed)
├── data/
│   └── docs/               # Generated policy PDFs
├── chroma_db/              # ChromaDB vector store (auto-created)
├── pipelines/
│   └── ingest_docs.py      # Document ingestion pipeline
├── scripts/
│   └── generate_docs.py    # Policy PDF generator
└── src/
    ├── state.py            # LangGraph state definition
    ├── graph.py            # Graph construction
    └── nodes/
        ├── guardrail.py
        ├── intent_router.py
        ├── rag.py
        ├── tool_call.py
        ├── chitchat.py
        └── response_generator.py
```

---

## Setup

### Prerequisites

- Python 3.13+
- [UV](https://docs.astral.sh/uv/) package manager
- OpenAI API key

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd agents-capstone-project-agentic-rag
uv sync
```

### 2. Configure environment

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-...
```

### 3. Generate policy documents (one-time)

```bash
uv run python scripts/generate_docs.py
```

### 4. Ingest documents into ChromaDB (one-time)

```bash
uv run python pipelines/ingest_docs.py
```

---

## Running the Application

### Start the FastAPI backend

```bash
uv run uvicorn api:app --reload --port 8000
```

### Start the Streamlit frontend

```bash
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501` in your browser.

### API endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/chat` | Stream a response — body: `{"query": "..."}` |

The `/chat` endpoint returns Server-Sent Events with two frame types:

```json
// Token frame (streamed during generation)
{"type": "token", "content": "Hello"}

// Done frame (sent after final token)
{"type": "done", "intent": "chitchat", "guardrail_decision": "PASS"}
```

---

## CLI Usage

```bash
uv run python main.py
```

---

## Guardrail Behaviour

| Decision | Trigger |
|---|---|
| `PASS` | Shopping queries, greetings, account/order questions |
| `BLOCK_HARMFUL` | Hacking, fraud, illegal activity, abuse |
| `BLOCK_ADVICE` | Medical, legal, or financial advice |
| `BLOCK_SCOPE` | Competitor comparisons, price predictions, unrelated topics |

---

## Knowledge Base & Ingestion Pipeline

Five ShopEasy policy PDFs are generated by `scripts/generate_docs.py` into `data/docs/`:

- Returns & Refunds Policy
- Shipping & Delivery Policy
- Payments & Pricing Policy
- Account Management Policy
- Product Condition & Listing Guidelines

`pipelines/ingest_docs.py` processes these into ChromaDB across four stages:

```
data/docs/*.pdf
      │
      ▼
┌──────────────────────────────────────────┐
│ Stage 1 · LOAD                           │
│  PyPDFDirectoryLoader                    │
│  · Reads all PDFs, merges pages per doc  │
│  · Strips header metadata per document:  │
│    title, version, effective_date,       │
│    department                            │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│ Stage 2 · CHUNK                          │
│  RecursiveCharacterTextSplitter          │
│  · chunk_size    = 650 chars             │
│  · chunk_overlap = 0                     │
│  · Splits on numbered sections first     │
│    (regex: \n(?=\d+\. )), then \n\n,    │
│    then \n                               │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│ Stage 3 · EMBED                          │
│  OpenAIEmbeddings                        │
│  · Model: text-embedding-3-small         │
│  · 1536-dimensional vectors              │
└─────────────────┬────────────────────────┘
                  │
                  ▼
┌──────────────────────────────────────────┐
│ Stage 4 · STORE                          │
│  ChromaDB                                │
│  · Collection : support_docs             │
│  · Persisted to : chroma_db/             │
└──────────────────────────────────────────┘
```

At query time the RAG node retrieves the **top-3 chunks** by cosine similarity and passes them as context to the response generator.

Re-run the pipeline whenever documents change:

```bash
uv run python pipelines/ingest_docs.py
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (required) |
