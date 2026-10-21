# Multi-Agent Orchestration — Testing & Validation

## Objective

Validate that:

1. The application starts.
2. Routing selects the intended domain.
3. The correct specialist agent executes.
4. Required tools/APIs are reachable.
5. Results reach the UI.
6. Multi-domain requests behave according to the implemented graph.
7. ServiceNow integration works after instructor-assisted setup.

## 1. Start the Application

```bash
cd ~/agentic-ai-workshop/multi_agent_langgraph/
```

```
sudo apt install python3.10-venv
```
```
python3 -m venv .venv
```
```
source .venv/bin/activate
```
```
pip install -r requirements.txt
```

Update .env by adding VMANAGE_HOST and LANGSMITH_API_KEY

```
vi .env
```
# ThousandEyes Agent Installation – Participant Machine(**linuxdesktop64**)


## 
### Please ignore the **HOST_NAME** change and **ThousandEyes installation** steps if they have already been completed.

Each participant must assign a unique hostname to their machine. Replace <YOUR_UNIQUE_HOSTNAME> with the hostname
## 1. Set the hostname

For Participant 1:

```bash
sudo hostnamectl set-hostname <YOUR_UNIQUE_HOSTNAME>
```

For Participant 2:

```bash
sudo hostnamectl set-hostname te-agent-user2
```

Continue similarly for the remaining participants.

## 2. Update `/etc/hosts`

Run:

```bash
sudo sed -i 's/^127\.0\.0\.1.*/127.0.0.1\t'"$(hostname)"'/' /etc/hosts
```

This updates the local hostname entry so the new hostname resolves correctly.

## 3. Verify the hostname

Run:

```bash
hostname
hostnamectl
```

Expected for Participant 1:

```
<YOUR_UNIQUE_HOSTNAME>
```

Look for:

```
Static hostname: <YOUR_UNIQUE_HOSTNAME>
```

## 4. Verify `/etc/hosts`

Run:

```bash
grep '127.0.0.1' /etc/hosts
```

Expected:

```text
127.0.0.1    <YOUR_UNIQUE_HOSTNAME>
```

## 5. Download the ThousandEyes Agent installer

```bash
curl -Os https://downloads.thousandeyes.com/agent/install_thousandeyes.sh
```

Verify:

```bash
ls -l install_thousandeyes.sh
```

## 6. Make the installer executable

```bash
chmod +x install_thousandeyes.sh
```

## 7. Install the ThousandEyes Agent

```bash
sudo ./install_thousandeyes.sh -b yv6buqseehhccf35n33sf6rkf3xt4fb3
```

> **Security:** Do not commit the installation token to Git or share it publicly. If a real production token has been exposed, rotate it.

## 8. Verify the ThousandEyes Agent

```bash
sudo systemctl status te-agent
```

Expected:

```text
Active: active (running)
```

Also verify:

```bash
sudo systemctl is-active te-agent
```

Expected:

```text
active
```

## 9. Verify the hostname again

```bash
hostname
```

Expected:

```
<YOUR_UNIQUE_HOSTNAME>
```

The ThousandEyes agent should now register using this hostname.

# If the Agent Was Already Installed

If ThousandEyes was installed **before** changing the hostname, the agent may retain the old hostname or identity.

First try:

```bash
sudo systemctl restart te-agent
```

Then check:

```bash
sudo systemctl status te-agent
```

If it still appears with the old hostname, follow your organization's ThousandEyes procedure to uninstall and reinstall the agent.


## Expected Final State

Each participant's machine should have:

- A unique hostname (`te-agent-user1`, `te-agent-user2`, etc.)
- The hostname correctly mapped in `/etc/hosts`
- ThousandEyes Agent installed
- ThousandEyes Agent service running
- Agent registered using the correct hostname


```
python3 app.py
```
Confirm:

- no startup exception
- Gradio UI is available
- prompts can be submitted


### You can see the Gradio link like this. Please open the Chrome browser, copy the link, and paste it into a new tab.


![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/01_05_16.jpg)


### **Observability from Gradio and LangSmith **

**SD-WAN**

Gradio

```
List my inventory details
```
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/e5a19254-d534-461c-89bb-9b33c7ea655a.PNG)


### You can log in to LangSmith using your credentials and trace it there.


![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-08-10%20121413.png)

---
**ThousandEyes**

```
Give the available test list of dns-servers of ThousandEyes agent
```

Gradio
![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/403f5e48-fc97-46f9-bb07-1eff873244af.PNG)

You can log in to LangSmith using your credentials and trace it there.

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-08-10%20122021.png)
---
**SD-WAN and ThousandEyes**

```
Investigate the performance issue.
Check the SD-WAN status, investigate the ThousandEyes path
```


Gradio

![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/915dd421-cd95-445b-906a-790fc3063897.PNG)


You can log in to LangSmith using your credentials and trace it there.


![](https://sdcloud-imgs.s3.amazonaws.com/sandboxes/Screenshot%202026-08-10%20122823.png)

---
## 2. SD-WAN Agent Test

Use a supported SD-WAN prompt, for example:

```text
Show me the SD-WAN device inventory.
```

Validate:

```text
Prompt → Router → SD-WAN Agent → SD-WAN API/tool → Response
```

Record:

- selected agent
- API/tool used
- result
- errors, if any

## 3. ThousandEyes Agent Test

Use the documented example:

```text
Get path visualization details for test_id 2637213.
```

or:

```text
Give the available test list of dns-server of ThousandEyes agent.
```

Expected result: ThousandEyes information is returned from the configured integration.

## 4. ServiceNow Agent Test

Use a known incident:

```text
Get details for ServiceNow incident INC0017997.
```

Expected flow:

```text
Prompt → Router → ServiceNow Agent → ServiceNow API → Incident response
```

Use an incident number that actually exists in the workshop instance if the documented example is unavailable.

## 5. Routing Tests

### SD-WAN

```text
Show me the SD-WAN tunnel status.
```

Expected:

```text
Router → SD-WAN Agent
```

### ThousandEyes

```text
Show me the ThousandEyes path for test 2637213.
```

Expected:

```text
Router → ThousandEyes Agent
```

### ServiceNow

```text
Get details for ServiceNow incident INC0017997.
```

Expected:

```text
Router → ServiceNow Agent
```

## 6. Multi-Agent Test

Use a cross-domain operational question:

```text
Investigate the network performance issue.
Check the SD-WAN status, investigate the ThousandEyes path,
and check whether there is a related ServiceNow incident.
```

Observe the workflow rather than only the final answer:

```text
User
 |
 v
Planner / Router
 |
 +---- SD-WAN
 |
 +---- ThousandEyes
 |
 +---- ServiceNow
 |
 v
Shared Context / State
 |
 v
Final Response
```

**Important:** If the current `multi_agent_v2` graph only supports single-agent routing, do not claim that parallel or sequential multi-agent execution is already implemented. Use the scenario as an instructor-led extension/demo.

## 7. Negative Tests

### Unknown intent

```text
What is the weather on Mars?
```

Observe how unsupported intent is handled.

### Incomplete request

```text
Check the incident.
```

Observe whether additional information is required.

### Invalid ServiceNow incident

```text
Get details for ServiceNow incident INC0000000.
```

Observe controlled API/error handling.

### Invalid ThousandEyes test

Use an invalid test ID and verify that the API error is handled without crashing the application.

## 8. Logging Validation

Keep the application terminal visible.

Correlate:

```text
Request
 ↓
Routing
 ↓
Agent
 ↓
Tool/API
 ↓
Result
 ↓
Final Response
```

The workshop material identifies centralized logging as useful for execution visibility, debugging and error tracing.

## 9. ServiceNow Instructor-Assisted Validation

Validate in stages:

### Stage 1 — Agent

Confirm ServiceNow can retrieve an incident.

### Stage 2 — Graph Node

Confirm the ServiceNow agent is connected to its LangGraph node.

### Stage 3 — Registration

Confirm the node is registered in the graph.

### Stage 4 — Routing

Confirm ServiceNow prompts reach the ServiceNow node.

### Stage 5 — End-to-End

Run:

```text
Get details for ServiceNow incident INC0017997.
```

Then run the broader cross-domain scenario.

## 10. Final Validation Checklist

| Test | Expected Result | Status |
|---|---|---|
| Application starts | `app.py` runs without errors | ☐ |
| Gradio UI | UI accessible | ☐ |
| SD-WAN prompt | SD-WAN agent responds | ☐ |
| ThousandEyes prompt | ThousandEyes agent responds | ☐ |
| ServiceNow prompt | ServiceNow agent responds | ☐ |
| SD-WAN routing | Correct graph path | ☐ |
| ThousandEyes routing | Correct graph path | ☐ |
| ServiceNow routing | Correct graph path | ☐ |
| Invalid request | Controlled handling | ☐ |
| API failure | Controlled error | ☐ |
| Multi-domain request | Behavior matches implemented graph | ☐ |
| Logs | Workflow is traceable | ☐ |

## 11. Instructor Acceptance Criteria

Participants should be able to explain:

```text
UI
 ↓
Orchestrator
 ↓
+-- SD-WAN Agent
+-- ThousandEyes Agent
+-- ServiceNow Agent
 ↓
Shared State / Graph
 ↓
Response
```

And:

```text
Prompt
 → Route
 → Execute specialist
 → Update state
 → Return response
```

## 12. Extension Pattern

The workshop material describes adding a new agent using:

```text
Create Agent
   ↓
Create Agent Node
   ↓
Register Node in Graph
   ↓
Update Router / Intent
   ↓
Test through Gradio
```

Ask the class:

> If we add a Splunk agent, what needs to change?

Expected discussion:

- specialist agent
- graph node
- graph registration
- routing/intent handling
- shared state if new context must travel through the workflow
- independent testing
- end-to-end testing