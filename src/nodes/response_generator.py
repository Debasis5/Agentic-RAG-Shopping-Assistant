import json
from langchain_openai import ChatOpenAI
from src.state import GraphState

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

_RAG_SYSTEM_PROMPT = """You are a helpful customer support assistant for ShopEasy, an Indian e-commerce platform.

Answer the user's question using ONLY the provided knowledge base excerpts.
Be concise, friendly, and factual. If the excerpts do not contain enough information to answer, say so honestly.
Do not make up information."""

_TOOL_SYSTEM_PROMPT = """You are a helpful customer support assistant for ShopEasy, an Indian e-commerce platform.

You have just retrieved live data from ShopEasy's systems. Use it to answer the user's question clearly and concisely.
Present the information in a friendly, readable way — avoid dumping raw data."""


def response_generator_node(state: GraphState) -> dict:
    # Pass-through: chitchat already set final_response
    if state.get("final_response"):
        print("[response_generator] pass-through (chitchat)")
        return {}

    query = state["query"]

    # RAG path
    if state.get("retrieved_docs"):
        context = "\n\n".join(state["retrieved_docs"])
        response = _llm.invoke([
            {"role": "system", "content": _RAG_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
        ])
        reply = response.content.strip()
        print(f"[response_generator] RAG reply ({len(reply)} chars)")
        return {"final_response": reply}

    # Tool call path
    if state.get("tool_output"):
        tool_data = json.dumps(state["tool_output"], indent=2)
        response = _llm.invoke([
            {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": f"Retrieved data:\n{tool_data}\n\nQuestion: {query}"},
        ])
        reply = response.content.strip()
        print(f"[response_generator] tool reply ({len(reply)} chars)")
        return {"final_response": reply}

    # Fallback
    print("[response_generator] no context available")
    return {"final_response": "I'm sorry, I wasn't able to find information to answer your question. Please contact ShopEasy support at 1800-3000-9009."}
