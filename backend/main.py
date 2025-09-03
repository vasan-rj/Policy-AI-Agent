from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from uuid import uuid4
import os
import shutil
from typing import Dict, List
from document_processor import DocumentProcessor
from agents import MultiAgentWorkflow

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors with agentic RAG fallback
try:
    from document_processor import DocumentProcessor
    doc_processor = DocumentProcessor()
    print("✅ Document processor initialized successfully")
except Exception as e:
    print(f"⚠️  Document processor failed to initialize: {e}")
    doc_processor = None

try:
    from agentic_rag import AgenticRAGWorkflow
    agent_workflow = AgenticRAGWorkflow()
    print("✅ Agentic RAG workflow initialized successfully")
except Exception as e:
    print(f"⚠️  Agentic RAG workflow failed to initialize: {e}")
    print("🔄 Using simple fallback agents")
    try:
        from agents import MultiAgentWorkflow
        agent_workflow = MultiAgentWorkflow()
        print("✅ Simple multi-agent workflow initialized")
    except Exception as e2:
        print(f"⚠️  Simple agents also failed: {e2}")
        from simple_agents import SimpleFallbackWorkflow
        agent_workflow = SimpleFallbackWorkflow()

class QueryRequest(BaseModel):
    question: str
    policy_id: str

class QueryResponse(BaseModel):
    answer: str
    task_type: str
    original_sections: List[Dict]
    status: str

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory policy registry for demo
policy_registry: Dict[str, Dict] = {}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_policy(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:  # Added .txt for testing
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT supported.")
    
    policy_id = str(uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{policy_id}{ext}")
    
    # Save file
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process document: parse, chunk, embed, store in ChromaDB
    if doc_processor:
        try:
            result = doc_processor.process_document(save_path, policy_id)
            
            if result["status"] == "success":
                policy_registry[policy_id] = {
                    "file_path": save_path,
                    "filename": file.filename,
                    "processing_result": result
                }
                
                return {
                    "policy_id": policy_id,
                    "filename": file.filename,
                    "total_chunks": result["total_chunks"],
                    "total_characters": result["total_characters"],
                    "status": "success"
                }
            else:
                raise Exception(result.get('error', 'Unknown processing error'))
        
        except Exception as e:
            print(f"Document processing failed: {e}")
            # Fallback: store without processing
            policy_registry[policy_id] = {
                "file_path": save_path,
                "filename": file.filename,
                "processing_result": {"status": "error", "error": str(e)}
            }
            return {
                "policy_id": policy_id,
                "filename": file.filename,
                "status": "uploaded_without_processing",
                "note": "Document uploaded but advanced processing failed. Basic functionality available."
            }
    else:
        # No document processor available
        policy_registry[policy_id] = {
            "file_path": save_path,
            "filename": file.filename,
            "processing_result": {"status": "no_processor"}
        }
        return {
            "policy_id": policy_id,
            "filename": file.filename,
            "status": "uploaded_basic_mode",
            "note": "Document uploaded in basic mode. Advanced AI features may be limited."
        }

@app.post("/query", response_model=QueryResponse)
async def query_policy(request: QueryRequest):
    if request.policy_id not in policy_registry:
        raise HTTPException(status_code=404, detail="Policy not found.")
    
    try:
        # Use multi-agent workflow to process the query
        result = agent_workflow.process_query(request.policy_id, request.question)
        
        return QueryResponse(
            answer=result["answer"],
            task_type=result["task_type"],
            original_sections=result["original_sections"],
            status=result["status"]
        )
    
    except Exception as e:
        # Fallback response
        return QueryResponse(
            answer=f"I apologize, but I encountered an error processing your question. Error: {str(e)}",
            task_type="error",
            original_sections=[],
            status="error"
        )
