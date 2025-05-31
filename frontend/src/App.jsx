import React, { useState } from 'react';
import './App.css';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState(null);

  const handleSend = () => {
    if (input.trim() || file) {
      setMessages([...messages, { text: input, file }]);
      setInput('');
      setFile(null);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, idx) => (
          <div key={idx} className="message">
            <span>{m.text}</span>
            {m.file && <span className="attachment">\u{1F4CE} {m.file.name}</span>}
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
        />
        <label className="file-input">
          \u{1F4CE}
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
            style={{ display: 'none' }}
          />
        </label>
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
}
