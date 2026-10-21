"""First LLM call — a minimal OpenRouter chat completion.

Vendored from agentic-ai-workshop/llm_call/call_llm.py and adapted:
  * Uses langchain_openai.ChatOpenAI pointed at OpenRouter instead of the
    unpinned `langchain-openrouter` package. The sibling repo's own
    multi_agent_v2 made the same switch after ChatOpenRouter timed out.
  * Model is an env var (OPENROUTER_MODEL), not hardcoded.

This program has NO tools. It can only return text — it cannot look at a
router. That limit is the whole point of Module 1 and the reason Module 2
introduces agents.

    export OPENROUTER_API_KEY=sk-or-v1-...
    python call_llm.py
"""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("OPENROUTER_MODEL", "anthropic/claude-sonnet-4")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set (see .env.example).")


def call_llm(query: str) -> None:
    if not query.strip():
        print("Please enter a valid prompt (not empty)")
        return
    try:
        llm = ChatOpenAI(
            model=MODEL,
            api_key=API_KEY,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
        )
        response = llm.invoke(query)
        print("\nAI Response:\n", response.content)
        # usage_metadata carries the token counts the model reports back.
        usage = getattr(response, "usage_metadata", None)
        if usage:
            print(
                f"\n[tokens] input={usage.get('input_tokens')} "
                f"output={usage.get('output_tokens')} "
                f"total={usage.get('total_tokens')}  model={MODEL}"
            )
    except Exception as exc:
        print("\nError calling LLM:", str(exc))


if __name__ == "__main__":
    while True:
        user_prompt = input("\nEnter your prompt (or type 'exit'): ")
        if user_prompt.lower() in ("exit", "quit"):
            print("Exiting LLM Playground")
            break
        call_llm(user_prompt)
