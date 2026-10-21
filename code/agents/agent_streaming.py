"""Agent with streaming. Module 2, exercise 2.3.

Vendored from agentic-ai-workshop/agents/agent_streaming.py, same adaptations
(ChatOpenAI->OpenRouter; VMANAGE_HOST with FQDN fallback).

What it adds over 2.2: streaming. The LLM is created with streaming=True, the
tool emits progress events via LangGraph's stream writer, and the response is
consumed with agent.stream(..., stream_mode=["updates", "custom"]) so the user
sees "Connecting... / parsing... / done" while a slow call runs instead of a
frozen screen.

    export OPENROUTER_API_KEY=sk-or-v1-...
    export VMANAGE_HOST=<your pod FQDN>:<exposed vmanage port>
    python agent_streaming.py
"""

import logging
import os
import time
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("sdwan-agent")

API_KEY = os.getenv("OPENROUTER_API_KEY")
VMANAGE_HOST = os.getenv("VMANAGE_HOST") or os.getenv("FQDN")
MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set")
if not VMANAGE_HOST:
    raise RuntimeError("VMANAGE_HOST not set (your pod FQDN + exposed vManage port)")

llm = ChatOpenAI(
    model=MODEL,
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
    streaming=True,
)

checkpointer = InMemorySaver()
thread_id = "sdwan_agent_session"


@tool
def fetch_inventory() -> Dict[str, Any]:
    """Fetch the SD-WAN device inventory for this lab. Emits progress events."""
    writer = get_stream_writer()
    writer({"stage": "start", "message": "Connecting to inventory API"})
    start = time.time()
    url = f"https://{VMANAGE_HOST}/nvcl/api/inventory/"
    response = httpx.get(url, verify=False, follow_redirects=True, timeout=30)
    writer({"stage": "download", "message": "Inventory received, parsing"})
    response.raise_for_status()
    data = response.json()
    writer({"stage": "completed", "message": f"Inventory fetched in {time.time() - start:.2f}s"})
    return data


agent = create_agent(model=llm, tools=[fetch_inventory], checkpointer=checkpointer)

system_prompt = {
    "role": "system",
    "content": (
        "You are an SDWAN network assistant.\n"
        "When a user asks about device inventory:\n"
        "- Call the `fetch_inventory` tool ONLY if the inventory has not yet "
        "been fetched in the current conversation.\n"
        "- Remember the returned inventory and reuse it for follow-up questions.\n"
        "- Do NOT call the tool again unless the user explicitly asks to refresh.\n"
        "Group devices logically by role and show their status."
    ),
}


def run_stream(messages) -> str:
    final_text = ""
    for stream_mode, chunk in agent.stream(
        {"messages": messages},
        {"configurable": {"thread_id": thread_id}},
        stream_mode=["updates", "custom"],
    ):
        if stream_mode == "updates":
            logger.info(f"[updates] {chunk}")
            if isinstance(chunk, dict) and "model" in chunk:
                msgs = chunk["model"].get("messages", [])
                if msgs and getattr(msgs[-1], "content", None):
                    final_text = msgs[-1].content
        elif stream_mode == "custom":
            logger.info(f"[custom] {chunk}")   # the tool's progress events
    logger.info(f"\nAgent Response:\n{final_text}\n")
    return final_text


if __name__ == "__main__":
    run_stream([system_prompt, {"role": "user", "content": "Show me the full device inventory"}])
    run_stream([{"role": "user", "content": "How many device types exist?"}])
    run_stream([{"role": "user", "content": "Which device category has the highest number of devices?"}])
    run_stream([{"role": "user", "content": "List only the devices from that device category."}])
