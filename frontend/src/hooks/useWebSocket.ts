import { useEffect, useCallback, useRef } from 'react'
import { webSocketManager } from '@/services/websocket'
import { useAppStore } from '@/store'
import type { ChatMessage } from '@/types'

export function useWebSocket() {
  const {
    addMessage,
    updateMessage,
    setConnectionStatus,
    setTypingStatus,
    isConnected,
  } = useAppStore()
  
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    // Configure WebSocket manager
    webSocketManager.options = {
      ...webSocketManager.options,
      onConnect: () => {
        setConnectionStatus(true)
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
        }
      },
      onDisconnect: () => {
        setConnectionStatus(false)
        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (!webSocketManager.isConnected) {
            webSocketManager.connect()
          }
        }, 3000)
      },
      onError: (error) => {
        console.error('WebSocket error:', error)
        setConnectionStatus(false)
      },
    }

    // Connect
    webSocketManager.connect()

    // Set up message listeners
    const unsubscribeChat = webSocketManager.on('chat', (data) => {
      if (data.type === 'message') {
        const message: ChatMessage = {
          id: crypto.randomUUID(),
          content: data.content,
          role: 'assistant',
          timestamp: new Date(),
          status: 'sent',
        }
        addMessage(message)
      } else if (data.type === 'typing') {
        setTypingStatus(data.isTyping)
      } else if (data.type === 'message_update') {
        updateMessage(data.messageId, data.updates)
      }
    })

    const unsubscribeStatus = webSocketManager.on('status', (data) => {
      if (data.type === 'connection') {
        setConnectionStatus(data.connected)
      }
    })

    const unsubscribeError = webSocketManager.on('error', (data) => {
      console.error('WebSocket error message:', data)
      // Handle error messages from server
    })

    return () => {
      unsubscribeChat()
      unsubscribeStatus()
      unsubscribeError()
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      webSocketManager.disconnect()
    }
  }, [addMessage, updateMessage, setConnectionStatus, setTypingStatus])

  const sendMessage = useCallback(
    (content: string, fileAttachments?: File[]) => {
      if (!webSocketManager.isConnected) {
        console.warn('Cannot send message: WebSocket not connected')
        return null
      }

      // Create user message
      const userMessage: ChatMessage = {
        id: crypto.randomUUID(),
        content,
        role: 'user',
        timestamp: new Date(),
        status: 'sending',
        metadata: fileAttachments ? {
          fileAttachments: fileAttachments.map(file => ({
            id: crypto.randomUUID(),
            name: file.name,
            size: file.size,
            type: file.type,
          }))
        } : undefined,
      }

      // Add to store
      addMessage(userMessage)

      // Send via WebSocket
      webSocketManager.sendChatMessage(content)

      // Update status to sent
      setTimeout(() => {
        updateMessage(userMessage.id, { status: 'sent' })
      }, 100)

      return userMessage.id
    },
    [addMessage, updateMessage]
  )

  const sendTyping = useCallback((isTyping: boolean) => {
    if (webSocketManager.isConnected) {
      webSocketManager.send('status', { type: 'typing', isTyping })
    }
  }, [])

  const reconnect = useCallback(() => {
    if (!webSocketManager.isConnected) {
      webSocketManager.connect()
    }
  }, [])

  return {
    isConnected,
    sendMessage,
    sendTyping,
    reconnect,
    connectionState: webSocketManager.readyState,
  }
}

export default useWebSocket