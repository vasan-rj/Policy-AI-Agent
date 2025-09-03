from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated, List, Dict, Any
import ollama
from document_processor import DocumentProcessor
import json

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    policy_id: str
    query: str
    task_type: str
    context_chunks: List[Dict]
    final_answer: str
    original_sections: List[Dict]
    next_agent: str

class SupervisorAgent:
    """Supervisor agent that routes queries to appropriate specialized agents"""
    
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.ollama_client = ollama.Client()
    
    def classify_and_route(self, state: AgentState) -> AgentState:
        """Classify query and determine routing"""
        
        classification_prompt = f"""
You are a query classification expert. Analyze the user's question and classify it into one of these categories:

CATEGORIES:
1. "translation" - Questions asking for plain English explanations of policy content
2. "compliance" - Questions about regulatory compliance (GDPR, HIPAA, etc.)

USER QUESTION: {state["query"]}

Respond with ONLY the category name: either "translation" or "compliance"
"""
        
        try:
            response = self.ollama_client.chat(
                model='gemma3:1b',
                messages=[{'role': 'user', 'content': classification_prompt}]
            )
            
            task_type = response['message']['content'].strip().lower()
            if task_type not in ["translation", "compliance"]:
                task_type = "translation"  # Default fallback
            
            state["task_type"] = task_type
            
            # Retrieve relevant context using RAG
            context_chunks = self.doc_processor.retrieve_relevant_chunks(
                state["policy_id"], 
                state["query"],
                n_results=5
            )
            state["context_chunks"] = context_chunks
            
            # Determine next agent
            if task_type == "compliance":
                state["next_agent"] = "compliance_expert"
            else:
                state["next_agent"] = "translator"
            
            print(f"📋 Supervisor: Classified as '{task_type}', routing to {state['next_agent']}")
            
        except Exception as e:
            print(f"⚠️ Supervisor classification failed: {e}")
            state["task_type"] = "translation"
            state["next_agent"] = "translator"
            state["context_chunks"] = []
        
        return state

class TranslatorAgent:
    """Agent specialized in translating legal/policy text to plain English"""
    
    def __init__(self):
        self.ollama_client = ollama.Client()
    
    def translate_to_plain_english(self, state: AgentState) -> AgentState:
        """Generate plain English explanation"""
        
        if not state["context_chunks"]:
            state["final_answer"] = "I couldn't find relevant information in the policy to answer your question."
            state["original_sections"] = []
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state["context_chunks"]])
        
        translation_prompt = f"""
You are an expert at explaining complex legal and privacy policy language in simple, clear terms that anyone can understand.

POLICY CONTEXT:
{context_text}

USER QUESTION: {state["query"]}

INSTRUCTIONS:
1. Answer based ONLY on the provided policy context
2. Use simple, everyday language - avoid legal jargon
3. Be specific and direct
4. If the context doesn't fully answer the question, say so clearly
5. Keep your answer concise but complete
6. Make it sound conversational and friendly

PLAIN ENGLISH ANSWER:"""

        try:
            response = self.ollama_client.chat(
                model='gemma3:1b',
                messages=[{'role': 'user', 'content': translation_prompt}]
            )
            
            answer = response['message']['content']
            state["final_answer"] = answer
            
            # Store original sections for highlighting
            state["original_sections"] = [
                {
                    "text": chunk["text"],
                    "relevance": 1.0 - chunk.get("distance", 0.3)
                }
                for chunk in state["context_chunks"]
            ]
            
            print(f"💬 Translator: Generated plain English response")
            
        except Exception as e:
            print(f"⚠️ Translation failed: {e}")
            state["final_answer"] = f"I encountered an error processing your question: {str(e)}"
            state["original_sections"] = []
        
        return state

class ComplianceExpertAgent:
    """Agent specialized in compliance analysis and regulatory review"""
    
    def __init__(self):
        self.ollama_client = ollama.Client()
    
    def analyze_compliance(self, state: AgentState) -> AgentState:
        """Perform detailed compliance analysis"""
        
        if not state["context_chunks"]:
            state["final_answer"] = "I couldn't find relevant policy content to analyze for compliance."
            state["original_sections"] = []
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state["context_chunks"]])
        
        compliance_prompt = f"""
You are a privacy and compliance expert specializing in GDPR, HIPAA, and data protection regulations.

POLICY CONTENT TO ANALYZE:
{context_text}

USER QUESTION: {state["query"]}

TASK: Provide a detailed compliance analysis following this structure:

🔍 COMPLIANCE ANALYSIS:

📋 Policy Section Reviewed: [Brief description]

✅ COMPLIANT ELEMENTS:
- [List what's good/compliant]

⚠️ POTENTIAL ISSUES:
- [List gaps or concerns]

📝 RECOMMENDATIONS:
- [Specific actionable improvements]

🎯 REGULATORY FOCUS:
- [Specific regulations that apply]

Be thorough but concise. Focus on actionable insights.

COMPLIANCE ANALYSIS:"""

        try:
            response = self.ollama_client.chat(
                model='gemma3:1b',
                messages=[{'role': 'user', 'content': compliance_prompt}]
            )
            
            answer = response['message']['content']
            state["final_answer"] = answer
            
            # Store original sections for highlighting
            state["original_sections"] = [
                {
                    "text": chunk["text"],
                    "relevance": 1.0 - chunk.get("distance", 0.3)
                }
                for chunk in state["context_chunks"]
            ]
            
            print(f"⚖️ Compliance Expert: Generated compliance analysis")
            
        except Exception as e:
            print(f"⚠️ Compliance analysis failed: {e}")
            state["final_answer"] = f"I encountered an error analyzing compliance: {str(e)}"
            state["original_sections"] = []
        
        return state

class AgenticRAGWorkflow:
    """Multi-agent RAG workflow using LangGraph"""
    
    def __init__(self):
        self.supervisor = SupervisorAgent()
        self.translator = TranslatorAgent()
        self.compliance_expert = ComplianceExpertAgent()
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes (agents)
        workflow.add_node("supervisor", self.supervisor.classify_and_route)
        workflow.add_node("translator", self.translator.translate_to_plain_english)
        workflow.add_node("compliance_expert", self.compliance_expert.analyze_compliance)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional routing from supervisor
        def route_to_specialist(state: AgentState) -> str:
            return state.get("next_agent", "translator")
        
        workflow.add_conditional_edges(
            "supervisor",
            route_to_specialist,
            {
                "translator": "translator",
                "compliance_expert": "compliance_expert"
            }
        )
        
        # Both specialist agents go to END
        workflow.add_edge("translator", END)
        workflow.add_edge("compliance_expert", END)
        
        return workflow.compile()
    
    def process_query(self, policy_id: str, query: str) -> Dict[str, Any]:
        """Process a user query through the agentic RAG system"""
        
        print(f"🚀 Starting agentic RAG workflow for query: '{query[:50]}...'")
        
        # Initialize state
        initial_state = AgentState(
            messages=[],
            policy_id=policy_id,
            query=query,
            task_type="",
            context_chunks=[],
            final_answer="",
            original_sections=[],
            next_agent=""
        )
        
        try:
            # Run the workflow
            result = self.workflow.invoke(initial_state)
            
            return {
                "answer": result["final_answer"],
                "task_type": result["task_type"],
                "context_chunks": result["context_chunks"],
                "original_sections": result["original_sections"],
                "status": "success"
            }
            
        except Exception as e:
            print(f"❌ Workflow execution failed: {e}")
            return {
                "answer": f"I encountered an error processing your question: {str(e)}",
                "task_type": "error",
                "context_chunks": [],
                "original_sections": [],
                "status": "error"
            }

# Create alias for backward compatibility
MultiAgentWorkflow = AgenticRAGWorkflow
