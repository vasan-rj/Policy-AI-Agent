import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [originalSections, setOriginalSections] = useState([]);
  const [taskType, setTaskType] = useState('');
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [policyId, setPolicyId] = useState('');
  const [uploadInfo, setUploadInfo] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post('http://localhost:8001/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPolicyId(res.data.policy_id);
      setUploadInfo(res.data);
      setAnswer('Document uploaded and processed successfully!');
      setOriginalSections([]);
    } catch (err) {
      setAnswer('Upload failed: ' + (err.response?.data?.detail || err.message));
      setUploadInfo(null);
    }
    setUploading(false);
  };

  const handleAsk = async () => {
    if (!question || !policyId) return;
    setAsking(true);
    setAnswer('Processing your question...');
    try {
      const res = await axios.post('http://localhost:8001/query', {
        question,
        policy_id: policyId,
      });
      setAnswer(res.data.answer);
      setOriginalSections(res.data.original_sections || []);
      setTaskType(res.data.task_type);
    } catch (err) {
      setAnswer('Query failed: ' + (err.response?.data?.detail || err.message));
      setOriginalSections([]);
    }
    setAsking(false);
  };

  const getTaskTypeIcon = () => {
    if (taskType === 'compliance') return '⚖️';
    if (taskType === 'translation') return '💬';
    return '🤖';
  };

  return (
    <div className="container">
      <h1>🛡️ Privacy Guardian</h1>
      <p className="subtitle">AI-powered privacy policy analysis and compliance checking</p>
      
      <div className="upload-section">
        <input 
          type="file" 
          accept=".pdf,.docx,.txt" 
          onChange={handleFileChange}
          disabled={uploading}
        />
        <button 
          onClick={handleUpload} 
          disabled={uploading || !file}
          className={uploading ? 'loading' : ''}
        >
          {uploading ? 'Processing...' : 'Upload Policy'}
        </button>
      </div>

      {uploadInfo && (
        <div className="upload-info">
          <h3>✅ Upload Complete</h3>
          <p><strong>File:</strong> {uploadInfo.filename}</p>
          {uploadInfo.total_chunks && (
            <>
              <p><strong>Chunks created:</strong> {uploadInfo.total_chunks}</p>
              <p><strong>Characters processed:</strong> {uploadInfo.total_characters}</p>
            </>
          )}
        </div>
      )}
      
      <div className="qa-section">
        <input
          type="text"
          placeholder="Ask about your privacy policy (e.g., 'Who can see my data?' or 'Is this GDPR compliant?')"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          disabled={!policyId || asking}
          onKeyPress={e => e.key === 'Enter' && handleAsk()}
        />
        <button 
          onClick={handleAsk} 
          disabled={!policyId || !question || asking}
          className={asking ? 'loading' : ''}
        >
          {asking ? 'Thinking...' : 'Ask'}
        </button>
      </div>
      
      <div className="answer-section">
        <h3>{getTaskTypeIcon()} Answer</h3>
        <div className="answer-box">
          {answer && (
            <div className="answer-content">
              <div className="answer-text">{answer}</div>
              {taskType && (
                <div className="task-type">
                  <small>Analysis type: {taskType === 'compliance' ? 'Compliance Review' : 'Plain English Translation'}</small>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {originalSections.length > 0 && (
        <div className="sources-section">
          <h3>📄 Relevant Policy Sections</h3>
          <div className="sources-container">
            {originalSections.map((section, index) => (
              <div 
                key={index} 
                className="source-section"
                style={{
                  borderLeft: `4px solid rgba(79, 70, 229, ${section.relevance || 0.5})`,
                  backgroundColor: `rgba(79, 70, 229, ${(section.relevance || 0.5) * 0.1})`
                }}
              >
                <div className="relevance-score">
                  Relevance: {Math.round((section.relevance || 0.5) * 100)}%
                </div>
                <div className="source-text">{section.text}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
