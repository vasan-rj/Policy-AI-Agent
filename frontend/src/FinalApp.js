import React, { useState, useRef, useEffect } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import {
  FiFilePlus,
  FiBarChart2,
  FiBookOpen,
  FiShield,
  FiClock,
  FiMessageSquare,
} from "react-icons/fi";
import { FaQuestionCircle, FaUpload } from "react-icons/fa";
import ConversationSidebar from "./ConversationSidebar";
import "./App.css";
import "./markdown-styles.css";

function FinalApp() {
  // State management
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]);
  const [documentId, setDocumentId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  
  // Conversation management state
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [conversationMessages, setConversationMessages] = useState([]);

  const qaRefs = useRef({});

  // Load conversation messages when active conversation changes
  useEffect(() => {
    if (activeConversationId) {
      loadConversationMessages(activeConversationId);
    } else {
      setConversationMessages([]);
    }
  }, [activeConversationId]);

  const loadConversationMessages = async (conversationId) => {
    try {
      const response = await axios.get(`http://localhost:8001/conversations/${conversationId}`);
      if (response.data.status === 'success') {
        setConversationMessages(response.data.messages);
      }
    } catch (error) {
      console.error('Failed to load conversation messages:', error);
    }
  };

  const handleConversationSelect = (conversationId) => {
    setActiveConversationId(conversationId);
    setHistory([]);
  };

  const handleNewConversation = (conversationId) => {
    setActiveConversationId(conversationId);
    setHistory([]);
    setConversationMessages([]);
  };

  // File upload handler
  const handleFileChange = (e) => setFile(e.target.files[0]);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8001/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setDocumentId(res.data.document_id);
    } catch (err) {
      alert("❌ Upload failed: " + (err.response?.data?.detail || err.message));
    }
    setUploading(false);
  };

  // Ask a question
  const handleAsk = async () => {
    if (!question || !documentId) return;
    setAsking(true);
    const newEntry = { id: Date.now(), question, answer: "⏳ Processing..." };
    
    if (activeConversationId) {
      setConversationMessages((prev) => [...prev, { 
        question, 
        answer: "⏳ Processing...", 
        task_type: "unknown",
        timestamp: new Date().toISOString()
      }]);
    } else {
      setHistory((prev) => [...prev, newEntry]);
    }
    
    setQuestion("");

    try {
      const endpoint = activeConversationId 
        ? `http://localhost:8001/query/${activeConversationId}`
        : "http://localhost:8001/query";
        
      const res = await axios.post(endpoint, {
        question,
        document_id: documentId,
        document_type: "general",
      });
      
      if (activeConversationId) {
        setConversationMessages((prev) =>
          prev.map((msg, index) =>
            index === prev.length - 1
              ? { 
                  ...msg, 
                  answer: res.data.answer, 
                  task_type: res.data.task_type,
                  timestamp: new Date().toISOString()
                }
              : msg
          )
        );
      } else {
        setHistory((prev) =>
          prev.map((h) =>
            h.id === newEntry.id ? { ...h, answer: res.data.answer } : h
          )
        );
      }
    } catch (err) {
      const errorMessage = "❌ Error: " + (err.response?.data?.detail || err.message);
      
      if (activeConversationId) {
        setConversationMessages((prev) =>
          prev.map((msg, index) =>
            index === prev.length - 1 ? { ...msg, answer: errorMessage } : msg
          )
        );
      } else {
        setHistory((prev) =>
          prev.map((h) =>
            h.id === newEntry.id ? { ...h, answer: errorMessage } : h
          )
        );
      }
    }
    setAsking(false);
  };

  // AI Analysis handler
  const handleAnalyze = async () => {
    if (!documentId) return;
    setAnalyzing(true);
    const analysisEntry = {
      id: Date.now(),
      question: "🔍 Comprehensive Analysis",
      answer: "⏳ Analyzing document...",
    };
    
    if (activeConversationId) {
      setConversationMessages((prev) => [...prev, { 
        question: "🔍 Comprehensive Analysis",
        answer: "⏳ Analyzing document...", 
        task_type: "analysis",
        timestamp: new Date().toISOString()
      }]);
    } else {
      setHistory((prev) => [...prev, analysisEntry]);
    }

    try {
      const endpoint = activeConversationId 
        ? `http://localhost:8001/query/${activeConversationId}`
        : "http://localhost:8001/query";
        
      const res = await axios.post(endpoint, {
        question: "Provide a comprehensive analysis of this document",
        document_id: documentId,
        document_type: "general",
      });
      
      if (activeConversationId) {
        setConversationMessages((prev) =>
          prev.map((msg, index) =>
            index === prev.length - 1
              ? { 
                  ...msg, 
                  answer: res.data.answer, 
                  task_type: res.data.task_type
                }
              : msg
          )
        );
      } else {
        setHistory((prev) =>
          prev.map((h) =>
            h.id === analysisEntry.id ? { ...h, answer: res.data.answer } : h
          )
        );
      }
    } catch (err) {
      const errorMessage = "❌ Analysis failed: " + (err.response?.data?.detail || err.message);
      
      if (activeConversationId) {
        setConversationMessages((prev) =>
          prev.map((msg, index) =>
            index === prev.length - 1 ? { ...msg, answer: errorMessage } : msg
          )
        );
      } else {
        setHistory((prev) =>
          prev.map((h) =>
            h.id === analysisEntry.id ? { ...h, answer: errorMessage } : h
          )
        );
      }
    }
    setAnalyzing(false);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'Segoe UI, Arial, sans-serif' }}>
      {/* Conversation Sidebar */}
      <ConversationSidebar 
        onConversationSelect={handleConversationSelect}
        activeConversationId={activeConversationId}
        onNewConversation={handleNewConversation}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
        {/* Header */}
        <header style={{ 
          padding: '16px 24px', 
          borderBottom: '1px solid #e2e8f0', 
          background: '#fff',
          textAlign: 'center'
        }}>
          <h1 style={{ 
            margin: 0, 
            fontSize: '1.8rem', 
            fontWeight: 700,
            color: '#1f2937',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px'
          }}>
            <FiShield /> Document Guardian
          </h1>
          {activeConversationId && (
            <div style={{ fontSize: '0.9rem', color: '#6b7280', marginTop: '4px' }}>
              Active Conversation
            </div>
          )}
        </header>

        {/* Upload Section */}
        <section style={{ 
          padding: '16px 24px', 
          borderBottom: '1px solid #e2e8f0', 
          background: '#fff',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          flexWrap: 'wrap'
        }}>
          <div style={{ position: 'relative' }}>
            <input
              id="file-input"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={handleFileChange}
              disabled={uploading}
              style={{ display: 'none' }}
            />
            <label 
              htmlFor="file-input" 
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 16px',
                border: '2px dashed #cbd5e1',
                borderRadius: '8px',
                background: '#f9fafb',
                cursor: 'pointer',
                fontSize: '0.95rem',
                color: '#374151'
              }}
            >
              <FaUpload />
              <span>{file ? file.name : "Choose a file"}</span>
            </label>
          </div>

          <button 
            onClick={handleUpload} 
            disabled={uploading || !file}
            style={{
              padding: '10px 16px',
              borderRadius: '6px',
              fontSize: '0.95rem',
              fontWeight: 600,
              border: 'none',
              cursor: uploading || !file ? 'not-allowed' : 'pointer',
              background: uploading || !file ? '#cbd5e1' : '#4f46e5',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {uploading ? (
              <>
                <FiClock /> Uploading...
              </>
            ) : (
              <>
                <FiFilePlus /> Upload Document
              </>
            )}
          </button>

          {documentId && (
            <button 
              onClick={handleAnalyze} 
              disabled={analyzing}
              style={{
                padding: '10px 16px',
                borderRadius: '6px',
                fontSize: '0.95rem',
                fontWeight: 600,
                border: 'none',
                cursor: analyzing ? 'not-allowed' : 'pointer',
                background: analyzing ? '#cbd5e1' : '#7c3aed',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {analyzing ? (
                <>
                  <FiClock /> Analyzing...
                </>
              ) : (
                <>
                  <FiBarChart2 /> AI Analysis
                </>
              )}
            </button>
          )}
        </section>

        {/* Messages Display */}
        <section style={{ flex: 1, padding: '20px', overflow: 'hidden' }}>
          <div style={{ height: '100%', overflowY: 'auto', maxWidth: '800px', margin: '0 auto' }}>
            {activeConversationId ? (
              conversationMessages.length === 0 ? (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '3rem', 
                  color: '#6b7280'
                }}>
                  <FiMessageSquare size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                  <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Start a conversation</div>
                  <div style={{ fontSize: '0.9rem' }}>Upload a document and ask questions to begin</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {conversationMessages.map((msg, index) => (
                    <div key={index} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{
                        alignSelf: 'flex-end',
                        maxWidth: '70%',
                        background: '#4f46e5',
                        color: 'white',
                        padding: '12px 16px',
                        borderRadius: '16px 16px 0 16px',
                        fontSize: '0.95rem'
                      }}>
                        {msg.question}
                      </div>
                      <div style={{
                        alignSelf: 'flex-start',
                        maxWidth: '75%',
                        background: '#ffffff',
                        color: '#1f2937',
                        padding: '12px 16px',
                        borderRadius: '16px 16px 16px 0',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.95rem',
                        lineHeight: 1.6
                      }}>
                        <ReactMarkdown>{msg.answer}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              history.length === 0 ? (
                <div style={{ 
                  textAlign: 'center', 
                  padding: '3rem', 
                  color: '#6b7280'
                }}>
                  <FiBookOpen size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                  <div style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Welcome to Document Guardian</div>
                  <div style={{ fontSize: '0.9rem' }}>Create a conversation or upload a document to get started</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {history.map((h) => (
                    <div key={h.id} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <div style={{
                        alignSelf: 'flex-end',
                        maxWidth: '70%',
                        background: '#4f46e5',
                        color: 'white',
                        padding: '12px 16px',
                        borderRadius: '16px 16px 0 16px',
                        fontSize: '0.95rem'
                      }}>
                        {h.question}
                      </div>
                      <div style={{
                        alignSelf: 'flex-start',
                        maxWidth: '75%',
                        background: '#ffffff',
                        color: '#1f2937',
                        padding: '12px 16px',
                        borderRadius: '16px 16px 16px 0',
                        border: '1px solid #e2e8f0',
                        fontSize: '0.95rem',
                        lineHeight: 1.6
                      }}>
                        <ReactMarkdown>{h.answer}</ReactMarkdown>
                      </div>
                    </div>
                  ))}
                </div>
              )
            )}
          </div>
        </section>

        {/* Input Section */}
        <footer style={{ 
          padding: '16px 20px', 
          background: '#fff', 
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          gap: '12px',
          maxWidth: '800px',
          margin: '0 auto',
          width: '100%',
          boxSizing: 'border-box'
        }}>
          <input
            type="text"
            placeholder={activeConversationId ? "Continue your conversation..." : "Ask about your document..."}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={!documentId || asking}
            onKeyPress={(e) => e.key === "Enter" && handleAsk()}
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: '2px solid #e2e8f0',
              fontSize: '1rem'
            }}
          />
          <button
            onClick={handleAsk}
            disabled={!documentId || !question || asking}
            style={{
              background: (!documentId || !question || asking) ? '#cbd5e1' : '#4f46e5',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              padding: '12px 24px',
              fontSize: '1rem',
              fontWeight: 600,
              cursor: (!documentId || !question || asking) ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {asking ? (
              <>
                <FiClock /> Thinking...
              </>
            ) : (
              <>
                <FaQuestionCircle /> Ask
              </>
            )}
          </button>
        </footer>
      </div>
    </div>
  );
}

export default FinalApp;
