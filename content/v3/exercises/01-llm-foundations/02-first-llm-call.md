# First LLM Call

**Category:** 01 · LLM Foundations · **Duration:** 8 min · **Runs on:** `linuxdesktop64` · **Targets:** —

**Devices in play:** None — a bare LLM returns text only. No network device is reached.

## Introduction

Everything else today sits on top of one primitive: a chat completion. Before agents, tools, or MCP, you send a model some text and it sends text back. That's it. This exercise strips the stack down to that single call so you can see its shape — and, more importantly, its *ceiling*.

The program you run can answer "what is BGP?" It **cannot** answer "is Gi2 up on `sdceightkv24`?" — because a bare model has no way to look. It only predicts text. When you feel that wall, you'll understand exactly what an agent adds in Module 2.

You'll call the model through **OpenRouter**, a provider gateway: one API key and base URL in front of many models, which is why the rest of the day can swap models without changing code.

## What You'll Learn

- How a chat completion request is actually shaped: model, messages, params
- What a provider gateway (OpenRouter) adds in front of a model
- How to read token counts and what they cost
- Why the model returns text and nothing else — it cannot act

## Before You Start

- Exercise 1.1 complete; `OPENROUTER_API_KEY` exported

## Architecture Overview

| Component | Role |
|---|---|
| `call_llm.py` (`code/llm/`) | the whole program — one `ChatOpenAI.invoke()` |
| **OpenRouter** (`https://openrouter.ai/api/v1`) | the gateway: one key/base-URL in front of many models |
| `OPENROUTER_MODEL` | which model answers (default `anthropic/claude-sonnet-4`) |

```text
your prompt --> ChatOpenAI --> OpenRouter gateway --> model --> text back
                 (no tools; text in, text out)
```

## Setup

### Step 1 — build the venv

```bash
cd code/llm
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # put your OpenRouter key in .env
```

## Exercises

### Part 1 — make a call and read it (4 min)

```bash
python call_llm.py
```

At the prompt, ask something a model can answer from its own training:

```text
Explain BGP route reflection in two sentences.
```

Read your own code (`call_llm.py`) — the call is four things:

- `model=MODEL` → which model (an OpenRouter id like `anthropic/claude-sonnet-4`).
- `base_url="https://openrouter.ai/api/v1"` → the **gateway**, not the model vendor directly.
- `api_key=API_KEY` → your OpenRouter key.
- `llm.invoke(query)` → sends your text as a `messages` list, returns the completion.

The program prints the answer **and** a `[tokens]` line.

**A1.** Record the `model`, and the `input` / `output` / `total` token counts from your call.

> Answer to check yourself: tokens are how usage is billed — input (your prompt + any system text) plus output (the model's reply). A longer conversation re-sends prior turns, so input tokens grow every turn (that's Module 2's memory cost, foreshadowed).

### Part 2 — hit the wall (4 min)

Now ask something that needs a live device:

```text
Is interface Gi2 up on sdceightkv24 right now?
```

**B1.** What did it do — refuse, guess, or hallucinate a plausible-looking answer? Why can this program *never* answer correctly?

> Answer to check yourself: it has no tool, no network, no way to reach `sdceightkv24`. At best it says it can't know; at worst it invents an answer. A bare LLM predicts text; it cannot *act*. Giving it a way to act — a tool loop — is exactly what Module 2 builds.

**Reflection Questions**

1. OpenRouter sits between you and the model. What does that gateway buy you across a whole workshop of swapping models?
2. Input tokens grow as a conversation lengthens. What does that imply for a long agent session's cost?
3. The model answered BGP but not the interface question. State the one-sentence difference between what a model *knows* and what it can *do*.

## Verify

**Success Criteria**

- A prompt you wrote returns a completion
- You can state the model id, the provider, and the token count of your call
- You can explain why this program cannot answer "is Gi2 up on sdceightkv24?"

**Done when:** you got a completion, recorded model + token counts, and can say in one sentence why a bare LLM can't answer a live-device question.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `OPENROUTER_API_KEY not set` | key not in `.env` or shell | put it in `code/llm/.env`, or `export OPENROUTER_API_KEY=...` |
| 401 / auth error | key wrong or unfunded | check the key on your lab sheet; confirm OpenRouter credit |
| `model not found` | bad `OPENROUTER_MODEL` | unset it to use the default, or use a valid OpenRouter id |
| no `[tokens]` line | provider didn't return usage metadata | harmless; the answer is still valid |
| import error on `langchain_openai` | venv not active / deps not installed | `. .venv/bin/activate`; `pip install -r requirements.txt` |

## Quick Reference

```bash
cd code/llm && . .venv/bin/activate
python call_llm.py          # type a prompt; 'exit' to quit
```

- One call: `ChatOpenAI(model, api_key, base_url).invoke(text)`.
- OpenRouter = gateway; `OPENROUTER_MODEL` picks the model.
- A bare LLM returns **text only** — it cannot reach a device. Agents (Module 2) add the tool loop.

---

**Source material:** `code/llm/call_llm.py` (vendored from the sibling agentic-ai-workshop repo)
