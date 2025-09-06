import React, { useState, useRef } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import {
  FiFilePlus,
  FiBarChart2,
  FiBookOpen,
  FiShield,
  FiClock,
} from "react-icons/fi";
import { FaQuestionCircle, FaUpload } from "react-icons/fa";
import "./App.css";
import "./markdown-styles.css";

function App() {
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [history, setHistory] = useState([]); // QnA history
  const [policyId, setPolicyId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [asking, setAsking] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [showHistory, setShowHistory] = useState(true);

  const qaRefs = useRef({}); // map: history index -> ref

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
      setPolicyId(res.data.policy_id);
    } catch (err) {
      alert("❌ Upload failed: " + (err.response?.data?.detail || err.message));
    }
    setUploading(false);
  };

  // Ask a question
  const handleAsk = async () => {
    if (!question || !policyId) return;
    setAsking(true);
    const newEntry = { id: Date.now(), question, answer: "⏳ Processing..." };
    setHistory((prev) => [...prev, newEntry]);
    setQuestion("");

    try {
      const res = await axios.post("http://localhost:8001/query", {
        question,
        policy_id: policyId,
      });
      setHistory((prev) =>
        prev.map((h) =>
          h.id === newEntry.id ? { ...h, answer: res.data.answer } : h
        )
      );
    } catch (err) {
      setHistory((prev) =>
        prev.map((h) =>
          h.id === newEntry.id
            ? {
              ...h,
              answer:
                "❌ Query failed: " +
                (err.response?.data?.detail || err.message),
            }
            : h
        )
      );
    }
    setAsking(false);
  };

  // Run AI Analysis
  const handleAnalyze = async () => {
    if (!policyId) return;
    setAnalyzing(true);
    const newEntry = {
      id: Date.now(),
      question: "AI Analysis",
      answer: "⏳ Analyzing...",
    };
    setHistory((prev) => [...prev, newEntry]);

    try {
      const res = await axios.post("http://localhost:8001/analyze", {
        policy_id: policyId,
      });
      setHistory((prev) =>
        prev.map((h) =>
          h.id === newEntry.id ? { ...h, answer: res.data.answer } : h
        )
      );
    } catch (err) {
      setHistory((prev) =>
        prev.map((h) =>
          h.id === newEntry.id
            ? {
              ...h,
              answer:
                "❌ Analysis failed: " +
                (err.response?.data?.detail || err.message),
            }
            : h
        )
      );
    }
    setAnalyzing(false);
  };

  // Scroll to Q&A block when clicked in history sidebar
  const scrollToQA = (id) => {
    const el = qaRefs.current[id];
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>

      <div className="app-container">
        {/* Sidebar */}
        <aside className={`sidebar ${showHistory ? "" : "hidden"}`}>
          <h3>
            <FiBookOpen style={{ marginRight: "8px" }} /> Q&A History
          </h3>
          <ul>
            {history.map((h) => (
              <li key={h.id} onClick={() => scrollToQA(h.id)}>
                {h.question.length > 20 ? h.question.slice(0, 20) + "..." : h.question}
              </li>
            ))}
          </ul>
        </aside>


        {/* Main content */}

        <main className={`main-content ${showHistory ? "" : "full"}`}>
          <button className="toggle-btn" onClick={() => setShowHistory(!showHistory)}>
            {showHistory ? "⮜" : "⮞"}
          </button>
          <header className="header">
            <h1>
              <FiShield style={{ marginRight: "8px" }} /> Privacy Guardian
            </h1>
          </header>

          {/* Upload + Actions */}
          <section className="upload-section">
            <div className="file-upload">
              <label htmlFor="file-input" className="file-upload-label">
                <FaUpload className="upload-icon" />
                <span>{file ? file.name : "Choose a file"}</span>
              </label>
              <input
                id="file-input"
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileChange}
                disabled={uploading}
              />
            </div>

            <button onClick={handleUpload} disabled={uploading || !file}>
              {uploading ? (
                <>
                  <FiClock style={{ marginRight: "6px" }} /> Uploading...
                </>
              ) : (
                <>
                  <FiFilePlus style={{ marginRight: "6px" }} /> Upload Policy
                </>
              )}
            </button>

            {policyId && (
              <button onClick={handleAnalyze} disabled={analyzing}>
                {analyzing ? (
                  <>
                    <FiClock style={{ marginRight: "6px" }} /> Analyzing...
                  </>
                ) : (
                  <>
                    <FiBarChart2 style={{ marginRight: "6px" }} /> AI Analysis
                  </>
                )}
              </button>
            )}
          </section>

          {/* Q&A Section */}
          <section className="qa-section">
            <div className="history-box">
              {history.map((h) => (
                <div
                  key={h.id}
                  ref={(el) => (qaRefs.current[h.id] = el)}
                  className="qa-pair"
                >
                  <p className="question">
                    <FaQuestionCircle
                      style={{ marginRight: "6px", color: "#4f46e5" }}
                    />
                    {h.question}
                  </p>
                  <div className="answer markdown-content">
                    <ReactMarkdown>{h.answer}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Footer Input */}
          <footer className="input-section">
            <input
              type="text"
              placeholder="Ask about your policy..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={!policyId || asking}
              onKeyPress={(e) => e.key === "Enter" && handleAsk()}
            />
            <button
              onClick={handleAsk}
              disabled={!policyId || !question || asking}
            >
              {asking ? (
                <>
                  <FiClock style={{ marginRight: "6px" }} /> Thinking...
                </>
              ) : (
                <>
                  <FaQuestionCircle style={{ marginRight: "6px" }} /> Ask
                </>
              )}
            </button>
          </footer>
        </main>
      </div>
    </>
  );
}

export default App;
