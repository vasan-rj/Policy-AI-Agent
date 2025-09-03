# Privacy Guardian

This project is a local-first, AI-powered compliance and transparency tool for privacy policies. It uses FastAPI, LangChain, LangGraph, Ollama, ChromaDB, and React, all orchestrated with Docker Compose.

## Getting Started

1. Clone the repo and navigate to the `infrastructure` folder:
   ```bash
   git clone <repo-url>
   cd Privacy-guardian/infrastructure
   ```
2. Build and start all services:
   ```bash
   docker-compose up --build
   ```
3. Access the frontend at http://localhost:3000 and backend API at http://localhost:8000

## Project Structure
- `backend/`: FastAPI app, multi-agent logic, document processing
- `frontend/`: React app for UI
- `infrastructure/`: Docker Compose and orchestration

## Next Steps
- Implement document parsing, chunking, embedding, and ChromaDB storage in backend
- Integrate LangGraph multi-agent workflow and connect to Ollama for LLM inference
- Enhance frontend to highlight original policy text in answers

---

For more details, see `claude .md`.
