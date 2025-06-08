import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check, FileText, ExternalLink } from 'lucide-react'
import { useState } from 'react'
import { copyToClipboard, formatRelativeTime } from '@/utils'
import type { ChatMessage } from '@/types'

interface MessageListProps {
  messages: ChatMessage[]
}

interface MessageItemProps {
  message: ChatMessage
}

const MessageItem = ({ message }: MessageItemProps) => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  const handleCopyCode = async (code: string) => {
    const success = await copyToClipboard(code)
    if (success) {
      setCopiedCode(code)
      setTimeout(() => setCopiedCode(null), 2000)
    }
  }

  const renderMarkdown = (content: string) => {
    return (
      <ReactMarkdown
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            const codeString = String(children).replace(/\n$/, '')
            const isInline = !className || !match
            
            if (!isInline && match) {
              return (
                <div className="code-block">
                  <div className="code-header">
                    <span className="language">{match[1]}</span>
                    <button
                      onClick={() => handleCopyCode(codeString)}
                      className="copy-button"
                      title="Copy code"
                    >
                      {copiedCode === codeString ? <Check size={16} /> : <Copy size={16} />}
                    </button>
                  </div>
                  <SyntaxHighlighter
                    style={vscDarkPlus as any}
                    language={match[1]}
                    PreTag="div"
                  >
                    {codeString}
                  </SyntaxHighlighter>
                </div>
              )
            }
            
            return (
              <code className="inline-code" {...props}>
                {children}
              </code>
            )
          },
          a({ href, children, ...props }) {
            return (
              <a 
                href={href} 
                target="_blank" 
                rel="noopener noreferrer"
                className="message-link"
                {...props}
              >
                {children}
                <ExternalLink size={12} />
              </a>
            )
          },
          blockquote({ children, ...props }) {
            return (
              <blockquote className="message-blockquote" {...props}>
                {children}
              </blockquote>
            )
          },
        }}
      >
        {content}
      </ReactMarkdown>
    )
  }

  return (
    <div className={`message ${message.role}`}>
      <div className="message-content">
        {message.role === 'assistant' ? (
          renderMarkdown(message.content)
        ) : (
          <div className="user-message-content">
            {message.content}
            {message.metadata?.fileAttachments && (
              <div className="file-attachments">
                {message.metadata.fileAttachments.map((file) => (
                  <div key={file.id} className="file-attachment">
                    <FileText size={16} />
                    <span>{file.name}</span>
                    <span className="file-size">
                      ({Math.round(file.size / 1024)}KB)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      
      <div className="message-meta">
        <span className="message-time">
          {formatRelativeTime(message.timestamp)}
        </span>
        {message.status && (
          <span className={`message-status ${message.status}`}>
            {message.status === 'sending' && '⏳'}
            {message.status === 'sent' && '✓'}
            {message.status === 'error' && '❌'}
          </span>
        )}
      </div>
    </div>
  )
}

const MessageList = ({ messages }: MessageListProps) => {
  return (
    <>
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
    </>
  )
}

export default MessageList