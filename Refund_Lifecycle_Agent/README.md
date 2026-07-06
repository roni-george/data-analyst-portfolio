###  Overview
This project introduces a highly resilient, autonomous AI agent architecture designed to completely automate an e-commerce platform's refund lifecycle. Developed following the engineering principles covered in the Kaggle 5-Day AI Agents Intensive Workshop (June 2026), the system eliminates manual email triage by reading incoming customer requests, securely querying local records, validating claims against a dynamic store policy using Retrieval-Augmented Generation (RAG), and executing automated communication pipelines.

###  Core Architectural Innovation: Dual-Loop State Protection
A major pitfall in standard email-processing bots is state collision—where a customer reply is treated as a brand-new inquiry, causing fragmented data and broken processing trails. 

To solve this, this application implements a structured dual-loop system backed by a local transactional SQLite database:
1. **The Ingestion & Safeguard Loop (`process_customer_replies`)**: Scans unread emails first. If a message belongs to a customer with an active `Incomplete Data` record in the database, the agent extracts the missing details (e.g., an order number or item condition), merges them into the existing file context, runs a policy audit, and clears the ticket. If no matching incomplete file is found, it preserves the email's `UNSEEN` flag and passes it downstream unharmed.
2. **The Discovery Loop (`process_new_requests`)**: Ingests completely fresh emails, extracts core metadata using structured schema validation via Gemini, and flags missing fields automatically while generating clear customer notification drafts.

###  RAG Grounding & Validation Shield
To guarantee strict compliance with company guidelines, the underlying Gemini 2.5 Flash model does not rely on its public training weights to approve or deny claims. Instead, the application reads a local corporate asset (`refund_policy.txt`) at runtime and injects it directly into the prompt template. Explicit prompt constraints act as an engineering guardrail, preventing LLM hallucinations, ensuring zero edge-case assumptions, and strictly enforcing corporate procedures.

###  Technical Stack
* **Language/Runtime:** Python 3.14+ managed via Astral `uv` for ultra-fast, deterministic package management.
* **Web Gateway:** FastAPI & Uvicorn (configured with an asynchronous application lifespan loop for continuous local 1-minute automation sweeps).
* **Data Persistence:** Relational SQLite schema for transaction isolation and state management.
* **Model Model:** Gemini 2.5 Flash.
