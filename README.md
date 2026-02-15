# Enterprise Access Portal

**An AI-powered, multi-agent conversational portal that unifies enterprise application access management.**

[![Built with Neuro SAN](https://img.shields.io/badge/Built%20with-Neuro%20SAN-blue)](https://github.com/cognizant-ai-lab/neuro-san)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE.txt)

Enterprise Access Portal is a production-grade reference implementation built on [Neuro SAN](https://github.com/cognizant-ai-lab/neuro-san) that demonstrates how multi-agent orchestration can transform enterprise IT operations. Instead of navigating fragmented portals and manual approval chains, employees interact with a single conversational interface to request access, resolve issues, and get answers -- all through natural language.

---

## Why This Matters

### The Problem

Enterprise employees waste hours navigating fragmented access systems -- different portals, approval chains, knowledge bases, and ticketing workflows for every application. IT teams drown in repetitive tickets that follow the same patterns but require manual processing every time.

### The Solution

A single AI-powered conversational portal that:

- Handles access requests across multiple applications through one interface
- Automates the full validation pipeline (identity, training, policy compliance)
- Creates and verifies ServiceNow tickets without leaving the conversation
- Debugs access issues via an external agent network
- Answers FAQs from a built-in knowledge base of 15+ ServiceNow topics

---

## Key Features

- **Multi-application support** -- Dataiku, LMS, DI_CAMCOS, with an extensible architecture for adding more
- **Automated validation pipeline** -- Identity verification, training requirements check, training completion verification, and policy compliance -- all executed automatically
- **ServiceNow integration** -- Ticket creation, verification, and status tracking (mock mode included for development)
- **Incident debugging** -- Routes access issues to an external agent network for automated analysis and resolution
- **Knowledge base** -- 15+ ServiceNow FAQs covering group management, application portfolio, service requests, and more
- **Dynamic prompting** -- Agents fetch their instructions at runtime from the MCP server, enabling prompt updates without redeployment
- **Secure context handling** -- Sensitive user data (IDs, credentials) flows through `sly_data`, never exposed in agent conversations

---

## Architecture Overview

```
                         User (Web UI / Slack / CLI)
                                    |
                    +-------------------------------+
                    | access_request_orchestrator   |
                    |         (Top-level Agent)     |
                    +-------------------------------+
                     /        |          |          \
                    /         |          |           \
     +----------------+ +----------+ +----------+ +------------------+
     | validation     | | ons      | | access   | | knowledge_base   |
     | _service (MCP) | | _agent   | | _issue   | | _agent           |
     +----------------+ +----------+ | _agent   | +------------------+
     | user_verify    | | ticket   | +----------+ | 15+ ServiceNow   |
     | training_reqs  | | verify   |  | issue   | | FAQs inline      |
     | training_comp  | | ticket   |  | ticket  | +------------------+
     | approvals_req  | | create   |  | create  |
     | prompt_retrieve| +----------+  | incident|
     +----------------+               | debug   |
            ^                         +----+----+
            |                              |
    +-------+--------+          +---------+---------+
    | MCP Server     |          | External Agent    |
    | (FastMCP)      |          | Network (API)     |
    +----------------+          +-------------------+
```

**access_request_orchestrator** -- The top-level agent that greets users, determines intent, and routes to the appropriate specialist. It fetches application-specific prompts dynamically from the MCP server.

**validation_service (MCP)** -- Connects to the FastMCP server over Streamable HTTP. Provides five tools: user verification, training requirements lookup, training completion check, policy compliance check, and prompt retrieval.

**ons_agent** -- Manages the ServiceNow ticket lifecycle. Verifies existing tickets or creates new ones for access requests.

**access_issue_agent** -- Handles troubleshooting for existing access problems. Creates incident tickets and delegates to an external debugging agent network for automated analysis.

**knowledge_base_agent** -- Answers frequently asked questions about ServiceNow processes, group management, application portfolio management, and more.

---

## How It Works

### Multi-Agent Orchestration (AAOSA)

The portal uses the **Ask, Analyze, Orchestrate, Synthesize, Answer** pattern from Neuro SAN. When a user inquiry arrives:

1. The orchestrator **asks** its downstream agents which parts of the inquiry they can handle
2. It **analyzes** their responses to determine the best routing
3. It **orchestrates** by gathering requirements and delegating work
4. It **synthesizes** the results from all participating agents
5. It **answers** the user with a unified response

This means a single user message like *"I need Dataiku access for PROD"* automatically triggers identity verification, training checks, policy validation, and ticket creation -- all coordinated across multiple specialized agents.

### MCP Integration

The validation service runs as a standalone [FastMCP](https://github.com/modelcontextprotocol/python-sdk) server (`servers/mcp/mcp_server.py`) exposing five tools over Streamable HTTP:

| MCP Tool | Purpose |
|---|---|
| `user_verification` | Validates user identity against the central users table |
| `training_requirements` | Returns required training for a given environment |
| `training_completions` | Checks if a user completed specific training |
| `approvals_required` | Checks policy compliance for environment + access type |
| `prompt_retriever` | Serves dynamic agent instructions by agent name and use case |

The `MCPToolAdapter` (`coded_tools/enterprise_access_portal/mcp/mcp_tool_adapter.py`) bridges Neuro SAN's `CodedTool` interface with the MCP server using `langchain-mcp-adapters`, allowing any agent in the network to call MCP tools seamlessly.

### Dynamic Prompting

Agents don't have all their instructions hardcoded in the HOCON registry. Instead, they call `prompt_retriever` at runtime to fetch context-specific instructions from the MCP server. For example, the orchestrator fetches different prompts for Dataiku vs. LMS access flows. This enables:

- Updating agent behavior without redeploying the agent network
- Application-specific workflows from a single agent definition
- Centralized prompt management in `servers/mcp/prompt_templates.py`

### ServiceNow Integration

The ONS (ServiceNow) agent supports two operations:

- **Ticket verification** -- Validates existing SNOW ticket numbers (`ons_ticket_verification_tool`)
- **Ticket creation** -- Generates new tickets for approved access requests (`ons_ticket_creator_tool`)

Both tools ship with mock implementations for development and demo use. To connect to a real ServiceNow instance, configure the ServiceNow environment variables in your `.env` file.

### External Agent Network (Incident Debugging)

When a user reports an access issue, the `access_issue_agent` creates an incident ticket and dispatches it to an external debugging agent network via HTTP API. This demonstrates Neuro SAN's ability to integrate with agent systems outside its own network. The tool includes graceful fallback responses when the external network is unavailable.

### Secure Context (sly_data)

Sensitive user information (User ID, Dataiku ID, employee details) is passed through Neuro SAN's `sly_data` mechanism. This data:

- Flows alongside the conversation but is **never visible** in agent prompts or LLM context
- Is available to `CodedTool` implementations for validation calls
- Prevents sensitive data from leaking into conversation logs or LLM providers

---

## Project Structure

```
enterprise-access-portal/
|-- registries/
|   |-- manifest.hocon                  # Declares active agent networks
|   |-- enterprise_access_portal.hocon  # Agent network definition (agents, tools, routing)
|
|-- servers/
|   |-- mcp/
|   |   |-- mcp_server.py              # FastMCP server (Streamable HTTP)
|   |   |-- tool_functions.py          # MCP tool implementations (sly_data-aware)
|   |   |-- prompt_templates.py        # Dynamic prompt templates for all agents
|   |-- neuro_san/                     # Neuro SAN server wrapper
|   |-- a2a/                           # Agent-to-Agent protocol server
|
|-- coded_tools/enterprise_access_portal/
|   |-- mcp/
|   |   |-- mcp_tool_adapter.py        # Bridges Neuro SAN CodedTool <-> MCP server
|   |-- tools/
|   |   |-- ons_ticket_creator_tool.py       # Mock ServiceNow ticket creation
|   |   |-- ons_ticket_verification_tool.py  # Mock ticket verification
|   |   |-- issue_creator_tool.py            # Incident ticket creation
|   |   |-- incident_debugging_agent_tool.py # External agent network integration
|   |   |-- knowdocs/                        # Knowledge base data files
|   |       |-- users.md                     # User identity table
|   |       |-- training_requirements.md     # Training requirements by environment
|   |       |-- training_completions.md      # Training completion records
|   |       |-- access_policies.md           # Access policy matrix
|
|-- mcp/
|   |-- mcp_info.hocon         # External MCP server configurations
|
|-- deploy/                    # Docker deployment files
|-- tests/                     # Unit and integration tests
|-- run.py                     # Application entry point
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- An LLM API key or local LLM model

### Installation

```bash
# Clone the repository
git clone https://github.com/M-Elsaied/enterprise-access-portal.git
cd enterprise-access-portal

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set your OpenAI API key
# OPENAI_API_KEY="your-key-here"
```

### Running the MCP Server

The MCP server must be running before starting the agent network:

```bash
cd servers/mcp
python mcp_server.py
```

The server starts on `http://localhost:8000/mcp/` using Streamable HTTP transport.

### Running the Application

In a separate terminal:

```bash
python run.py
```

This starts the Neuro SAN server and loads the `enterprise_access_portal` agent network. You can then interact through the Web UI, Slack, or CLI depending on your configuration.

---

## Configuration

### Key Environment Variables

| Variable | Description | Default |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o | Required |
| `NEURO_SAN_SERVER_HOST` | Neuro SAN server hostname | `localhost` |
| `NEURO_SAN_SERVER_HTTP_PORT` | Neuro SAN HTTP port | `8080` |
| `NEURO_SAN_WEB_CLIENT_PORT` | Web client port | `5003` |
| `INCIDENT_DEBUG_API_URL` | External debugging agent network URL | Optional |
| `THINKING_FILE` | Path for agent thinking file | `/tmp/agent_thinking.txt` |

### Adding a New Application

To add support for a new application:

1. **Add prompt templates** in `servers/mcp/prompt_templates.py` -- add a new key under `access_request_orchestrator_agent` and `ons_agent` dictionaries
2. **Update knowdocs** in `coded_tools/enterprise_access_portal/tools/knowdocs/` -- add the application's training requirements, policies, and user mappings
3. **Update the orchestrator greeting** in `registries/enterprise_access_portal.hocon` to list the new application
4. Restart the MCP server and agent network

---

## Built With

- [Neuro SAN](https://github.com/cognizant-ai-lab/neuro-san) -- Multi-agent orchestration framework (AAOSA pattern)
- [FastMCP](https://github.com/modelcontextprotocol/python-sdk) -- Model Context Protocol server
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters) -- MCP client integration

---

## License

This project is licensed under the Apache License 2.0 -- see [LICENSE.txt](LICENSE.txt) for details.

## Acknowledgments

- Built on [Neuro SAN Studio](https://github.com/cognizant-ai-lab/neuro-san-studio) by Cognizant AI Lab
- Part of the [Neuro SAN Studio Community Projects](https://github.com/cognizant-ai-lab/neuro-san-studio?tab=readme-ov-file#community-projects)
