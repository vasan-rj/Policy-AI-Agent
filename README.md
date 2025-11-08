# Document Guardian

This project is a local-first, AI-powered document analysis and question-answering tool. It supports any document type including finance, healthcare, legal, technical documents, and more. Uses FastAPI, LangChain, LangGraph, Ollama, ChromaDB, and React, all orchestrated with Docker Compose.

## Features

- **Multi-Document Support**: Finance, healthcare, legal, technical, policy documents, and more
- **Intelligent Analysis**: Automatic document type detection and specialized analysis
- **4 Agent Types**: 
  - **Explanation Agent**: Simplifies complex content into easy-to-understand language
  - **Analysis Agent**: Provides detailed risk assessment and compliance analysis
  - **Extraction Agent**: Finds specific facts, numbers, dates, and data points
  - **Summary Agent**: Creates comprehensive overviews and executive summaries
- **Conversation Memory**: Maintains context across questions for natural dialogue
- **Local-First**: All processing happens locally for maximum privacy

## Getting Started

1. Clone the repo and navigate to the `infrastructure` folder:
   ```bash
   git clone <repo-url>
   cd Document-Guardian/infrastructure
   ```
2. Build and start all services:
   ```bash
   docker-compose up --build
   ```
3. Access the frontend at http://localhost:3000 and backend API at http://localhost:8001

## API Endpoints

- **POST /upload**: Upload any document (PDF/DOCX/TXT) with document type specification
- **POST /query**: Ask questions about uploaded documents
- **POST /analyze**: Get comprehensive analysis of documents
- **GET /health**: Check service status
- **GET /health/ollama**: Check AI model availability

## Document Types Supported

- **finance**: Financial reports, statements, contracts
- **healthcare**: Medical records, policies, research papers  
- **legal**: Contracts, policies, legal documents
- **technical**: Technical documentation, manuals, specifications
- **general**: Any other document type

## Project Structure
- `backend/`: FastAPI app, multi-agent logic, document processing
- `frontend/`: React app for UI
- `infrastructure/`: Docker Compose and orchestration

## Example Usage

1. Upload a financial report with document_type="finance"
2. Ask: "What are the key financial metrics?"
3. Ask: "What was my last question?" (tests memory)
4. Ask: "Analyze the financial risks in this report"

---

For more details, see `claude .md`.
