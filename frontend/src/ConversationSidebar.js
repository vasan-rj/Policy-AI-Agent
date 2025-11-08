import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiPlus, FiMessageSquare, FiEdit3, FiTrash2 } from 'react-icons/fi';
import './ConversationSidebar.css';

const ConversationSidebar = ({ 
  onConversationSelect, 
  activeConversationId, 
  onNewConversation 
}) => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const response = await axios.get('http://localhost:8001/conversations');
      if (response.data.status === 'success') {
        setConversations(response.data.conversations);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const createNewConversation = async () => {
    if (!newTitle.trim()) return;
    
    try {
      const response = await axios.post('http://localhost:8001/conversations', {
        title: newTitle,
        document_type: 'general'
      });
      
      if (response.data.status === 'success') {
        const newConversation = response.data.conversation;
        setConversations(prev => [newConversation, ...prev]);
        setShowModal(false);
        setNewTitle('');
        onNewConversation(newConversation.id);
        onConversationSelect(newConversation.id);
      }
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const deleteConversation = async (conversationId) => {
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return;
    }
    
    try {
      await axios.delete(`http://localhost:8001/conversations/${conversationId}`);
      setConversations(prev => prev.filter(c => c.id !== conversationId));
      
      if (activeConversationId === conversationId) {
        onConversationSelect(null);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  const updateConversationTitle = async (conversationId, title) => {
    try {
      await axios.put(`http://localhost:8001/conversations/${conversationId}`, {
        title: title
      });
      
      setConversations(prev => prev.map(c => 
        c.id === conversationId ? { ...c, title } : c
      ));
      setEditingId(null);
    } catch (error) {
      console.error('Failed to update conversation title:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return 'Today';
    if (diffDays === 2) return 'Yesterday';
    if (diffDays <= 7) return `${diffDays - 1} days ago`;
    return date.toLocaleDateString();
  };

  const handleTitleEdit = (conversationId, currentTitle) => {
    setEditingId(conversationId);
    setNewTitle(currentTitle);
  };

  const handleTitleSave = (conversationId) => {
    if (newTitle.trim()) {
      updateConversationTitle(conversationId, newTitle.trim());
    } else {
      setEditingId(null);
    }
    setNewTitle('');
  };

  const handleKeyPress = (e, conversationId) => {
    if (e.key === 'Enter') {
      handleTitleSave(conversationId);
    } else if (e.key === 'Escape') {
      setEditingId(null);
      setNewTitle('');
    }
  };

  return (
    <div className="conversation-sidebar">
      <div className="sidebar-header">
        <button 
          className="new-conversation-btn"
          onClick={() => setShowModal(true)}
        >
          <FiPlus size={16} />
          New Conversation
        </button>
      </div>

      <div className="conversations-list">
        {loading ? (
          <div className="empty-state">
            <div>Loading conversations...</div>
          </div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">
              <FiMessageSquare />
            </div>
            <div>No conversations yet</div>
            <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
              Create your first conversation to get started
            </div>
          </div>
        ) : (
          conversations.map(conversation => (
            <div 
              key={conversation.id}
              className={`conversation-item ${activeConversationId === conversation.id ? 'active' : ''}`}
              onClick={() => onConversationSelect(conversation.id)}
            >
              <div className="conversation-title">
                {editingId === conversation.id ? (
                  <input
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    onBlur={() => handleTitleSave(conversation.id)}
                    onKeyDown={(e) => handleKeyPress(e, conversation.id)}
                    className="form-input"
                    style={{ padding: '0.25rem', fontSize: '0.9rem' }}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  conversation.title
                )}
              </div>
              <div className="conversation-meta">
                <span>{formatDate(conversation.updated_at)}</span>
                <span>{conversation.message_count} messages</span>
                <div className="conversation-actions">
                  <button
                    className="action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTitleEdit(conversation.id, conversation.title);
                    }}
                    title="Edit title"
                  >
                    <FiEdit3 size={12} />
                  </button>
                  <button
                    className="action-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteConversation(conversation.id);
                    }}
                    title="Delete conversation"
                  >
                    <FiTrash2 size={12} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* New Conversation Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">New Conversation</h3>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">Conversation Title</label>
                <input
                  type="text"
                  className="form-input"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Enter a title for your conversation..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') createNewConversation();
                    if (e.key === 'Escape') setShowModal(false);
                  }}
                  autoFocus
                />
              </div>
            </div>
            <div className="modal-actions">
              <button 
                className="btn btn-secondary"
                onClick={() => setShowModal(false)}
              >
                Cancel
              </button>
              <button 
                className="btn btn-primary"
                onClick={createNewConversation}
                disabled={!newTitle.trim()}
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConversationSidebar;
