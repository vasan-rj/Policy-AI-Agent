import pdfplumber
import docx
from typing import List, Dict
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
import uuid
import os

class DocumentProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.chroma_client = chromadb.Client()
        
    def extract_text(self, file_path: str) -> str:
        """Extract text from PDF, DOCX, or TXT files"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return self._extract_pdf_text(file_path)
        elif ext == '.docx':
            return self._extract_docx_text(file_path)
        elif ext == '.txt':
            return self._extract_txt_text(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _extract_pdf_text(self, file_path: str) -> str:
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _extract_docx_text(self, file_path: str) -> str:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    def _extract_txt_text(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    
    def chunk_text(self, text: str) -> List[Dict[str, str]]:
        """Split text into chunks with metadata"""
        chunks = self.text_splitter.split_text(text)
        chunk_data = []
        
        for i, chunk in enumerate(chunks):
            chunk_data.append({
                "id": str(uuid.uuid4()),
                "text": chunk,
                "chunk_index": i,
                "char_count": len(chunk)
            })
        
        return chunk_data
    
    def create_embeddings(self, chunks: List[Dict[str, str]]) -> List[Dict]:
        """Create embeddings for text chunks"""
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedder.encode(texts)
        
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i].tolist()
        
        return chunks
    
    def store_in_chromadb(self, policy_id: str, chunks: List[Dict]):
        """Store chunks and embeddings in ChromaDB"""
        try:
            collection = self.chroma_client.create_collection(
                name=f"policy_{policy_id}",
                metadata={"description": f"Policy chunks for {policy_id}"}
            )
        except:
            collection = self.chroma_client.get_collection(f"policy_{policy_id}")
        
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["text"] for chunk in chunks]
        embeddings = [chunk["embedding"] for chunk in chunks]
        metadatas = [
            {
                "chunk_index": chunk["chunk_index"],
                "char_count": chunk["char_count"],
                "policy_id": policy_id
            }
            for chunk in chunks
        ]
        
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        return collection
    
    def retrieve_relevant_chunks(self, policy_id: str, query: str, n_results: int = 5) -> List[Dict]:
        """Retrieve relevant chunks for a query"""
        try:
            collection = self.chroma_client.get_collection(f"policy_{policy_id}")
            query_embedding = self.embedder.encode([query])[0].tolist()
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            relevant_chunks = []
            for i in range(len(results["documents"][0])):
                relevant_chunks.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
            
            return relevant_chunks
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def process_document(self, file_path: str, policy_id: str) -> Dict:
        """Complete document processing pipeline"""
        try:
            # Extract text
            text = self.extract_text(file_path)
            
            # Chunk text
            chunks = self.chunk_text(text)
            
            # Create embeddings
            chunks_with_embeddings = self.create_embeddings(chunks)
            
            # Store in ChromaDB
            collection = self.store_in_chromadb(policy_id, chunks_with_embeddings)
            
            return {
                "status": "success",
                "policy_id": policy_id,
                "total_chunks": len(chunks),
                "total_characters": len(text),
                "collection_name": f"policy_{policy_id}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
