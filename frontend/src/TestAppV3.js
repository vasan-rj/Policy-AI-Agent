import React, { useState } from 'react';
import axios from 'axios';
import ConversationSidebar from './ConversationSidebar';

// Test step 3: Basic App with ConversationSidebar imported and minimal styling
const TestAppV3 = () => {
  const [response, setResponse] = useState('Test App V3 - ConversationSidebar rendering test');

  const handleTest = () => {
    setResponse('ConversationSidebar component test clicked!');
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1>Document Guardian - Test V3</h1>
      <p>{response}</p>
      <button onClick={handleTest} style={{ margin: '10px', padding: '10px' }}>
        Test Button
      </button>
      <div>
        <p>Testing app with ConversationSidebar rendered</p>
        <div style={{ border: '1px solid #ccc', height: '200px', width: '300px' }}>
          <ConversationSidebar 
            onConversationSelect={() => console.log('Conversation selected')}
            activeConversationId={null}
            onNewConversation={() => console.log('New conversation')}
          />
        </div>
      </div>
    </div>
  );
};

export default TestAppV3;
