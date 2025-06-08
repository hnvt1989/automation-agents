import { useState, useRef, KeyboardEvent, ChangeEvent } from 'react'
import { Send, Paperclip, X } from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'
import { formatFileSize } from '@/utils'

interface ChatInputProps {
  onSendMessage: (content: string, files?: File[]) => void
  disabled?: boolean
}

const ChatInput = ({ onSendMessage, disabled = false }: ChatInputProps) => {
  const [input, setInput] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { sendTyping } = useWebSocket()
  const typingTimeoutRef = useRef<NodeJS.Timeout>()

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setInput(value)

    // Send typing indicator
    sendTyping(true)
    
    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }
    
    // Stop typing indicator after 1 second of no typing
    typingTimeoutRef.current = setTimeout(() => {
      sendTyping(false)
    }, 1000)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = () => {
    if (!input.trim() && files.length === 0) return
    if (disabled) return

    // Stop typing indicator
    sendTyping(false)
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current)
    }

    onSendMessage(input.trim(), files.length > 0 ? files : undefined)
    setInput('')
    setFiles([])
  }

  const handleFileSelect = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    setFiles(prev => [...prev, ...selectedFiles])
    
    // Clear the input so the same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const maxFileSize = 10 * 1024 * 1024 // 10MB
  const hasOversizedFiles = files.some(file => file.size > maxFileSize)

  return (
    <div className="input-area">
      {files.length > 0 && (
        <div className="file-preview">
          {files.map((file, index) => (
            <div 
              key={`${file.name}-${index}`} 
              className={`file-preview-item ${file.size > maxFileSize ? 'oversized' : ''}`}
            >
              <span className="file-name">{file.name}</span>
              <span className="file-size">({formatFileSize(file.size)})</span>
              {file.size > maxFileSize && (
                <span className="file-error">Too large</span>
              )}
              <button
                onClick={() => removeFile(index)}
                className="remove-file"
                aria-label={`Remove ${file.name}`}
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      
      <div className="input-container">
        <button
          onClick={handleFileSelect}
          className="attach-button"
          disabled={disabled}
          title="Attach files"
        >
          <Paperclip size={18} />
        </button>
        
        <input
          type="text"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? 'Connecting...' : 'Type your message...'}
          disabled={disabled}
          className="message-input"
        />
        
        <button
          onClick={handleSend}
          disabled={disabled || (!input.trim() && files.length === 0) || hasOversizedFiles}
          className="send-button"
          title="Send message"
        >
          <Send size={18} />
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept=".txt,.md,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.webp"
      />
    </div>
  )
}

export default ChatInput