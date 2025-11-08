from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from uuid import uuid4
import os
import shutil
from typing import Dict, List, Optional
from datetime import datetime
from document_processor import DocumentProcessor
from agents import MultiAgentWorkflow
from auth_models import UserAuthManager

app = FastAPI()

# Security
security = HTTPBearer()

# Initialize authentication manager
auth_manager = UserAuthManager()

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
    from agentic_rag import AgenticRAGWorkflow, test_ollama_connection
    if test_ollama_connection():
        agent_workflow = AgenticRAGWorkflow()
        print("✅ Agentic RAG workflow with Ollama initialized successfully")
    else:
        raise Exception("Ollama connection failed")
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
    document_id: str  # Changed from policy_id to document_id
    document_type: str = "general"  # New field to specify document type

class QueryResponse(BaseModel):
    answer: str
    task_type: str
    original_sections: List[Dict]
    document_type: str  # Add document type to response
    status: str

class ConversationFolderRequest(BaseModel):
    title: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    document_type: str = "general"

class ConversationUpdateRequest(BaseModel):
    title: str

# Authentication Models
class UserSignupRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str

class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory document registry for demo (changed from policy_registry)
document_registry: Dict[str, Dict] = {}

# Authentication helper function
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    user_info = auth_manager.verify_jwt_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_info

# Optional authentication (for backwards compatibility)
def get_current_user_optional(authorization: Optional[str] = Header(None)):
    """Get current user if authenticated, otherwise return None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization.split(" ")[1]
    return auth_manager.verify_jwt_token(token)

@app.get("/health")
def health():
    return {"status": "ok"}

# ============ AUTHENTICATION ENDPOINTS ============

@app.post("/auth/signup")
def signup(request: UserSignupRequest):
    """User registration endpoint"""
    result = auth_manager.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name
    )
    
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
            "user_id": result["user_id"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.post("/auth/login")
def login(request: UserLoginRequest):
    """User login endpoint"""
    result = auth_manager.authenticate_user(request.username_or_email, request.password)
    
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"],
            "user": result["user"],
            "token": result["token"]
        }
    else:
        raise HTTPException(status_code=401, detail=result["message"])

@app.get("/auth/me")
def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current user information"""
    user_info = auth_manager.get_user_by_id(current_user["user_id"])
    if user_info:
        return {
            "status": "success",
            "user": user_info
        }
    else:
        raise HTTPException(status_code=404, detail="User not found")

@app.put("/auth/profile")
def update_profile(request: UserUpdateRequest, current_user = Depends(get_current_user)):
    """Update user profile"""
    result = auth_manager.update_user_profile(
        user_id=current_user["user_id"],
        full_name=request.full_name,
        email=request.email
    )
    
    if result["success"]:
        return {
            "status": "success",
            "message": result["message"]
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.post("/auth/logout")
def logout(current_user = Depends(get_current_user)):
    """User logout (client should discard token)"""
    return {
        "status": "success",
        "message": "Logged out successfully"
    }

@app.get("/health/ollama")
def ollama_health():
    """Check Ollama service and model availability"""
    try:
        from agentic_rag import test_ollama_connection
        is_connected = test_ollama_connection()
        return {
            "ollama_available": is_connected,
            "model": "gemma3:1b",
            "status": "connected" if is_connected else "disconnected",
            "agentic_rag_enabled": hasattr(agent_workflow, 'supervisor')
        }
    except Exception as e:
        return {
            "ollama_available": False,
            "model": "gemma3:1b",
            "status": "error",
            "error": str(e),
            "agentic_rag_enabled": False
        }

@app.get("/memory/stats")
def get_memory_stats():
    """Get conversation memory statistics"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            stats = agent_workflow.memory_manager.get_database_stats()
            return {
                "memory_enabled": True,
                "storage_type": "persistent_sqlite",
                **stats
            }
        else:
            return {
                "memory_enabled": False,
                "storage_type": "none",
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "memory_enabled": False,
            "error": str(e)
        }

@app.delete("/memory/{document_id}")
def clear_document_memory(document_id: str):
    """Clear conversation history for a specific document"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            agent_workflow.memory_manager.clear_conversation_history(document_id)
            return {
                "status": "success",
                "message": f"Cleared conversation history for document {document_id}"
            }
        else:
            return {
                "status": "error",
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/memory/{document_id}")
def get_document_conversations(document_id: str):
    """Get all conversations for a specific document"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            conversations = agent_workflow.memory_manager.get_all_conversations(document_id)
            return {
                "document_id": document_id,
                "conversations": conversations,
                "total_count": len(conversations)
            }
        else:
            return {
                "document_id": document_id,
                "conversations": [],
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "document_id": document_id,
            "conversations": [],
            "error": str(e)
        }

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    document_type: str = Form("general"),
    current_user = Depends(get_current_user_optional)
):
    """Upload any document type (finance, healthcare, legal, technical, etc.)"""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:  
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT supported.")
    
    document_id = str(uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{document_id}{ext}")
    
    # Save file
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process document: parse, chunk, embed, store in ChromaDB
    if doc_processor:
        try:
            result = doc_processor.process_document(save_path, document_id)
            
            if result["status"] == "success":
                document_registry[document_id] = {
                    "file_path": save_path,
                    "filename": file.filename,
                    "document_type": document_type,
                    "processing_result": result,
                    "user_id": current_user["user_id"] if current_user else None,
                    "created_at": datetime.now().isoformat()
                }
                
                return {
                    "document_id": document_id,
                    "filename": file.filename,
                    "document_type": document_type,
                    "total_chunks": result["total_chunks"],
                    "total_characters": result["total_characters"],
                    "status": "success"
                }
            else:
                raise Exception(result.get('error', 'Unknown processing error'))
        
        except Exception as e:
            print(f"Document processing failed: {e}")
            # Fallback: store without processing
            document_registry[document_id] = {
                "file_path": save_path,
                "filename": file.filename,
                "document_type": document_type,
                "processing_result": {"status": "error", "error": str(e)},
                "user_id": current_user["user_id"] if current_user else None,
                "created_at": datetime.now().isoformat()
            }
            return {
                "document_id": document_id,
                "filename": file.filename,
                "document_type": document_type,
                "status": "uploaded_without_processing",
                "note": "Document uploaded but advanced processing failed. Basic functionality available."
            }
    else:
        # No document processor available
        document_registry[document_id] = {
            "file_path": save_path,
            "filename": file.filename,
            "document_type": document_type,
            "processing_result": {"status": "no_processor"},
            "user_id": current_user["user_id"] if current_user else None,
            "created_at": datetime.now().isoformat()
        }
        return {
            "document_id": document_id,
            "filename": file.filename,
            "document_type": document_type,
            "status": "uploaded_basic_mode",
            "note": "Document uploaded in basic mode. Advanced AI features may be limited."
        }

@app.post("/analyze", response_model=QueryResponse)
async def analyze_document(request: Dict[str, str]):
    """Provide comprehensive initial analysis of the uploaded document"""
    document_id = request.get("document_id")
    
    if document_id not in document_registry:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    try:
        # Get document type
        doc_info = document_registry[document_id]
        document_type = doc_info.get('document_type', 'general')
        
        # Create a comprehensive analysis prompt based on document type
        if document_type == "finance":
            analysis_question = "Please provide a comprehensive financial analysis of this document including key financial metrics, risks, recommendations, and overall assessment."
        elif document_type == "healthcare":
            analysis_question = "Please provide a comprehensive healthcare analysis of this document including key medical information, risks, compliance considerations, and recommendations."
        elif document_type == "legal":
            analysis_question = "Please provide a comprehensive legal analysis of this document including key legal points, compliance issues, risks, and recommendations."
        else:
            analysis_question = f"""
            Please provide a comprehensive analysis of this {document_type} document including:
            1. Executive Summary - Brief overview
            2. Key Information - Important details users should know
            3. Main Topics - Primary content areas
            4. Important Findings - Critical facts or data
            5. Recommendations - Suggestions or next steps
            6. Overall Assessment - General evaluation
            """
        
        # Use the agent workflow to generate the analysis
        result = agent_workflow.process_query(document_id, analysis_question, document_type)
        
        return QueryResponse(
            answer=result["answer"],
            task_type="analysis",
            original_sections=result["original_sections"],
            document_type=result["document_type"],
            status=result["status"]
        )
    
    except Exception as e:
        # Fallback response
        return QueryResponse(
            answer=f"## Analysis Error\n\nI apologize, but I encountered an error analyzing the document: {str(e)}",
            task_type="error",
            original_sections=[],
            document_type="general",
            status="error"
        )

@app.post("/query", response_model=QueryResponse)
async def query_document(request: QueryRequest):
    if request.document_id not in document_registry:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    try:
        # Get document type from registry
        doc_info = document_registry[request.document_id]
        document_type = doc_info.get('document_type', request.document_type)
        
        # Use multi-agent workflow to process the query
        result = agent_workflow.process_query(request.document_id, request.question, document_type)
        
        return QueryResponse(
            answer=result["answer"],
            task_type=result["task_type"],
            original_sections=result["original_sections"],
            document_type=result["document_type"],
            status=result["status"]
        )
    
    except Exception as e:
        # Fallback response
        return QueryResponse(
            answer=f"I apologize, but I encountered an error processing your question. Error: {str(e)}",
            task_type="error",
            original_sections=[],
            document_type=request.document_type,
            status="error"
        )

# ============ CONVERSATION MANAGEMENT ENDPOINTS ============

@app.get("/conversations")
def get_all_conversations():
    """Get all conversation folders"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            folders = agent_workflow.memory_manager.get_all_conversation_folders()
            return {
                "status": "success",
                "conversations": folders
            }
        else:
            return {
                "status": "error", 
                "message": "Memory system not available",
                "conversations": []
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "conversations": []
        }

@app.post("/conversations")
def create_conversation(request: ConversationFolderRequest):
    """Create a new conversation folder"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            conversation_id = str(uuid4())
            folder = agent_workflow.memory_manager.create_conversation_folder(
                conversation_id=conversation_id,
                title=request.title,
                document_id=request.document_id,
                document_name=request.document_name,
                document_type=request.document_type
            )
            return {
                "status": "success",
                "conversation": folder
            }
        else:
            return {
                "status": "error",
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/conversations/{conversation_id}")
def get_conversation_messages(conversation_id: str):
    """Get all messages for a specific conversation"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            messages = agent_workflow.memory_manager.get_conversation_messages(conversation_id)
            return {
                "status": "success",
                "messages": messages
            }
        else:
            return {
                "status": "error",
                "message": "Memory system not available",
                "messages": []
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "messages": []
        }

@app.put("/conversations/{conversation_id}")
def update_conversation_title(conversation_id: str, request: ConversationUpdateRequest):
    """Update conversation title"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            agent_workflow.memory_manager.update_conversation_title(conversation_id, request.title)
            return {
                "status": "success",
                "message": "Conversation title updated"
            }
        else:
            return {
                "status": "error",
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation folder and all its messages"""
    try:
        if hasattr(agent_workflow, 'memory_manager'):
            agent_workflow.memory_manager.delete_conversation_folder(conversation_id)
            return {
                "status": "success",
                "message": "Conversation deleted"
            }
        else:
            return {
                "status": "error",
                "message": "Memory system not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# ============ ENHANCED QUERY ENDPOINT WITH CONVERSATION SUPPORT ============

@app.post("/query/{conversation_id}")
def query_with_conversation(conversation_id: str, request: QueryRequest):
    """Query with specific conversation context"""
    try:
        if request.document_id not in document_registry:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_info = document_registry[request.document_id]
        document_type = doc_info.get('document_type', request.document_type)
        
        # Process the query with conversation context
        result = agent_workflow.process_query_with_conversation(
            document_id=request.document_id,
            user_query=request.question,
            document_type=document_type,
            conversation_id=conversation_id
        )
        
        return QueryResponse(
            answer=result["answer"],
            task_type=result["task_type"],
            original_sections=result["original_sections"],
            document_type=result["document_type"],
            status=result["status"]
        )
    
    except Exception as e:
        return QueryResponse(
            answer=f"I apologize, but I encountered an error processing your question. Error: {str(e)}",
            task_type="error",
            original_sections=[],
            document_type=request.document_type,
            status="error"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
