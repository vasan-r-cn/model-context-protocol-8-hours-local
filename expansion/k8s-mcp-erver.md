# Kubernetes Agent (k8s-agent)

## Introduction

The Kubernetes Agent (`k8s-agent`) is an AI-powered operations assistant that understands your cluster state and reasons over it using a Large Language Model (LLM). Instead of memorizing `kubectl` commands or manually parsing logs, you interact with the agent in plain English, and it handles the rest.

---

## What You'll Learn

* How MCP (Model Context Protocol) connects an LLM to Kubernetes tools
* How the Kubernetes Python SDK replaces manual `kubectl` commands
* How to run a multi-turn AI agent loop with tool-calling
* How to expose the agent as a web UI with Gradio
* How to debug and extend the agent with new tools

---

## Architecture Overview

The `k8s-agent` is built from four core components:

| Component                 | Role                                                                                    |
| ------------------------- | --------------------------------------------------------------------------------------- |
| **LLM (Claude / GPT)**    | Reads cluster state, analyzes issues, and provides recommendations                      |
| **MCP Server**            | Exposes 7 Kubernetes tools for LLM interaction, including pods, logs, events, and nodes |
| **Kubernetes Python SDK** | Connects directly to the Kubernetes API server without using a `kubectl` subprocess     |
| **Gradio Web UI**         | Provides a browser-based chat interface on port `7860`                                  |

---

## Setup

### Step 1 — Verify Installation

Confirm that all required packages are installed:

```bash
pip list | grep -E 'openai|mcp|gradio|kubernetes'
```

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/ubuntu-cclorchestrator78-agentic-ai-workshop-mcp-sdwan-09-10-2026_12_56_PM.png)

---

### Step 2 — Configure Your API Key

Navigate to the Kubernetes agent directory:

```bash
cd ~/agentic-ai-workshop/mcp/k8s
```

Retrieve the OpenRouter API key from the workshop environment and make it persistent across sessions:

```bash
echo "export OPENROUTER_API_KEY='your_api_key'" >> ~/.bashrc
source ~/.bashrc
```

Verify that the key is set:

```bash
echo $OPENROUTER_API_KEY | head -c 20
```

---

### Step 3 — Launch the Agent UI

Install or upgrade Gradio:

```bash
pip install --upgrade gradio
```

Alternatively:

```bash
python3 -m pip install --upgrade gradio
```

Start the Kubernetes MCP server:

```bash
python3 k8s_mcp_server.py
```

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/ubuntu-cclorchestrator78-agentic-ai-workshop-mcp-k8s-09-10-2026_01_03_PM.png)

In a separate terminal, start the Kubernetes MCP client:

```bash
python3 k8s_mcp_client.py
```

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/ubuntu-cclorchestrator78-agentic-ai-workshop-mcp-k8s-09-10-2026_01_04_PM.png)

The Gradio UI will be available in your browser on **port `7860`**.

---

## Exercises

### Part 1 — Explore Cluster State

Open the Agent UI and ask the agent the following questions. Observe which tools it calls and how it builds its responses.

**1. Check node status**

```text
"How many nodes are in the cluster and what is their status?"
```

**2. List namespaces with running pods**

```text
"List all namespaces that have running pods."
```

**3. Count pods in the default namespace**

```text
"How many total pods are running in the default namespace?"
```

**4. Check deployment replicas**

```text
"Which deployments have fewer ready replicas than desired?"
```

**Reflection Questions**

```text
Which MCP tools were called to answer question 1?
```

```text
Did the agent make multiple tool calls for any single question?
```

```text
How did the LLM decide which tools to call?
```

---

### Part 2 — Deploy a Broken Application

#### Create the Namespace

First, check whether the namespace already exists:

```bash
kubectl get namespace k8s-agent-lab
```

If it does not exist, create it:

```bash
kubectl create namespace k8s-agent-lab
```

#### Deploy a Broken Pod

Create a pod that will crash:

```bash
cat > broken-pod.yaml << 'EOF'
apiVersion: v1
kind: Pod
metadata:
  name: broken-app
  namespace: k8s-agent-lab
spec:
  containers:
  - name: app
    image: python:3.11-slim
    command: ['python', '-c', 'import time; time.sleep(5); exit(1)']
    resources:
      limits:
        memory: '32Mi'
        cpu: '100m'
EOF
```

Apply the configuration:

```bash
kubectl apply -f broken-pod.yaml
```

---

### Part 3 — Diagnose with the Agent

Open the Agent UI and ask the following questions:

**5. Check the pod status**

```text
"What is the status of the broken-app pod in the k8s-agent-lab namespace?"
```

**6. Check namespace events**

```text
"Show me the events for the k8s-agent-lab namespace."
```

**7. Analyze the pod logs**

```text
"Why is the broken-app pod failing? What do the logs say?"
```

**8. Ask for a recommended fix**

```text
"How should I fix this pod?"
```

---

### Part 4 — Verify the Diagnosis

Run the following commands and compare the results with the agent's responses:

```bash
kubectl describe pod broken-app -n k8s-agent-lab
kubectl logs broken-app -n k8s-agent-lab
kubectl get events -n k8s-agent-lab
```

**Success Criteria**

* The agent correctly identifies the pod as `CrashLoopBackOff` or `Error`
* The agent retrieves and interprets the pod logs
* The agent suggests a fix, such as increasing the memory limit or correcting the command
* The agent's response matches the output from `kubectl describe` and `kubectl logs`

---

## Quick Reference

| Question                        | Tool Chain                                      |
| ------------------------------- | ----------------------------------------------- |
| Why is my pod crashing?         | `list_pods` → `get_pod_logs` → `get_events`     |
| Show cluster health             | `list_nodes` → `list_pods` → `list_deployments` |
| What events happened recently?  | `get_events` (per namespace)                    |
| List all services and endpoints | `list_services`                                 |
| What resources are pods using?  | `get_resource_usage`                            |
| Describe a pod in detail        | `describe_pod`                                  |