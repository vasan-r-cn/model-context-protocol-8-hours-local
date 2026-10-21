show JSON-RPC and host/client/server communication format in the slides and connect these formats back to the earlier example (vacation planner) for clarity.

add a simple user-facing example (e.g., ticket or vacation booking) before the slide on agents and agent-tool workflow, and explicitly map components of the example to the agent workflow in the slides.

include a diagram of the MCP/server/topology and show how tools (e.g., get interfaces) map to resources or prompts in that topology.

explain the MCP value proposition: how vendor-provided MCP servers remove direct API integration maintenance, and add a slide demonstrating this with a concrete example (e.g., booking.com MCP).


emphasizes teaching to beginners by starting with a simple example before introducing technical concepts, because participants may have zero prior knowledge. He advises using a concrete scenario (e.g., ticket or vacation booking) to explain agent workflows and then unpacking each component. The current state is that trainers will rework slides to introduce examples first, then technical detail.
Sharad Chandra recommends presenting the overall picture first and then drilling down into components like agents and workflows

Troubleshooting architecture demo
Sharad recommends building a troubleshooting IT use-case (e.g., diagnosing slow Webex) that integrates multiple tools and APIs to demonstrate end-to-end architecture. He suggests showing how a UI chat box, a master agent, LLMs, monitoring tools, and ticketing systems interact. The current state is that trainers will craft the troubleshooting use-case to illustrate integrations and responsibilities across components.
Sharad Chandra proposes using a troubleshooting IT example, such as diagnosing slow Webex, to demonstrate integration of tools like ThousandEyes and Splunk.
Sharad Chandra explains that the demo should show a UI chat box connecting to a master agent that sends data to an LLM and interacts with ticketing systems.


Introduce MCP concept
The team discusses introducing MCP (Middleware/Message Control Plane) as a replacement for traditional direct API integrations and clarifies that MCP can communicate via multiple mechanisms, not only APIs. Sharad wants trainers to explain how MCP reduces code churn when third-party applications change. The current state is that MCP will be defined and contrasted with traditional API-based integrations in the slides.
Sharad Chandra asks the team to introduce MCP as an alternative to direct API integrations and to clarify that MCP can communicate through mechanisms beyond APIs.
Sharad Chandra highlights that MCP helps avoid repeated code changes when third-party applications evolve.


Topology and sandbox demo
Sharad explains the need to present the lab topology and sandbox environment showing an MCP server interacting with routers and tools (e.g., get interfaces). He wants the demo to illustrate resources, prompts, and tool calls visually so attendees can picture the flow. The current state is trainers will prepare topology diagrams and a sandbox demo that maps tool calls to MCP behavior.
Sharad Chandra instructs the trainers to show the lab topology and a demo MCP server that talks to routers using example calls like 'get interfaces'.
Sharad Chandra suggests using diagrams to help attendees visualize tools, resources, and prompt interactions in the sandbox.


MCP provider example
Sharad asks trainers to include a scenario where external providers (e.g., airline.com or booking.com) expose MCP servers so consumers need not handle API changes. He wants the narrative to show how relying on provider MCPs simplifies integration and maintenance. The current state is that slides will incorporate provider MCP examples to illustrate decoupling benefits.
Sharad Chandra asks the team to present a scenario in which external providers supply MCP servers so consumers avoid handling shifting APIs.
Sharad Chandra emphasizes that this scenario demonstrates reduced dependency on code updates when third-party services change.
Technical details and communication modes
Sharad directs the team to cover technical formats (e.g., JSON-RPC) and client-host-server models, explaining that host and server can be local or remote and that communication may occur over stdio, streaming, or HTTP. He stresses connecting these technical details back to the running example so learners see how requests flow. The current state is that trainers will add technical examples and clarify communication modalities.
Sharad Chandra instructs the trainers to show JSON-RPC examples and explain host-client-server roles in the topology.
Sharad Chandra clarifies that MCP communications can use standard input/output, streamable protocols, or HTTP, and that examples should map to the vacation planner scenario.
MCP inspector/demo timing
The team agrees to show the MCP inspector (debugger) at the end of the session after attendees understand tool capabilities and message exchange patterns. Sharad argues the inspector is most valuable once learners have context from the end-to-end flow and the lab documents. The current state is the inspector will be scheduled for the end of the lab portion and demonstrated after code and documents are reviewed.
Sharad Chandra recommends showing the MCP inspector and debugger at the end of the session so attendees know what they are viewing.
Vasan R confirms the plan to present the inspector after the documentation review and lab walkthrough.
Lab exercise and code distribution
Sharad outlines a lab where trainers type commands (e.g., get interfaces) and then break down how each component produces the result; he intends to provide lab code and documentation as example MCP server code for attendees to use as a starting point. He clarifies the code is an instructional example, not an official Cisco standard. The current state is that the team will prepare and distribute the lab documents and code samples.
Sharad Chandra plans a lab exercise that demonstrates typing 'get interface' and then explains where each piece of functionality sits.
Sharad Chandra states he will provide example MCP server code and documentation as a starting point, noting it is not an official Cisco standard.

