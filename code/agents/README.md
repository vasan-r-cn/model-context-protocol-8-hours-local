# code/agents — Module 2, the single-agent progression

Three files, each adding one idea over the last. All use the same one tool
(`fetch_inventory`, SD-WAN inventory over the vManage NVCL API) so you watch the
*agent* mechanics change, not the domain.

| File | Exercise | Adds |
|---|---|---|
| `sdwan_agent.py` | 2.1 | the tool loop — model decides, loop runs the tool, model answers |
| `agent_short_term_memory.py` | 2.2 | `InMemorySaver` checkpointer — follow-ups reuse remembered context |
| `agent_streaming.py` | 2.3 | streaming — progress events while a slow call runs |

Vendored from `agentic-ai-workshop/agents/` with two adaptations: `ChatOpenAI`
pointed at OpenRouter (reliable; avoids the unpinned `langchain-openrouter`
dep), and a single standardized `VMANAGE_HOST` env var (the originals mixed
`VMANAGE_HOST` and `FQDN`).

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # OpenRouter key + your pod's vManage FQDN:port
python sdwan_agent.py
```

**vManage endpoint:** `https://$VMANAGE_HOST/nvcl/api/inventory/`. Set
`VMANAGE_HOST` to your pod's exposed FQDN **and port** (e.g. the vManage service
exposed via `cclorchestrator`), not the in-pod `:80`. TLS verification is off
(lab self-signed cert). If vManage is unreachable, the tool returns an `error`
dict and the agent reports it — the agent mechanics still demonstrate.
