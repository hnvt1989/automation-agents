// Core application types
export interface WorkspaceItem {
  id: string
  name: string
  description?: string
  type: 'task' | 'document' | 'note' | 'log'
  lastModified: Date
  status?: string
  content?: string
  filePath?: string
  priority?: 'high' | 'medium' | 'low'
}

// Chat types
export interface ChatMessage {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
  status?: 'sending' | 'sent' | 'error'
  metadata?: {
    fileAttachments?: FileAttachment[]
    citations?: Citation[]
  }
}

export interface FileAttachment {
  id: string
  name: string
  size: number
  type: string
  url?: string
}

export interface Citation {
  source: string
  content: string
  url?: string
}

// Task types
export interface Task extends WorkspaceItem {
  type: 'task'
  priority: 'high' | 'medium' | 'low'
  status: 'todo' | 'in_progress' | 'completed' | 'cancelled'
  dueDate?: Date
  assignee?: string
  tags?: string[]
}

// Document types
export interface Document extends WorkspaceItem {
  type: 'document'
  content: string
  format: 'markdown' | 'text' | 'rich'
  version?: number
  tags?: string[]
}

// Note types
export interface Note extends WorkspaceItem {
  type: 'note'
  content: string
  tags?: string[]
  category?: string
}

// Log types
export interface DailyLog extends WorkspaceItem {
  type: 'log'
  date: Date
  content: string
  mood?: 'positive' | 'neutral' | 'negative'
  productivity?: number // 1-10 scale
  tags?: string[]
}

// Configuration types
export interface AppConfig {
  paths: {
    localFileDir: string
    knowledgeBaseDir: string
  }
  preferences: {
    theme: 'light' | 'dark' | 'auto'
    language: string
    autoSave: boolean
    notifications: boolean
  }
  api: {
    baseUrl: string
    timeout: number
  }
}

// API types
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
}

// WebSocket types
export interface WebSocketMessage {
  type: 'chat' | 'notification' | 'status' | 'error'
  payload: any
  timestamp: Date
}

// UI types
export interface TabConfig {
  id: string
  label: string
  icon?: string
  component: React.ComponentType
  badge?: number
}

export interface ModalState {
  isOpen: boolean
  mode: 'add' | 'edit' | 'view'
  item?: WorkspaceItem
}

// Form types
export interface FormField {
  name: string
  label: string
  type: 'text' | 'textarea' | 'select' | 'date' | 'file' | 'checkbox'
  required?: boolean
  options?: { value: string; label: string }[]
  validation?: {
    pattern?: RegExp
    min?: number
    max?: number
    custom?: (value: any) => string | null
  }
}

// Error types
export interface AppError {
  code: string
  message: string
  details?: any
  timestamp: Date
}

// Search and filter types
export interface SearchFilters {
  query?: string
  type?: WorkspaceItem['type'][]
  status?: string[]
  dateRange?: {
    start: Date
    end: Date
  }
  tags?: string[]
}

export interface SortOption {
  field: keyof WorkspaceItem
  direction: 'asc' | 'desc'
}

// Store types (for Zustand)
export interface AppState {
  // Chat state
  messages: ChatMessage[]
  isConnected: boolean
  isTyping: boolean
  
  // Workspace state
  tasks: Task[]
  documents: Document[]
  notes: Note[]
  logs: DailyLog[]
  activeTab: string
  
  // UI state
  modal: ModalState
  isLoading: boolean
  errors: AppError[]
  
  // Configuration
  config: AppConfig
  
  // Search and filters
  searchFilters: SearchFilters
  sortOption: SortOption
}

// Hook types
export interface UseWebSocketOptions {
  url: string
  reconnectAttempts?: number
  reconnectDelay?: number
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Error) => void
}

export interface UseApiOptions {
  baseURL?: string
  timeout?: number
  retries?: number
  onError?: (error: AppError) => void
}