# Agent Development Kit (ADK) Workshop

Welcome to the ADK Workshop! This repository contains hands-on examples and exercises to help you build, run, and deploy AI agents using the Google Agent Development Kit.

## Workshop Structure

### Module 1: Building Your First Agent
**Goal:** Create a specialized Flight Agent that can search and book flights.
- **Source Code:** [`flight_agent/`](flight_agent/)
- **Key Concepts:** `LlmAgent`, Tools (`search_flights`, `book_flight`), Instructions.

### Module 2: Multi-Agent Systems
**Goal:** Build a Travel Coordinator that orchestrates multiple specialized agents (Flight & Hotel).
- **Source Code:** [`multi_agent/`](multi_agent/)
- **Key Concepts:** `sub_agents`, Delegation, Orchestration.

### Module 3: Running Your Agents
Learn the different ways to execute and interact with your agents.

1.  **Terminal Execution (`adk run`)**
    - Interact directly via the command line.
    - **Example:** [`run_terminal/`](run_terminal/)
    - **Run:** `adk run workshop/run_terminal`

2.  **API Server (`adk api_server`)**
    - Serve your agent as a REST API for integration.
    - **Example:** [`run_api/`](run_api/)
    - **Run:** `adk api_server workshop/run_api`

3.  **Programmatic Execution (Python)**
    - Embed agents directly into your Python code.
    - **Example:** [`run_programmatic/`](run_programmatic/)
    - **Run:** `python3 workshop/run_programmatic/main.py`

### Module 4: Deployment
**Goal:** Deploy your Multi-Agent System to production using Vertex AI Agent Engine.
- **Source Code:** [`agent_engine/`](agent_engine/)
- **Key Concepts:** `adk deploy`, Cloud Deployment, Scalability.
- **Deploy Command:** 
    ```bash
    adk deploy agent_engine workshop/agent_engine \
        --project sascha-playground-doit \
        --region us-central1 \
        --display_name "Multi-Agent System"
    ```

## Resources
- **Documentation:** See the `workshop-documents/` folder for PDF guides.
- **Reference:** `llms-full.txt` contains the full text of the workshop materials.
