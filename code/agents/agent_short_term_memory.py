"""Agent with short-term memory. Module 2, exercise 2.2.

Vendored from agentic-ai-workshop/agents/agent_short_term_memory.py, same two
adaptations as sdwan_agent.py (ChatOpenAI->OpenRouter; VMANAGE_HOST with FQDN
fallback).

What it adds over 2.1: a LangGraph InMemorySaver checkpointer keyed by a
thread_id. The agent fetches inventory once, then answers follow-ups ("and the
other one?") from the remembered conversation instead of calling the tool
again. Memory here is just the message history re-sent each turn — not magic.

    export OPENROUTER_API_KEY=sk-or-v1-...
    export VMANAGE_HOST=<your pod FQDN>:<exposed vmanage port>
    python agent_short_term_memory.py
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
)

checkpointer = InMemorySaver()
thread_id = "sdwan_agent_session"


@tool
def fetch_inventory() -> Dict[str, Any]:
    """Fetch the SD-WAN device inventory for this lab."""
    url = f"https://{VMANAGE_HOST}/nvcl/api/inventory/"
    logger.info(f"Tool call -> {url}")
    start = time.time()
    response = httpx.get(url, verify=False, follow_redirects=True, timeout=30)
    response.raise_for_status()
    data = response.json()
    logger.info(f"Inventory fetched successfully in {time.time() - start:.2f}s")
    return data


agent = create_agent(model=llm, tools=[fetch_inventory], checkpointer=checkpointer)

system_prompt = {
    "role": "system",
    "content": (
        "You are an SDWAN network assistant.\n"
        "When a user asks about device inventory:\n"
        "- Call the `fetch_inventory` tool ONLY if the inventory has not yet "
        "been fetched in the current conversation.\n"
        "- After calling the tool, remember the returned inventory for the "
        "entire session and reuse it for all follow-up questions.\n"
        "- Do NOT call the tool again unless the user explicitly asks to "
        "refresh or reload the inventory.\n"
        "When presenting results:\n"
        "- Group devices by device ROLE logically.\n"
        "- Clearly show the status of each device.\n"
        "For follow-up questions such as counting, filtering, comparisons, "
        "or summaries, ALWAYS use the stored inventory already present in "
        "memory instead of calling the tool again."
    ),
}


if __name__ == "__main__":
    print("Type your questions below. Enter 'exit' or 'quit' to end the session.\n")
    first_turn = True
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            break
        if first_turn:
            messages = [system_prompt, {"role": "user", "content": user_input}]
            first_turn = False
        else:
            messages = [{"role": "user", "content": user_input}]
        res = agent.invoke(
            {"messages": messages},
            {"configurable": {"thread_id": thread_id}},
        )
        print(f"\nAssistant: {res['messages'][-1].content}\n")
