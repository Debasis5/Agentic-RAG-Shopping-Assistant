import json
import random
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from src.state import GraphState


# ---------------------------------------------------------------------------
# Mock tools
# ---------------------------------------------------------------------------

@tool
def get_order_status(order_id: str) -> str:
    """Get the current status of a customer order by order ID."""
    statuses = ["Processing", "Shipped", "Out for Delivery", "Delivered", "Cancelled"]
    status = random.choice(statuses)
    return json.dumps({
        "order_id": order_id,
        "status": status,
        "estimated_delivery": "June 6, 2026" if status not in ("Delivered", "Cancelled") else None,
        "last_updated": "June 3, 2026 10:30 AM",
    })


@tool
def track_shipment(order_id: str) -> str:
    """Get shipment tracking details and courier information for an order."""
    return json.dumps({
        "order_id": order_id,
        "courier": "ShopEasy Logistics",
        "awb_number": f"SHL{random.randint(100000000, 999999999)}",
        "current_location": "Mumbai Hub",
        "status": "In Transit",
        "estimated_delivery": "June 6, 2026",
    })


@tool
def get_account_info(email: str) -> str:
    """Get basic account information for a customer by their email address."""
    return json.dumps({
        "email": email,
        "name": "Customer",
        "account_status": "Active",
        "member_since": "January 2022",
        "shopeasy_pay_balance": f"₹{random.randint(0, 5000)}",
        "active_orders": random.randint(0, 3),
    })


@tool
def get_return_status(order_id: str) -> str:
    """Get the status of a return or refund request for an order."""
    statuses = ["Return Initiated", "Pickup Scheduled", "Item Received", "Refund Processed"]
    status = random.choice(statuses)
    return json.dumps({
        "order_id": order_id,
        "return_status": status,
        "refund_amount": f"₹{random.randint(200, 5000)}",
        "refund_method": "Original Payment Method",
        "expected_refund_date": "June 8, 2026" if status != "Refund Processed" else "June 2, 2026",
    })


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

_TOOLS = [get_order_status, track_shipment, get_account_info, get_return_status]
_TOOL_MAP = {t.name: t for t in _TOOLS}

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(_TOOLS)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def tool_call_node(state: GraphState) -> dict:
    query = state["query"]

    response = _llm.invoke([HumanMessage(content=query)])

    if not response.tool_calls:
        print("[tool_call] LLM did not invoke any tool")
        return {"tool_output": {"result": response.content}}

    results = []
    for tc in response.tool_calls:
        tool_name = tc["name"]
        tool_args = tc["args"]
        print(f"[tool_call] calling {tool_name}({tool_args})")

        fn = _TOOL_MAP.get(tool_name)
        if fn is None:
            output = json.dumps({"error": f"Unknown tool: {tool_name}"})
        else:
            output = fn.invoke(tool_args)

        results.append({
            "tool": tool_name,
            "args": tool_args,
            "output": json.loads(output) if isinstance(output, str) else output,
        })

    print(f"[tool_call] {len(results)} tool(s) executed")
    return {"tool_output": results}
