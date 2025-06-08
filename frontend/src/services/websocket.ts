import config, { getWebSocketUrl } from '@/config'
import type { WebSocketMessage } from '@/types'

export interface WebSocketManagerOptions {
  url: string
  reconnectAttempts?: number
  reconnectDelay?: number
  onConnect?: () => void
  onDisconnect?: () => void
  onMessage?: (message: WebSocketMessage) => void
  onError?: (error: Event) => void
}

export class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string
  private reconnectAttempts: number
  private maxReconnectAttempts: number
  private reconnectDelay: number
  private listeners: Map<string, ((data: any) => void)[]> = new Map()
  public options: WebSocketManagerOptions

  constructor(options: WebSocketManagerOptions) {
    this.url = options.url
    this.maxReconnectAttempts = options.reconnectAttempts ?? 5
    this.reconnectAttempts = 0
    this.reconnectDelay = options.reconnectDelay ?? 1000
    this.options = options
  }

  connect(): void {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.options.onConnect?.()
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        this.options.onDisconnect?.()
        
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.options.onError?.(error)
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.handleMessage(message)
          this.options.onMessage?.(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1) // Exponential backoff

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      this.connect()
    }, delay)
  }

  private handleMessage(message: WebSocketMessage): void {
    const typeListeners = this.listeners.get(message.type) || []
    typeListeners.forEach(listener => listener(message.payload))
  }

  send(type: 'chat' | 'notification' | 'status' | 'error', payload: any): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message: WebSocketMessage = {
        type,
        payload,
        timestamp: new Date(),
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  sendChatMessage(content: string): void {
    this.send('chat', { content })
  }

  on(type: string, listener: (data: any) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, [])
    }
    this.listeners.get(type)!.push(listener)

    // Return unsubscribe function
    return () => {
      const typeListeners = this.listeners.get(type)
      if (typeListeners) {
        const index = typeListeners.indexOf(listener)
        if (index > -1) {
          typeListeners.splice(index, 1)
        }
      }
    }
  }

  off(type: string, listener?: (data: any) => void): void {
    if (!listener) {
      this.listeners.delete(type)
    } else {
      const typeListeners = this.listeners.get(type)
      if (typeListeners) {
        const index = typeListeners.indexOf(listener)
        if (index > -1) {
          typeListeners.splice(index, 1)
        }
      }
    }
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting')
      this.ws = null
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get readyState(): number | null {
    return this.ws?.readyState ?? null
  }
}

// Create a default instance
export const webSocketManager = new WebSocketManager({
  url: getWebSocketUrl(),
  reconnectAttempts: config.websocket.reconnectAttempts,
  reconnectDelay: config.websocket.reconnectDelay,
})

export default webSocketManager