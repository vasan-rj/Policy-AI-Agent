# Simple fallback agents for testing without Ollama
from typing import Dict, List, Any
from document_processor import DocumentProcessor
import re

class AgentState(dict):
    """Simple state dictionary"""
    pass

class SimpleFallbackWorkflow:
    """Fallback workflow that works without Ollama"""
    
    def __init__(self):
        try:
            self.doc_processor = DocumentProcessor()
        except Exception as e:
            print(f"Warning: Document processor initialization failed: {e}")
            self.doc_processor = None
    
    def classify_query(self, query: str) -> str:
        """Classify the user query to determine task type"""
        query_lower = query.lower()
        
        compliance_keywords = [
            "gdpr", "hipaa", "compliance", "regulation", "legal", "violation",
            "audit", "checklist", "requirements", "law", "policy compliance",
            "compliant", "regulatory", "violation"
        ]
        
        if any(keyword in query_lower for keyword in compliance_keywords):
            return "compliance"
        else:
            return "translation"
    
    def simple_text_search(self, text: str, query: str) -> List[str]:
        """Simple text-based search when vector search is unavailable"""
        query_words = query.lower().split()
        sentences = re.split(r'[.!?]+', text)
        
        relevant_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short sentences
                score = sum(1 for word in query_words if word in sentence.lower())
                if score > 0:
                    relevant_sentences.append((sentence, score))
        
        # Sort by relevance and return top 3
        relevant_sentences.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in relevant_sentences[:3]]
    
    def generate_simple_answer(self, query: str, context_chunks: List[str], task_type: str) -> str:
        """Generate a simple rule-based answer"""
        if not context_chunks:
            return "I couldn't find relevant information in the policy to answer your question."
        
        context_text = " ".join(context_chunks)
        
        if task_type == "compliance":
            return self._generate_compliance_answer(query, context_text)
        else:
            return self._generate_translation_answer(query, context_text)
    
    def _generate_translation_answer(self, query: str, context: str) -> str:
        """Generate plain English translation"""
        query_lower = query.lower()
        
        # Pattern matching for common questions
        if "who" in query_lower and ("see" in query_lower or "access" in query_lower):
            return f"Based on the policy, your data may be accessed by the parties mentioned in this section: '{context[:200]}...'"
        
        elif "how long" in query_lower and ("store" in query_lower or "keep" in query_lower):
            return f"According to the policy, data retention is described as: '{context[:200]}...'"
        
        elif "share" in query_lower or "third party" in query_lower:
            return f"Regarding data sharing, the policy states: '{context[:200]}...'"
        
        elif "delete" in query_lower or "remove" in query_lower:
            return f"About data deletion, the policy mentions: '{context[:200]}...'"
        
        else:
            return f"Based on the relevant policy section: '{context[:300]}...' - This means the policy addresses your question about {query.lower()}."
    
    def _generate_compliance_answer(self, query: str, context: str) -> str:
        """Generate compliance analysis"""
        return f"""
Compliance Analysis:

✅ FOUND: The policy contains relevant sections about your query.

📋 POLICY EXCERPT: "{context[:200]}..."

⚠️  RECOMMENDATIONS:
- Review the specific language used in the policy
- Ensure it meets current regulatory standards
- Consider consulting with legal experts for detailed compliance review

🔍 AREAS TO EXAMINE:
- Data subject rights implementation
- Consent mechanisms
- Data processing lawfulness
- International data transfers
- Breach notification procedures

Note: This is a basic analysis. For comprehensive compliance review, consult with privacy law experts.
"""
    
    def process_query(self, policy_id: str, query: str) -> Dict[str, Any]:
        """Process a user query with fallback functionality"""
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
                            "relevance": 1.0 - chunk.get("distance", 0.5)
                        }
                        for chunk in retrieved_chunks
                    ]
                except Exception as e:
                    print(f"Vector search failed, using fallback: {e}")
            
            # Fallback: try to read the original file if vector search fails
            if not context_chunks:
                try:
                    # This would need access to the policy registry
                    # For now, return a generic message
                    context_chunks = ["Policy content analysis is temporarily unavailable."]
                    original_sections = []
                except:
                    pass
            
            answer = self.generate_simple_answer(query, context_chunks, task_type)
            
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
