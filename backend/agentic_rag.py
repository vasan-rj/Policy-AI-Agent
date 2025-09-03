"""
Agentic RAG System with Multi-Agent Workflow using LangGraph
Uses Ollama with gemma3:1b model for privacy policy analysis
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
    policy_id: str
    user_query: str
    task_type: str
    context_chunks: List[Dict]
    current_agent: str
    final_answer: str
    original_sections: List[Dict]
    reasoning_steps: List[str]
    next_agent: str

class SupervisorAgent:
    """Supervisor agent that routes queries to specialized agents"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=500
        )
        self.doc_processor = DocumentProcessor()
    
    def classify_and_route(self, state: AgentState) -> AgentState:
        """Classify the query and determine which agent should handle it"""
        
        classification_prompt = f"""
        You are a privacy policy analysis supervisor. Analyze this user query and classify it:
        
        User Query: "{state['user_query']}"
        
        Classification Options:
        1. "translation" - User wants plain English explanation of policy terms
        2. "compliance" - User wants compliance analysis (GDPR, HIPAA, etc.)
        3. "retrieval" - User needs specific information retrieval from policy
        4. "analysis" - User wants comprehensive analysis including summary, issues, and recommendations
        
        Respond with ONLY the classification word: translation, compliance, retrieval, or analysis
        """
        
        try:
            classification = self.llm.invoke(classification_prompt).strip().lower()
            
            # Special handling for comprehensive analysis requests
            query_lower = state['user_query'].lower()
            if 'comprehensive analysis' in query_lower or 'initial analysis' in query_lower or len(state['user_query']) > 300:
                classification = 'analysis'
            
            # Fallback classification if LLM response is unclear
            if classification not in ['translation', 'compliance', 'retrieval', 'analysis']:
                if any(word in query_lower for word in ['gdpr', 'hipaa', 'compliant', 'regulation', 'legal']):
                    classification = 'compliance'
                elif any(word in query_lower for word in ['what', 'who', 'when', 'where', 'how']):
                    classification = 'retrieval'
                elif any(word in query_lower for word in ['summary', 'analysis', 'overview', 'issues', 'recommendation']):
                    classification = 'analysis'
                else:
                    classification = 'translation'
            
            state['task_type'] = classification
            state['current_agent'] = 'supervisor'
            state['reasoning_steps'].append(f"Supervisor classified query as: {classification}")
            
            # Retrieve relevant context chunks
            try:
                retrieved_chunks = self.doc_processor.retrieve_relevant_chunks(
                    state['policy_id'], state['user_query'], n_results=4
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
            state['task_type'] = 'translation'  # Default fallback
            state['current_agent'] = 'supervisor'
            return state

class TranslationAgent:
    """Agent specialized in translating legal jargon to plain English"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.2,
            num_predict=800
        )
    
    def translate_to_plain_english(self, state: AgentState) -> AgentState:
        """Translate complex policy language to plain English"""
        
        if state['task_type'] != 'translation':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        
        translation_prompt = f"""
        You are an expert at explaining complex privacy policies in simple, clear language.
        
        CONTEXT FROM POLICY:
        {context_text}
        
        USER QUESTION: {state['user_query']}
        
        INSTRUCTIONS:
        1. Answer based ONLY on the provided context
        2. Use simple, everyday language anyone can understand
        3. Avoid legal jargon completely
        4. Be specific and practical
        5. If context doesn't answer the question, say so clearly
        6. Keep response under 200 words
        7. FORMAT YOUR ANSWER IN MARKDOWN with headings, lists, and emphasis where appropriate
        8. Use a heading like "## Plain English Explanation" at the start
        
        Plain English Answer (in Markdown):
        """
        
        try:
            response = self.llm.invoke(translation_prompt)
            state['final_answer'] = response.strip()
            state['current_agent'] = 'translator'
            state['reasoning_steps'].append("Translation agent provided plain English explanation")
            
        except Exception as e:
            state['final_answer'] = f"## Error\n\nI apologize, but I encountered an error translating the policy language: {str(e)}"
            state['reasoning_steps'].append(f"Translation agent error: {str(e)}")
        
        return state

class ComplianceAgent:
    """Agent specialized in compliance analysis"""
    
    def __init__(self, model_name: str = "gemma3:1b"):
        self.llm = OllamaLLM(
            model=model_name,
            temperature=0.1,
            num_predict=1000
        )
    
    def analyze_compliance(self, state: AgentState) -> AgentState:
        """Analyze policy for regulatory compliance"""
        
        if state['task_type'] != 'compliance':
            return state
        
        context_text = "\n".join([chunk["text"] for chunk in state['context_chunks'][:4]])
        
        compliance_prompt = f"""
        You are a privacy compliance expert specializing in GDPR, HIPAA, and data protection laws.
        
        POLICY CONTENT:
        {context_text}
        
        USER QUESTION: {state['user_query']}
        
        ANALYSIS REQUIREMENTS:
        1. Review the policy content for compliance gaps
        2. Identify specific regulatory requirements that may be missing
        3. Provide actionable recommendations
        4. FORMAT YOUR RESPONSE AS MARKDOWN with these sections:
           - ## Compliance Analysis
           - ### Issues Found
           - ### Recommendations
           - ### Risk Level
        5. Use proper Markdown formatting with **bold**, *italics*, bullet lists, etc.
        6. Be specific about which regulations apply
        
        Compliance Analysis (in Markdown):
        """
        
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
        
        retrieval_prompt = f"""
        You are an information retrieval specialist for privacy policies.
        
        RELEVANT POLICY SECTIONS:
        {context_text}
        
        USER QUESTION: {state['user_query']}
        
        TASK:
        1. Extract the exact information requested
        2. Provide direct, factual answers
        3. Quote specific policy language when relevant (use Markdown > blockquotes)
        4. If information is not found, state clearly
        5. Be concise and accurate
        6. FORMAT YOUR RESPONSE IN MARKDOWN with:
           - ## Key Information
           - Use bullet lists for multiple points
           - Use blockquotes (>) for direct quotes from the policy
        7. Keep response under 250 words
        
        Retrieved Information (in Markdown):
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
        
        analysis_prompt = f"""
        You are a comprehensive privacy policy analyst. Provide a detailed analysis of this privacy policy.
        
        POLICY CONTENT:
        {context_text}
        
        USER REQUEST: {state['user_query']}
        
        PROVIDE A COMPREHENSIVE ANALYSIS IN MARKDOWN FORMAT WITH THESE SECTIONS:

        ## Executive Summary
        Brief overview of what this privacy policy covers and its purpose.

        ## Key Information
        Important details users should know:
        - What data is collected
        - How data is used
        - Who has access to data
        - Data retention periods

        ## Data Collection Practices
        Detailed breakdown of:
        - Types of data collected
        - Collection methods
        - Purposes for collection

        ## User Rights
        What rights users have regarding their data:
        - Access rights
        - Deletion rights
        - Opt-out options
        - Contact information

        ## Issues & Concerns
        Any problematic areas identified:
        - Unclear language
        - Broad permissions
        - Missing information
        - Potential privacy risks

        ## Recommendations
        Actionable suggestions:
        - For users (how to protect themselves)
        - For the organization (policy improvements)

        ## Overall Assessment
        General evaluation and key takeaways.

        Keep each section concise but informative. Use bullet points where appropriate.
        
        Comprehensive Analysis:
        """
        
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
        
        # Initialize state
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
            next_agent=""
        )
        
        try:
            # Run the workflow
            config = {"configurable": {"thread_id": f"thread_{policy_id}"}}
            result = self.workflow.invoke(initial_state, config)
            
            return {
                "answer": result.get('final_answer', 'No answer generated'),
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
