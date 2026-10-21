"""Simple agent — one tool, wired by hand. Module 2, exercise 2.1.

Vendored from agentic-ai-workshop/agents/sdwan_agent.py and adapted:
  * langchain_openai.ChatOpenAI against OpenRouter (reliable; no unpinned
    langchain-openrouter dep).
  * Endpoint host read from VMANAGE_HOST (falls back to FQDN) so the memory
    and streaming variants use the SAME env var as this one.

The agent is a model PLUS a tool loop: the model decides to call
`fetch_inventory`, the loop runs it, feeds the result back, and the model
answers. One tool, one decision — that is what separates an agent from the
bare LLM of Module 1.

    export OPENROUTER_API_KEY=sk-or-v1-...
    export VMANAGE_HOST=<your pod FQDN>:<exposed vmanage port>
    python sdwan_agent.py
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

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("sdwan-agent-demo")

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


@tool
def fetch_inventory() -> Dict[str, Any]:
    """Fetch the SD-WAN device inventory for this lab."""
    url = f"https://{VMANAGE_HOST}/nvcl/api/inventory/"
    logger.info(f"[TOOL] Fetching inventory -> {url}")
    start = time.time()
    try:
        response = httpx.get(url, verify=False, follow_redirects=True, timeout=30)
        response.raise_for_status()
        data = response.json()
        logger.info(f"[TOOL] Inventory fetched in {time.time() - start:.2f}s")
        return data
    except httpx.HTTPError as exc:
        logger.error(f"[TOOL] HTTP error: {exc}")
        return {"error": str(exc)}
    except Exception as exc:
        logger.exception("[TOOL] Unexpected error")
        return {"error": str(exc)}


agent = create_agent(model=llm, tools=[fetch_inventory])


def run_agent() -> None:
    query = "List my full SD-WAN device inventory details."
    logger.info(f"User query: {query}")
    response = agent.invoke({"messages": [{"role": "user", "content": query}]})
    logger.info("Agent response:")
    logger.info(response["messages"][-1].content)


if __name__ == "__main__":
    run_agent()
