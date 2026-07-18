import os
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")

# Mock order database (reference date in prompt: July 17, 2026)
MOCK_ORDERS = {
    "ORD-101": {
        "purchase_date": "2026-07-10",
        "amount": 89.99,
        "item_name": "Premium Leather Jacket",
        "is_clearance": False,
        "refund_status": "NONE",
    },
    "ORD-102": {
        "purchase_date": "2026-05-15",
        "amount": 120.00,
        "item_name": "Pro Running Shoes",
        "is_clearance": False,
        "refund_status": "NONE",
    },
    "ORD-103": {
        "purchase_date": "2026-07-14",
        "amount": 29.99,
        "item_name": "Clearance Gym Tee",
        "is_clearance": True,
        "refund_status": "NONE",
    },
}


def check_order_status(order_id: str) -> dict:
    """Look up an order by ID (e.g. ORD-101)."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"status": "error", "message": f"Order ID {order_id} not found."}
    return {"status": "success", "order_details": order}


def process_refund(order_id: str, amount: float) -> dict:
    """Process a refund for a validated order."""
    order = MOCK_ORDERS.get(order_id)
    if not order:
        return {"status": "error", "message": "Order ID not found."}
    if order["refund_status"] == "REFUNDED":
        return {"status": "error", "message": f"Order {order_id} already refunded."}
    order["refund_status"] = "REFUNDED"
    return {
        "status": "success",
        "message": f"Processed refund of ${amount} for {order_id}",
    }


check_order_tool = FunctionTool(func=check_order_status)
process_refund_tool = FunctionTool(func=process_refund)

refund_agent = Agent(
    name="retail_refund_agent",
    model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}"),
    instruction=(
        "You are a policy-compliant Retail Refund Assistant.\n\n"
        "Rules:\n"
        "1. Ask for Order ID if missing.\n"
        "2. Call check_order_status first.\n"
        "3. Current date is Friday, July 17, 2026. Return window is 30 days.\n"
        "4. Clearance items (is_clearance=true) are non-refundable.\n"
        "5. Only call process_refund when eligible.\n"
        "6. If ineligible, explain why clearly."
    ),
    tools=[check_order_tool, process_refund_tool],
)

# ADK / agents-cli eval expects this name when loading the agent.
root_agent = refund_agent
