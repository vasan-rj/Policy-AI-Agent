import React, { useState } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import './App.css';
import './markdown-styles.css';

function App() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [originalSections, setOriginalSections] = useState([]);
  const [taskType, setTaskType] = useState('');
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
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

  const handleAnalyze = async () => {
    if (!policyId) return;
    setAnalyzing(true);
    setAnswer('Analyzing your policy document...');
    try {
      const res = await axios.post('http://localhost:8001/analyze', {
        policy_id: policyId,
      });
      setAnswer(res.data.answer);
      setOriginalSections(res.data.original_sections || []);
      setTaskType(res.data.task_type);
    } catch (err) {
      setAnswer('Analysis failed: ' + (err.response?.data?.detail || err.message));
      setOriginalSections([]);
    }
    setAnalyzing(false);
  };

  const getTaskTypeIcon = () => {
    if (taskType === 'compliance') return '⚖️';
    if (taskType === 'translation') return '💬';
    if (taskType === 'analysis') return '📊';
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
          <h3>Upload Complete</h3>
          <p><strong>File:</strong> {uploadInfo.filename}</p>
          {uploadInfo.total_chunks && (
            <>
              <p><strong>Chunks created:</strong> {uploadInfo.total_chunks}</p>
              <p><strong>Characters processed:</strong> {uploadInfo.total_characters}</p>
            </>
          )}
          <div className="analysis-section">
            <button 
              onClick={handleAnalyze} 
              disabled={analyzing || !policyId}
              className={analyzing ? 'loading analysis-btn' : 'analysis-btn'}
            >
              {analyzing ? 'Analyzing...' : '📊 AI Analysis'}
            </button>
          </div>
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
        <h3> Answer</h3>
        <div className="answer-box">
          {answer && (
            <div className="answer-content">
              <div className="answer-text markdown-content">
                <ReactMarkdown>{answer}</ReactMarkdown>
              </div>
              {taskType && (
                <div className="task-type">
                  {/* <small>Analysis type: {getTaskTypeIcon()} {taskType === 'compliance' ? 'Compliance Review' : taskType === 'translation' ? 'Plain English Translation' : 'Information Retrieval'}</small> */}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Relevant policy sections are hidden as requested */}
    </div>
  );
}

export default App;
