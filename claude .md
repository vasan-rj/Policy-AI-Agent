Project: Privacy Guardian
1. Introduction
The objective of the "Privacy Guardian" project is to build an AI-powered, local-first compliance and transparency tool. This application will bridge the critical gap between complex legal privacy policies and user-friendly clarity. By leveraging the gpt-oss open-source models, we will create a system that can ingest and analyze legal documents offline, translate them into plain language for users, and provide a compliance checklist for app developers. The primary use case for this MVP is a "Lungs Healthcare App," focusing on user trust and regulatory adherence. The core tech stack for this project will include Python with FastAPI, LangChain, LangGraph, Ollama, and ChromaDB, all orchestrated with Docker Compose.

2. High-Level Design
The system is designed as a modular, local-first application using a microservices-style architecture with separate frontend and backend containers. This approach ensures a clean separation of concerns, simplifies deployment, and allows for isolated development of each component. The entire system is orchestrated using Docker Compose.

High-Level Architecture Diagram
graph TD
    subgraph "Local User Machine"
        subgraph "Frontend Container"
            UI[User Interface]
        end
        subgraph "Backend Container"
            APIGateway(API Gateway & Agent Supervisor)
            subgraph "LangGraph Agent System"
                subgraph "Specialized Agents"
                    AgentA(Policy Analyst Agent)
                    AgentB(Compliance Expert Agent)
                    AgentC(Translator Agent)
                end
            end
            Preprocessor(Document Preprocessor)
        end
        subgraph "Data Services"
            VectorDB(Vector Database - ChromaDB)
        end
        subgraph "LLM Inference"
            Ollama(Ollama Daemon)
        end

        UI -- HTTP Requests --> APIGateway
        APIGateway -- Ingests & processes requests --> Preprocessor
        Preprocessor -- Embeddings & Storage --> VectorDB
        APIGateway -- Orchestrates Task --> AgentA
        APIGateway -- Orchestrates Task --> AgentB
        APIGateway -- Orchestrates Task --> AgentC
        AgentA & AgentB & AgentC -- Inference Request --> Ollama
        Ollama -- LLM Response --> AgentA & AgentB & AgentC
        AgentA & AgentB & AgentC -- Generated Content --> APIGateway
        APIGateway -- JSON Response --> UI
    end

3. Low-Level Design
A. Backend Service Container (privacy-guardian-backend)
This container will be the brain of the application. It hosts the RAG pipeline, the multi-agent logic, and the local inference engine.

Technology Stack: Python with a web framework like FastAPI or Flask. The AI agent workflow will be built using LangGraph.

Dependencies: LangChain, LangGraph, Ollama, ChromaDB, SentenceTransformers.

Dockerization: A Dockerfile will be created to set up the Python environment, install dependencies, and run the FastAPI server.

REST API Endpoints:

POST /upload: Accepts a policy document (PDF/DOCX). Triggers the ingestion and RAG pipeline.

POST /query: Accepts a user question and a policy ID. Initiates the multi-agent process and returns a generated response.

GET /health: A simple endpoint to check the service's status.

State Management: The LangGraph framework's state-based architecture will be utilized. A shared, mutable state dictionary will be passed between agents, allowing each agent to read from and write to it. This enables the output of one agent (e.g., retrieved context) to be seamlessly used as the input for another (e.g., the prompt for the LLM).

B. Frontend Service Container (privacy-guardian-frontend)
This container will provide the user interface.

Technology Stack: React, Angular, or a lightweight HTML/JS frontend.

Dependencies: A library for making API calls (fetch or axios).

Dockerization: A Dockerfile will be created to serve the static frontend files (e.g., using Nginx). It will be configured to communicate with the backend container.

C. Data & LLM Services
These services will run as separate containers, managed by Docker Compose for persistence and resource isolation.

ollama container: This will run the Ollama daemon. We will use the ollama/ollama official Docker image. This container will pre-pull the gpt-oss-20b model to ensure it's ready for local inference.

chroma container: This will run the ChromaDB vector database, ensuring that the indexed data is persistent even if the other containers are restarted.

Docker Compose for Orchestration
We will use a docker-compose.yml file to define and run the multi-container application with a single command. This file will define the backend, frontend, ollama, and chroma services, configure their networking, and manage persistent volumes for the models and vector database.

Multi-Agent Workflow Low-Level Diagram (Mermaid)
flowchart TD
    subgraph "LangGraph Workflow"
        Start(User Query) -- "Assign Task" --> Supervisor[Supervisor Agent]
        Supervisor -- "If 'Translation' Task" --> Translator[Translator Agent]
        Supervisor -- "If 'Compliance' Task" --> Analyst[Policy Analyst Agent]
        Translator -- "Retrieve relevant policy chunks" --> Retriever(RAG Retriever)
        Analyst -- "Retrieve relevant policy chunks" --> Retriever
        Retriever -- "Returns context" --> Translator
        Retriever -- "Returns context" --> Analyst
        Translator -- "Generate plain-english answer" --> Output(Final Output)
        Analyst -- "Identify compliance risks" --> Expert[Compliance Expert Agent]
        Expert -- "Generate checklist & fixes" --> Output
        Output -- "Return to UI" --> End
    end

4. MVP Use Cases (Demonstration Flow)
Use Case 1: Plain-English Translation for Patients
User Action: A user (a patient) uploads the "Lungs Healthcare App" privacy policy document via the frontend UI.

System Action: The document is sent to the backend's /upload endpoint. The Document Preprocessor and RAG pipeline components handle the chunking, embedding, and storage in ChromaDB.

User Action: The user asks a question in a natural language chat interface: "Who can see my spirometry test results?" or "How long is my medical history stored?"

System Action: The query is sent to the Supervisor Agent. It routes the task to the Translator Agent. The Translator Agent retrieves the most relevant chunks from the policy via the RAG Retriever and uses a comprehensive prompt for the gpt-oss-20b model.

LLM Action: The model generates a response based only on the provided context, translating the legal jargon into a clear, concise answer.

Demo Output: The UI displays the plain-language answer and highlights the original text in the privacy policy for transparency.

Use Case 2: Compliance Checklist for App Developers
User Action: An app developer uploads the "Lungs Healthcare App" privacy policy.

System Action: The document is indexed as before.

User Action: The developer asks a targeted question: "Is my policy compliant with GDPR and HIPAA?" or "What are the data retention rules for geo-location data?"

System Action: The query is sent to the Supervisor Agent, which routes the task to the Policy Analyst Agent. This agent retrieves policy chunks and passes them to the Compliance Expert Agent. The Compliance Expert Agent then generates a structured, actionable response with a checklist of gaps, risks, and suggestions for improvement.

LLM Action: The model generates a structured, actionable response. This could be a list of gaps, potential risks, and concrete suggestions for improvement.

Demo Output: The UI displays the checklist, highlighting specific policy sections that may need to be updated to align with the specified regulations.

5. Timeline & Next Steps
This project is ambitious but achievable within the 15-day timeframe. We recommend a phased approach:

Days 1-3: Team setup, environment configuration (Docker, Ollama, ChromaDB), and initial RAG pipeline build.

Days 4-7: Core multi-agent logic development using LangGraph, initial prompt engineering, and building a basic proof-of-concept UI.

Days 8-12: Implementing the two key MVP use cases with polished UI/UX, and refining the model's responses.

Days 13-15: Final polish, preparing the demo video, and drafting the project's documentation and pitch.

By following this plan, your team will be able to deliver a functional, impressive, and highly relevant project that showcases the power of the gpt-oss models in a privacy-centric, real-world application.