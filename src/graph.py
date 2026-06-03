from langgraph.graph import StateGraph, END
from src.state import GraphState
from src.nodes.guardrail import guardrail_node
from src.nodes.intent_router import intent_router_node
from src.nodes.rag import rag_node
from src.nodes.tool_call import tool_call_node


def chitchat_node(state: GraphState) -> GraphState:
    print("[chitchat] TODO: implement chitchat")
    return state


def response_generator_node(state: GraphState) -> GraphState:
    print("[response_generator] TODO: implement final response")
    return {**state, "final_response": "Not implemented yet."}


# --- Routing logic ---

def route_after_guardrail(state: GraphState) -> str:
    if state["guardrail_decision"] == "BLOCK":
        return "blocked"
    return "intent_router"


def route_by_intent(state: GraphState) -> str:
    intent = state.get("intent", "chitchat")
    if intent == "rag":
        return "rag"
    elif intent == "tool_call":
        return "tool_call"
    return "chitchat"


# --- Build graph ---

def build_graph() -> StateGraph:
    graph = StateGraph(GraphState)

    graph.add_node("guardrail", guardrail_node)
    graph.add_node("intent_router", intent_router_node)
    graph.add_node("rag", rag_node)
    graph.add_node("tool_call", tool_call_node)
    graph.add_node("chitchat", chitchat_node)
    graph.add_node("response_generator", response_generator_node)

    graph.set_entry_point("guardrail")

    graph.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {"blocked": END, "intent_router": "intent_router"},
    )

    graph.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {"rag": "rag", "tool_call": "tool_call", "chitchat": "chitchat"},
    )

    graph.add_edge("rag", "response_generator")
    graph.add_edge("tool_call", "response_generator")
    graph.add_edge("chitchat", "response_generator")
    graph.add_edge("response_generator", END)

    return graph.compile()
