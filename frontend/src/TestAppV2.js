import React, { useState } from 'react';
import axios from 'axios';
import ConversationSidebar from './ConversationSidebar';
import './App.css';

// Test step 2: Basic App with ConversationSidebar imported but not used
const TestAppV2 = () => {
  const [response, setResponse] = useState('Test App V2 - ConversationSidebar import test');

  return (
    <div className="app">
      <h1>Document Guardian - Test V2</h1>
      <p>{response}</p>
      <div>
        <p>Testing app with ConversationSidebar imported but not rendered</p>
        <p>If this displays correctly, the import works</p>
        <p>ConversationSidebar imported: {ConversationSidebar ? 'YES' : 'NO'}</p>
      </div>
    </div>
  );
};

export default TestAppV2;
