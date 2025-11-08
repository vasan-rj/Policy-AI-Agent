"""
Agentic RAG System with Multi-Agent Workflow using LangGraph
Uses Ollama with gemma3:1b model for document analysis and question answering
Supports any document type: finance, healthcare, legal, technical, etc.
"""

from typing import TypedDict, List, Dict, Any, Annotated
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_ollama import OllamaLLM
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver
import operator
import ollama
from document_processor import DocumentProcessor

# Define the state for our multi-agent system
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    document_id: str  # Changed from policy_id to document_id
    user_query: str
    task_type: str
    context_chunks: List[Dict]
    current_agent: str
    final_answer: str
    original_sections: List[Dict]
    reasoning_steps: List[str]
    next_agent: str
    conversation_history: List[Dict]  # Store last 3 Q&A pairs
    document_type: str  # New field to track document type (finance, healthcare, legal, etc.)

# Chat Memory Manager
class ChatMemoryManager:
    """Manages conversation history for context awareness across all document types"""
    
    def __init__(self):
        self.conversations = {}  # document_id -> List[Dict]
    
    def add_conversation(self, document_id: str, question: str, answer: str, task_type: str):
        """Add a Q&A pair to conversation history"""
        if document_id not in self.conversations:
            self.conversations[document_id] = []
        
        conversation_entry = {
            "question": question,
            "answer": answer,
            "task_type": task_type,
            "timestamp": f"{len(self.conversations[document_id]) + 1}"
        }
        
        self.conversations[document_id].append(conversation_entry)
        
        # Keep only last 3 conversations
        if len(self.conversations[document_id]) > 3:
            self.conversations[document_id] = self.conversations[document_id][-3:]
    
    def get_conversation_context(self, document_id: str) -> str:
        """Get formatted conversation history for context"""
        if document_id not in self.conversations or not self.conversations[document_id]:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for conv in self.conversations[document_id]:
            context_parts.append(f"Q: {conv['question']}")
            context_parts.append(f"A: {conv['answer'][:200]}...")  # Truncate long answers
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def get_conversation_history(self, document_id: str) -> List[Dict]:
        """Get raw conversation history"""
        return self.conversations.get(document_id, [])

class SupervisorAgent:
    """Supervisor agent that routes queries to specialized agents based on document type and query"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=500
        )
        self.doc_processor = DocumentProcessor()
    
    def classify_and_route(self, state: AgentState) -> AgentState:
        """Classify the query and determine which agent should handle it"""
        
        # Get conversation context if available
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-2:]  # Last 2 for context
            if recent_qa:
                conversation_context = "\nRecent conversation:\n"
                for qa in recent_qa:
                    conversation_context += f"Q: {qa['question']}\nA: {qa['answer'][:100]}...\n"
        
        # Get document type context
        doc_type = state.get('document_type', 'general')
        
        classification_prompt = f"""Classify this document question into ONE category:
{conversation_context}
Document Type: {doc_type}
Current Query: "{state['user_query']}"

Categories:
- explanation: Explain content in simple terms
- analysis: Detailed analysis/compliance/risk assessment  
- extraction: Find specific facts/data/numbers
- summary: Comprehensive overview/summary

Answer with ONE word only:"""
        
        try:
            classification = self.llm.invoke(classification_prompt).strip().lower()
            print(f"LLM Classification result: '{classification}'")
            
            # Special handling for comprehensive analysis requests
            query_lower = state['user_query'].lower()
            if ('comprehensive analysis' in query_lower or 
                'initial analysis' in query_lower or 
                'full analysis' in query_lower or
                ('summary' in query_lower and any(word in query_lower for word in ['complete', 'full', 'comprehensive', 'detailed']))):
                classification = 'summary'
            
            # Enhanced fallback classification with better keyword patterns
            if classification not in ['explanation', 'analysis', 'extraction', 'summary']:
                print(f"Unknown classification '{classification}', using enhanced fallback logic")
                
                # Rule-based classification with priority order
                if any(word in query_lower for word in ['analyze', 'compliance', 'risk', 'check', 'assess', 'evaluate', 'review']):
                    classification = 'analysis'
                elif any(word in query_lower for word in ['what', 'who', 'when', 'where', 'how', 'which', 'list', 'find', 'show', 'tell me', 'extract', 'data', 'number', 'amount']):
                    classification = 'extraction'
                elif any(word in query_lower for word in ['explain', 'simple', 'understand', 'mean', 'clarify', 'what does']):
                    classification = 'explanation'
                elif any(word in query_lower for word in ['summary', 'overview', 'summarize', 'key points', 'main points']):
                    classification = 'summary'
                else:
                    # Default based on question structure
                    if query_lower.startswith(('what', 'who', 'when', 'where', 'how', 'which')):
                        classification = 'extraction'
                    elif any(word in query_lower for word in ['is', 'does', 'can', 'will']):
                        classification = 'explanation'
                    else:
                        classification = 'explanation'  # Safe default
                        
                print(f"Enhanced fallback classification: '{classification}'")
            
            state['task_type'] = classification
            state['current_agent'] = 'supervisor'
            state['reasoning_steps'].append(f"Supervisor classified query as: {classification}")
            print(f"Final classification: {classification}")
            
            # Retrieve relevant context chunks
            try:
                retrieved_chunks = self.doc_processor.retrieve_relevant_chunks(
                    state['document_id'], state['user_query'], n_results=4
                )
                state['context_chunks'] = retrieved_chunks
                state['original_sections'] = [
                    {
                        "text": chunk["text"],
                        "relevance": 1.0 - chunk.get("distance", 0.3)
                    }
                    for chunk in retrieved_chunks
                ]
                state['reasoning_steps'].append(f"Retrieved {len(retrieved_chunks)} relevant context chunks")
            except Exception as e:
                state['reasoning_steps'].append(f"Context retrieval failed: {str(e)}")
                state['context_chunks'] = []
                state['original_sections'] = []
            
            return state
            
        except Exception as e:
            state['reasoning_steps'].append(f"Supervisor error: {str(e)}")
            state['task_type'] = 'explanation'  # Default fallback
            state['current_agent'] = 'supervisor'
            return state

class ExplanationAgent:
    """Agent specialized in explaining document content in simple terms"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.2,
            num_predict=800
        )
    
    def explain_content(self, state: AgentState) -> AgentState:
        """Explain complex document content in simple terms"""
        
        if state['task_type'] != 'explanation':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        doc_type = state.get('document_type', 'document')
        
        # Add conversation context for continuity
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nPrevious question: {recent_qa[0]['question']}\n"
        
        explanation_prompt = f"""Explain this {doc_type} content in simple terms:
{conversation_context}
DOCUMENT TEXT:
{context_text}

USER QUESTION: {state['user_query']}

Rules:
- Use everyday language, avoid jargon
- Answer only from the document text above
- If information not found, say "not available in document"
- Format as markdown with ## heading
- Max 150 words

## Simple Explanation:"""
        
        try:
            response = self.llm.invoke(explanation_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'explanation'
            state['reasoning_steps'].append("Explanation agent provided simplified explanation")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error explaining the content: {str(e)}"
            state['reasoning_steps'].append(f"Explanation agent error: {str(e)}")
        
        return state

class AnalysisAgent:
    """Agent specialized in detailed analysis and risk assessment"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=1000
        )
    
    def analyze_document(self, state: AgentState) -> AgentState:
        """Analyze document for risks, compliance, or detailed assessment"""
        
        if state['task_type'] != 'analysis':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        doc_type = state.get('document_type', 'document')
        
        # Add conversation context for analysis continuity
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nPrevious analysis: {recent_qa[0]['question']}\n"
        
        analysis_prompt = f"""Analyze this {doc_type} for detailed insights:
{conversation_context}
DOCUMENT TEXT:
{context_text}

QUESTION: {state['user_query']}

Provide structured analysis based on document type.

Format:
## Analysis Results
### Key Findings
### Risk Assessment  
### Recommendations
### Assessment: [Low/Medium/High Risk or Good/Fair/Poor]

Be specific and factual. Max 200 words."""
        
        try:
            response = self.llm.invoke(analysis_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'analysis'
            state['reasoning_steps'].append("Analysis agent provided detailed assessment")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error during analysis: {str(e)}"
            state['reasoning_steps'].append(f"Analysis agent error: {str(e)}")
        
        return state

class ExtractionAgent:
    """Agent specialized in extracting specific information and data"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=600
        )
    
    def extract_information(self, state: AgentState) -> AgentState:
        """Extract specific information and provide focused answers"""
        
        if state['task_type'] != 'extraction':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        doc_type = state.get('document_type', 'document')
        
        # Add conversation context for related questions
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nRelated to previous: {recent_qa[0]['question']}\n"
        
        extraction_prompt = f"""Find specific information from this {doc_type}:
{conversation_context}
DOCUMENT TEXT:
{context_text}

QUESTION: {state['user_query']}

Instructions:
- Extract exact facts, numbers, dates, names requested
- Quote document text using > blockquotes
- If not found, say "Information not available in document"
- Be direct and factual

## Key Information:"""
        
        try:
            response = self.llm.invoke(extraction_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'extraction'
            state['reasoning_steps'].append("Extraction agent provided specific information")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error extracting information: {str(e)}"
            state['reasoning_steps'].append(f"Extraction agent error: {str(e)}")
        
        return state

class SummaryAgent:
    """Agent specialized in comprehensive document summarization"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=1500
        )
    
    def comprehensive_summary(self, state: AgentState) -> AgentState:
        """Provide comprehensive summary of the document"""
        
        if state['task_type'] != 'summary':
            return state
        
        # Use more context for comprehensive summary
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:8]])
        doc_type = state.get('document_type', 'document')
        
        # Add conversation context for related summary
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nBased on previous summary: {recent_qa[0]['question']}\n"
        
        summary_prompt = f"""Provide a comprehensive summary of this {doc_type}:
{conversation_context}
DOCUMENT TEXT:
{context_text}

Provide structured summary:

## Executive Summary
Brief overview

## Key Points  
Main topics and important details

## Important Information
Critical facts users should know

## Recommendations
Actions or considerations

## Overall Assessment
General evaluation

Keep each section concise. Use bullet points where appropriate."""
        
        try:
            response = self.llm.invoke(summary_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'summary'
            state['reasoning_steps'].append("Summary agent provided comprehensive overview")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error during summarization: {str(e)}"
            state['reasoning_steps'].append(f"Summary agent error: {str(e)}")
        
        return state
        
        # Add conversation context for compliance continuity
        conversation_context = ""
        if state.get('conversation_history'):
            compliance_qa = [qa for qa in state['conversation_history'] if qa.get('task_type') == 'compliance']
            if compliance_qa:
                conversation_context = f"\nPrevious compliance question: {compliance_qa[-1]['question']}\n"
        
        compliance_prompt = f"""Check this policy for legal compliance:
{conversation_context}
POLICY TEXT:
{context_text}

QUESTION: {state['user_query']}

Analyze for GDPR, HIPAA, data protection laws.

Format:
## Compliance Check
###  Good Practices
###  Issues Found  
###  Recommendations
###  Risk Level: [Low/Medium/High]

Be specific about regulations. Max 200 words."""
        
        try:
            response = self.llm.invoke(compliance_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'compliance'
            state['reasoning_steps'].append("Compliance agent completed regulatory analysis")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error during compliance analysis: {str(e)}"
            state['reasoning_steps'].append(f"Compliance agent error: {str(e)}")
        
        return state

class RetrievalAgent:
    """Agent specialized in information retrieval and summarization"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=600
        )
    
    def retrieve_and_summarize(self, state: AgentState) -> AgentState:
        """Retrieve specific information and provide focused answers"""
        
        if state['task_type'] != 'retrieval':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        
        # Add conversation context for related questions
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nRelated to previous: {recent_qa[0]['question']}\n"
        
        retrieval_prompt = f"""Find specific information from this policy:
{conversation_context}
POLICY TEXT:
{context_text}

QUESTION: {state['user_query']}

Instructions:
- Extract exact facts requested
- Quote policy text using > blockquotes
- If not found, say "Information not available"
- Be direct and factual

## Key Information
"""
        
        try:
            response = self.llm.invoke(retrieval_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'retrieval'
            state['reasoning_steps'].append("Retrieval agent extracted specific information")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error retrieving information: {str(e)}"
            state['reasoning_steps'].append(f"Retrieval agent error: {str(e)}")
        
        return state

class AnalysisAgent:
    """Agent specialized in comprehensive policy analysis"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=1500
        )
    
    def comprehensive_analysis(self, state: AgentState) -> AgentState:
        """Provide comprehensive analysis of the policy document"""
        
        if state['task_type'] != 'analysis':
            return state
        
        # Use more context for comprehensive analysis
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:8]])
        
        # Add conversation context for related analysis
        conversation_context = ""
        if state.get('conversation_history'):
            recent_qa = state['conversation_history'][-1:]
            if recent_qa:
                conversation_context = f"\nBased on previous analysis: {recent_qa[0]['question']}\n"
        
        analysis_prompt = f"""Analyze this privacy policy completely:
{conversation_context}
POLICY TEXT:
{context_text}

Provide structured analysis:

## Summary
Brief policy overview

## Data Collection  
What data is collected and how

## User Rights
Access, deletion, opt-out rights

## Issues Found
Problems or unclear areas

## Recommendations  
Improvements needed

## Overall Rating
Rate: Good/Fair/Poor with reasons

Keep each section under 50 words. Use bullet points."""
        
        try:
            response = self.llm.invoke(analysis_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'analysis'
            state['reasoning_steps'].append("Analysis agent provided comprehensive policy analysis")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI encountered an error during comprehensive analysis: {str(e)}"
            state['reasoning_steps'].append(f"Analysis agent error: {str(e)}")
        
        return state
        

class AgenticRAGWorkflow:
    """Main workflow orchestrator for multi-agent RAG system"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.model_name = model_name
        self.memory_manager = ChatMemoryManager()
        self.supervisor = SupervisorAgent(model_name)
        self.translator = TranslationAgent(model_name)
        self.compliance_agent = ComplianceAgent(model_name)
        self.retrieval_agent = RetrievalAgent(model_name)
        self.analysis_agent = AnalysisAgent(model_name)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with conditional routing"""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes for each agent
        workflow.add_node("supervisor", self.supervisor.classify_and_route)
        workflow.add_node("translator", self.translator.translate_to_plain_english)
        workflow.add_node("compliance", self.compliance_agent.analyze_compliance)
        workflow.add_node("retrieval", self.retrieval_agent.retrieve_and_summarize)
        workflow.add_node("analysis", self.analysis_agent.comprehensive_analysis)
        
        # Set entry point
        workflow.set_entry_point("supervisor")
        
        # Add conditional routing based on task type
        def route_to_specialist(state: AgentState) -> str:
            task_type = state.get('task_type', 'translation')
            if task_type == 'compliance':
                return 'compliance'
            elif task_type == 'retrieval':
                return 'retrieval'
            elif task_type == 'analysis':
                return 'analysis'
            else:
                return 'translator'
        
        workflow.add_conditional_edges(
            "supervisor",
            route_to_specialist,
            {
                "translator": "translator",
                "compliance": "compliance", 
                "retrieval": "retrieval",
                "analysis": "analysis"
            }
        )
        
        # All specialist agents end the workflow
        workflow.add_edge("translator", END)
        workflow.add_edge("compliance", END)
        workflow.add_edge("retrieval", END)
        workflow.add_edge("analysis", END)
        
        # Compile with memory for state persistence
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)
    
    def process_query(self, policy_id: str, user_query: str) -> Dict[str, Any]:
        """Process a user query through the multi-agent RAG system"""
        
        print(f"🚀 Starting agentic RAG workflow for query: '{user_query[:50]}...'")
        
        # Get conversation history for context
        conversation_history = self.memory_manager.get_conversation_history(policy_id)
        
        # Initialize state with conversation history
        initial_state = AgentState(
            messages=[HumanMessage(content=user_query)],
            policy_id=policy_id,
            user_query=user_query,
            task_type="",
            context_chunks=[],
            current_agent="",
            final_answer="",
            original_sections=[],
            reasoning_steps=[],
            next_agent="",
            conversation_history=conversation_history
        )
        
        try:
            # Run the workflow
            config = {"configurable": {"thread_id": f"thread_{policy_id}"}}
            result = self.workflow.invoke(initial_state, config)
            
            # Store this conversation in memory for future context
            final_answer = result.get('final_answer', 'No answer generated')
            task_type = result.get('task_type', 'unknown')
            self.memory_manager.add_conversation(policy_id, user_query, final_answer, task_type)
            
            return {
                "answer": final_answer,
                "task_type": result.get('task_type', 'unknown'),
                "context_chunks": result.get('context_chunks', []),
                "original_sections": result.get('original_sections', []),
                "reasoning_steps": result.get('reasoning_steps', []),
                "current_agent": result.get('current_agent', 'unknown'),
                "status": "success"
            }
            
        except Exception as e:
            return {
                "answer": f"## Error\n\nI encountered an error processing your query: {str(e)}",
                "task_type": "error",
                "context_chunks": [],
                "original_sections": [],
                "reasoning_steps": [f"Workflow error: {str(e)}"],
                "current_agent": "error",
                "status": "error"
            }

# Test function to verify Ollama connectivity
def test_ollama_connection(model_name: str = "gemma3:1b") -> bool:
    """Test if Ollama is running and model is available"""
    try:
        client = ollama.Client()
        response = client.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': 'Hello, respond with just "OK"'}]
        )
        return "ok" in response['message']['content'].lower()
    except Exception as e:
        print(f"Ollama connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Test the agentic RAG system
    print("Testing Agentic RAG System...")
    
    if test_ollama_connection():
        print("✅ Ollama connection successful!")
        workflow = AgenticRAGWorkflow()
        print("✅ Agentic RAG workflow initialized!")
    else:
        print("❌ Ollama connection failed!")
