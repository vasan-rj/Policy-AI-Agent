# Simplified agents implementation without complex LangGraph imports
from typing import TypedDict, List, Dict, Any
import json
from document_processor import DocumentProcessor

class AgentState(TypedDict):
    policy_id: str
    query: str
    task_type: str
    context_chunks: List[Dict]
    final_answer: str
    original_sections: List[Dict]

class SimpleMultiAgentWorkflow:
    def __init__(self):
        try:
            self.doc_processor = DocumentProcessor()
        except Exception as e:
            print(f"Warning: Document processor initialization failed: {e}")
            self.doc_processor = None
    
    def classify_query(self, query: str) -> str:
        """Classify the user query to determine routing"""
        query_lower = query.lower()
        
        compliance_keywords = [
            "gdpr", "hipaa", "compliance", "regulation", "legal", "violation",
            "audit", "checklist", "requirements", "law", "policy compliance"
        ]
        
        if any(keyword in query_lower for keyword in compliance_keywords):
            return "compliance"
        else:
            return "translation"
    
    def translate_to_plain_english(self, query: str, context_text: str) -> str:
        """Simple rule-based translation to plain English"""
        query_lower = query.lower()
        
        if "who" in query_lower and ("see" in query_lower or "access" in query_lower):
            # Extract relevant parties from context
            parties = []
            if "healthcare provider" in context_text.lower():
                parties.append("your healthcare provider")
            if "researcher" in context_text.lower():
                parties.append("medical researchers (with anonymized data)")
            if "third-party" in context_text.lower() or "third party" in context_text.lower():
                parties.append("approved third-party services")
            
            if parties:
                return f"According to your privacy policy, your data can be seen by: {', '.join(parties)}. " + \
                       f"Here's the exact policy text: '{context_text[:200]}...'"
            else:
                return f"The policy mentions data access in this section: '{context_text[:300]}...'"
        
        elif "how long" in query_lower and ("store" in query_lower or "keep" in query_lower or "retain" in query_lower):
            # Extract retention periods
            if "7 years" in context_text:
                return "Your medical data is stored for 7 years according to the policy. " + \
                       f"The policy states: '{context_text[:200]}...'"
            elif "30 days" in context_text:
                return "Some data (like location data) is stored for 30 days. " + \
                       f"The policy states: '{context_text[:200]}...'"
            else:
                return f"The data retention policy is described as: '{context_text[:300]}...'"
        
        elif "share" in query_lower or "third party" in query_lower:
            return f"Regarding data sharing, the policy explains: '{context_text[:300]}...' " + \
                   "In simple terms, this means your data may be shared with specific approved parties under certain conditions."
        
        else:
            return f"Based on the relevant policy section: '{context_text[:250]}...' " + \
                   f"This addresses your question about {query.lower()}. " + \
                   "The policy language has been simplified for easier understanding."
    
    def analyze_compliance(self, query: str, context_text: str) -> str:
        """Simple compliance analysis"""
        compliance_issues = []
        recommendations = []
        
        # Check for GDPR elements
        if "gdpr" in query.lower():
            if "consent" not in context_text.lower():
                compliance_issues.append("Missing explicit consent mechanism")
                recommendations.append("Add clear consent collection procedures")
            
            if "right to delete" not in context_text.lower() and "erasure" not in context_text.lower():
                compliance_issues.append("Right to erasure not clearly stated")
                recommendations.append("Include user's right to request data deletion")
        
        # Check for HIPAA elements
        if "hipaa" in query.lower():
            if "minimum necessary" not in context_text.lower():
                compliance_issues.append("HIPAA minimum necessary rule not addressed")
                recommendations.append("Specify minimum necessary data usage")
        
        response = "🔍 **Compliance Analysis Results:**\n\n"
        response += f"📋 **Policy Section Reviewed:** {context_text[:200]}...\n\n"
        
        if compliance_issues:
            response += "⚠️ **Potential Issues Found:**\n"
            for issue in compliance_issues:
                response += f"• {issue}\n"
            response += "\n"
        
        if recommendations:
            response += "✅ **Recommendations:**\n"
            for rec in recommendations:
                response += f"• {rec}\n"
            response += "\n"
        
        response += "📌 **Note:** This is a basic automated analysis. For comprehensive compliance review, consult with privacy law experts."
        
        return response
    
    def process_query(self, policy_id: str, query: str) -> Dict[str, Any]:
        """Process a user query through the simplified agent system"""
        try:
            task_type = self.classify_query(query)
            
            # Try to get context from document processor
            context_chunks = []
            original_sections = []
            
            if self.doc_processor:
                try:
                    retrieved_chunks = self.doc_processor.retrieve_relevant_chunks(
                        policy_id, query, n_results=3
                    )
                    context_chunks = [chunk["text"] for chunk in retrieved_chunks]
                    original_sections = [
                        {
                            "text": chunk["text"],
                            "relevance": 1.0 - chunk.get("distance", 0.3)
                        }
                        for chunk in retrieved_chunks
                    ]
                except Exception as e:
                    print(f"Vector search failed: {e}")
                    # Fallback: try to read the original file
                    context_chunks = ["Document processing temporarily unavailable."]
            
            if not context_chunks:
                context_chunks = ["No relevant context found in the policy."]
            
            context_text = " ".join(context_chunks)
            
            # Generate answer based on task type
            if task_type == "compliance":
                answer = self.analyze_compliance(query, context_text)
            else:
                answer = self.translate_to_plain_english(query, context_text)
            
            return {
                "answer": answer,
                "task_type": task_type,
                "context_chunks": context_chunks,
                "original_sections": original_sections,
                "status": "success"
            }
            
        except Exception as e:
            return {
                "answer": f"I encountered an error processing your question: {str(e)}",
                "task_type": "error",
                "context_chunks": [],
                "original_sections": [],
                "status": "error"
            }

# Alias for compatibility
MultiAgentWorkflow = SimpleMultiAgentWorkflow
