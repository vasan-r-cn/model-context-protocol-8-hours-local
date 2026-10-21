# code/llm — Module 1, first LLM call

A single file, `call_llm.py`: the smallest possible OpenRouter chat call. No
tools, no agent — it can only return text. That ceiling is the lesson.

Vendored from the sibling `agentic-ai-workshop/llm_call/call_llm.py`, adapted to
use `langchain_openai.ChatOpenAI` against OpenRouter (reliable; avoids the
unpinned `langchain-openrouter` dependency).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # put your OpenRouter key in it
python call_llm.py              # type a prompt; 'exit' to quit
```

Model is `OPENROUTER_MODEL` (default `anthropic/claude-sonnet-4`).
