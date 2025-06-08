import { useRef, useEffect } from 'react'
import { useAppStore } from '@/store'
import { useWebSocket } from '@/hooks/useWebSocket'
import MessageList from './MessageList'
import ChatInput from './ChatInput'
import './styles.css'

const ChatPanel = () => {
  const messages = useAppStore((state) => state.messages)
  const isTyping = useAppStore((state) => state.isTyping)
  const { isConnected, sendMessage } = useWebSocket()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSendMessage = (content: string, fileAttachments?: File[]) => {
    if (!content.trim() || !isConnected) return
    sendMessage(content, fileAttachments)
  }

  return (
    <div className="assistant-panel">
      <div className="assistant-header">
        <div className="assistant-title">Assistant</div>
        <div className="connection-status">
          <div 
            className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}
            title={isConnected ? 'Connected' : 'Disconnected'}
          />
          <span className="status-text">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      <div className="messages">
        {messages.length === 0 && (
          <div className="message assistant welcome-message">
            <h3>👋 Welcome to Automation Agents!</h3>
            <p>I'm here to help you manage your tasks, documents, notes, and daily logs. Here are some things you can try:</p>
            <ul>
              <li>Ask me to analyze your current workload</li>
              <li>Request help with organizing your tasks</li>
              <li>Upload files for processing</li>
              <li>Get insights about your productivity</li>
            </ul>
            <p>How can I assist you today?</p>
          </div>
        )}
        
        <MessageList messages={messages} />
        
        {isTyping && (
          <div className="message assistant typing-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="typing-text">Assistant is typing...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      <ChatInput 
        onSendMessage={handleSendMessage}
        disabled={!isConnected}
      />
    </div>
  )
}

export default ChatPanel