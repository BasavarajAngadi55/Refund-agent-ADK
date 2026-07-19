import os
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.models.google_llm import Gemini
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

from app.database import get_order, mark_refunded

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def build_model():
    """Cloud: Groq free API (recommended) or Gemini. Local: Ollama/Gemma."""
    if GROQ_API_KEY:
        return LiteLlm(model=f"groq/{GROQ_MODEL}")
    if GEMINI_API_KEY:
        return Gemini(
            model=GEMINI_MODEL,
            client_kwargs={"api_key": GEMINI_API_KEY},
        )
    return LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}")


def check_order_status(order_id: str) -> dict:
    """Look up an order by ID (e.g. ORD-101) from SQLite."""
    normalized_id = order_id.strip().upper()
    order = get_order(normalized_id)
    if not order:
        return {"status": "error", "message": f"Order ID {normalized_id} not found."}
    return {"status": "success", "order_details": order}


def process_refund(order_id: str, amount: float) -> dict:
    """Process a refund for a validated order in SQLite."""
    normalized_id = order_id.strip().upper()
    order = get_order(normalized_id)
    if not order:
        return {"status": "error", "message": "Order ID not found."}
    if order["refund_status"] == "REFUNDED":
        return {
            "status": "error",
            "message": f"Order {normalized_id} already refunded.",
        }
    if not mark_refunded(normalized_id):
        return {
            "status": "error",
            "message": f"Order {normalized_id} could not be refunded.",
        }
    return {
        "status": "success",
        "message": f"Processed refund of ${amount} for {normalized_id}",
    }

check_order_tool = FunctionTool(func=check_order_status)
process_refund_tool = FunctionTool(func=process_refund)

refund_agent = Agent(
    name="retail_refund_agent",
    model=build_model(),
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
