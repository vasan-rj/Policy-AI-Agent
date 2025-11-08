import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Test step 1: Basic App with only ConversationSidebar import (not used)
const TestAppV1 = () => {
  const [response, setResponse] = useState('Test App V1 - Basic import test');

  return (
    <div className="app">
      <h1>Document Guardian - Test V1</h1>
      <p>{response}</p>
      <div>
        <p>Testing basic app without using ConversationSidebar component</p>
        <p>If this displays correctly, the basic app structure works</p>
      </div>
    </div>
  );
};

export default TestAppV1;
