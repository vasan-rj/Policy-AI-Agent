"""
Persistent Chat Memory Manager using SQLite
Stores conversation history in a database for persistence across server restarts
"""

import sqlite3
import json
from typing import List, Dict
from datetime import datetime
import os

class PersistentChatMemoryManager:
    """Manages conversation history with SQLite persistence"""
    
    def __init__(self, db_path: str = "chat_memory.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database and create tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create conversation_folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_folders (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                document_id TEXT,
                document_name TEXT,
                document_type TEXT DEFAULT 'general',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        # Create conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                task_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversation_folders (id)
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_document_id_timestamp 
            ON conversations (document_id, timestamp DESC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversation_id_timestamp 
            ON conversations (conversation_id, timestamp ASC)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_folders_updated 
            ON conversation_folders (updated_at DESC)
        ''')
        
        conn.commit()
        conn.close()
    
    def add_conversation(self, document_id: str, question: str, answer: str, task_type: str, conversation_id: str = None):
        """Add a Q&A pair to conversation history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # If no conversation_id provided, use document_id as default
        if conversation_id is None:
            conversation_id = document_id
        
        cursor.execute('''
            INSERT INTO conversations (conversation_id, document_id, question, answer, task_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (conversation_id, document_id, question, answer, task_type))
        
        # Update message count and updated_at for the conversation folder
        cursor.execute('''
            UPDATE conversation_folders 
            SET message_count = message_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (conversation_id,))
        
        conn.commit()
        conn.close()
        print(f"💾 Saved conversation to database for conversation: {conversation_id}")
    
    def create_conversation_folder(self, conversation_id: str, title: str, document_id: str = None, 
                                  document_name: str = None, document_type: str = "general"):
        """Create a new conversation folder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conversation_folders 
            (id, title, document_id, document_name, document_type, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 0)
        ''', (conversation_id, title, document_id, document_name, document_type))
        
        conn.commit()
        conn.close()
        print(f"📁 Created conversation folder: {title} ({conversation_id})")
        
        return {
            "id": conversation_id,
            "title": title,
            "document_id": document_id,
            "document_name": document_name,
            "document_type": document_type,
            "message_count": 0
        }
    
    def get_all_conversation_folders(self) -> List[Dict]:
        """Get all conversation folders ordered by last update"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, document_id, document_name, document_type, 
                   created_at, updated_at, message_count
            FROM conversation_folders 
            ORDER BY updated_at DESC
        ''')
        
        folders = []
        for row in cursor.fetchall():
            folders.append({
                "id": row[0],
                "title": row[1],
                "document_id": row[2],
                "document_name": row[3],
                "document_type": row[4],
                "created_at": row[5],
                "updated_at": row[6],
                "message_count": row[7]
            })
        
        conn.close()
        return folders
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get all messages for a specific conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question, answer, task_type, timestamp
            FROM conversations 
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        ''', (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "question": row[0],
                "answer": row[1],
                "task_type": row[2],
                "timestamp": row[3]
            })
        
        conn.close()
        return messages
    
    def delete_conversation_folder(self, conversation_id: str):
        """Delete a conversation folder and all its messages"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete all messages in the conversation
        cursor.execute('DELETE FROM conversations WHERE conversation_id = ?', (conversation_id,))
        
        # Delete the folder
        cursor.execute('DELETE FROM conversation_folders WHERE id = ?', (conversation_id,))
        
        conn.commit()
        conn.close()
        print(f"🗑️ Deleted conversation folder: {conversation_id}")
    
    def update_conversation_title(self, conversation_id: str, new_title: str):
        """Update the title of a conversation folder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE conversation_folders 
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_title, conversation_id))
        
        conn.commit()
        conn.close()
        print(f"✏️ Updated conversation title: {conversation_id} -> {new_title}")
    
    def get_conversation_history(self, document_id: str, limit: int = 3) -> List[Dict]:
        """Get raw conversation history (last N conversations)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question, answer, task_type, timestamp
            FROM conversations 
            WHERE document_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (document_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts and reverse to get chronological order
        conversations = []
        for i, (question, answer, task_type, timestamp) in enumerate(reversed(rows)):
            conversations.append({
                "question": question,
                "answer": answer,
                "task_type": task_type,
                "timestamp": str(i + 1)
            })
        
        return conversations
    
    def get_conversation_context(self, document_id: str) -> str:
        """Get formatted conversation history for context"""
        conversations = self.get_conversation_history(document_id, limit=2)
        
        if not conversations:
            return ""
        
        context_parts = ["Previous conversation context:"]
        for conv in conversations:
            context_parts.append(f"Q: {conv['question']}")
            # Truncate long answers for context
            answer_preview = conv['answer'][:200]
            if len(conv['answer']) > 200:
                answer_preview += "..."
            context_parts.append(f"A: {answer_preview}")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def get_all_conversations(self, document_id: str) -> List[Dict]:
        """Get all conversations for a document (for admin/debug purposes)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT question, answer, task_type, timestamp
            FROM conversations 
            WHERE document_id = ? 
            ORDER BY timestamp ASC
        ''', (document_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        conversations = []
        for question, answer, task_type, timestamp in rows:
            conversations.append({
                "question": question,
                "answer": answer,
                "task_type": task_type,
                "timestamp": timestamp
            })
        
        return conversations
    
    def clear_conversation_history(self, document_id: str):
        """Clear all conversation history for a document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM conversations WHERE document_id = ?', (document_id,))
        
        conn.commit()
        conn.close()
        
        print(f"🗑️ Cleared conversation history for document: {document_id}")
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total conversations
        cursor.execute('SELECT COUNT(*) FROM conversations')
        total_conversations = cursor.fetchone()[0]
        
        # Unique documents
        cursor.execute('SELECT COUNT(DISTINCT document_id) FROM conversations')
        unique_documents = cursor.fetchone()[0]
        
        # Database size
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        
        conn.close()
        
        return {
            "total_conversations": total_conversations,
            "unique_documents": unique_documents,
            "database_size_bytes": db_size,
            "database_size_mb": round(db_size / (1024 * 1024), 2)
        }

# Compatibility wrapper for the old in-memory system
class ChatMemoryManager(PersistentChatMemoryManager):
    """Backward compatibility wrapper"""
    pass

if __name__ == "__main__":
    # Test the persistent memory system
    print("Testing Persistent Chat Memory Manager...")
    
    memory = PersistentChatMemoryManager("test_memory.db")
    
    # Add some test conversations
    memory.add_conversation("doc1", "What is this document about?", "This is a financial report...", "explanation")
    memory.add_conversation("doc1", "What are the key metrics?", "The key metrics include revenue of $100M...", "extraction")
    memory.add_conversation("doc1", "What was my last question?", "Your last question was about key metrics.", "explanation")
    
    # Get conversation history
    history = memory.get_conversation_history("doc1")
    print(f"Conversation history: {history}")
    
    # Get formatted context
    context = memory.get_conversation_context("doc1")
    print(f"Context for prompts:\n{context}")
    
    # Get stats
    stats = memory.get_database_stats()
    print(f"Database stats: {stats}")
    
    print("✅ Persistent memory system working!")
