import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const SimpleApp = () => {
  const [file, setFile] = useState(null);
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');
  const [chatHistory, setChatHistory] = useState([]);

  const handleFileUpload = async () => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    const formData = new FormData();
    formData.append('file', file);
    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadStatus(response.data.message);
    } catch (error) {
      console.error('Error uploading file:', error);
      setUploadStatus('Error uploading file');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAsk = async () => {
    if (!query) {
      alert('Please enter a query.');
      return;
    }

    setIsLoading(true);
    try {
      const result = await axios.post('http://localhost:8000/ask', { query });
      const newResponse = result.data.response;
      setResponse(newResponse);
      
      // Add to chat history
      setChatHistory(prev => [...prev, 
        { type: 'user', content: query },
        { type: 'assistant', content: newResponse }
      ]);
      setQuery('');
    } catch (error) {
      console.error('Error asking query:', error);
      setResponse('Error processing query');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>Simple Document Guardian</h1>
      
      <div className="upload-section">
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          accept=".pdf,.txt,.docx"
        />
        <button onClick={handleFileUpload} disabled={isLoading}>
          {isLoading ? 'Uploading...' : 'Upload Document'}
        </button>
        {uploadStatus && <p>{uploadStatus}</p>}
      </div>

      <div className="query-section">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask a question about your document..."
          onKeyPress={(e) => e.key === 'Enter' && handleAsk()}
        />
        <button onClick={handleAsk} disabled={isLoading}>
          {isLoading ? 'Processing...' : 'Ask'}
        </button>
      </div>

      {response && (
        <div className="response-section">
          <h3>Response:</h3>
          <p>{response}</p>
        </div>
      )}

      {chatHistory.length > 0 && (
        <div className="chat-history">
          <h3>Chat History:</h3>
          {chatHistory.map((message, index) => (
            <div key={index} className={`message ${message.type}`}>
              <strong>{message.type === 'user' ? 'You:' : 'Assistant:'}</strong>
              <p>{message.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default SimpleApp;
