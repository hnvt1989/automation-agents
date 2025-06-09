import config, { getApiUrl } from '@/config'
import type { ApiResponse, WorkspaceItem, Task, Document, Note, DailyLog, AppConfig } from '@/types'

class ApiClient {
  private baseURL: string
  private timeout: number

  constructor() {
    this.baseURL = getApiUrl('')
    this.timeout = config.api.timeout
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        // Check if response is HTML (likely 404/error page)
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('text/html')) {
          throw new Error(`Backend API not available (${response.status}). Is the server running?`)
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      // Check if response is JSON
      const contentType = response.headers.get('content-type')
      if (!contentType || !contentType.includes('application/json')) {
        throw new Error('Expected JSON response but got ' + contentType)
      }

      const data = await response.json()
      return data
    } catch (error) {
      clearTimeout(timeoutId)
      throw error
    }
  }

  // Generic CRUD operations
  async getItems<T extends WorkspaceItem>(type: T['type']): Promise<ApiResponse<T[]>> {
    return this.request<T[]>(`/${type}s`)
  }

  async getItem<T extends WorkspaceItem>(type: T['type'], id: string): Promise<ApiResponse<T>> {
    return this.request<T>(`/${type}s/${id}`)
  }

  async createItem<T extends WorkspaceItem>(type: T['type'], item: Omit<T, 'id'>): Promise<ApiResponse<T>> {
    return this.request<T>(`/${type}s`, {
      method: 'POST',
      body: JSON.stringify(item),
    })
  }

  async updateItem<T extends WorkspaceItem>(type: T['type'], id: string, item: Partial<T>): Promise<ApiResponse<T>> {
    // For tasks, we need to find the index based on the ID
    if (type === 'task') {
      const tasksResponse = await this.getTasks()
      const tasks = tasksResponse.tasks || []
      const taskIndex = tasks.findIndex(t => t.id === id)
      
      if (taskIndex === -1) {
        throw new Error('Task not found')
      }
      
      return this.request<T>(`/${type}s/${taskIndex}`, {
        method: 'PUT',
        body: JSON.stringify(item),
      })
    }
    
    return this.request<T>(`/${type}s/${id}`, {
      method: 'PUT',
      body: JSON.stringify(item),
    })
  }

  async deleteItem(type: WorkspaceItem['type'], id: string): Promise<ApiResponse<void>> {
    // For tasks, we need to find the index based on the ID
    if (type === 'task') {
      const tasksResponse = await this.getTasks()
      const tasks = tasksResponse.tasks || []
      const taskIndex = tasks.findIndex(t => t.id === id)
      
      if (taskIndex === -1) {
        throw new Error('Task not found')
      }
      
      return this.request<void>(`/${type}s/${taskIndex}`, {
        method: 'DELETE',
      })
    }
    
    return this.request<void>(`/${type}s/${id}`, {
      method: 'DELETE',
    })
  }

  // Specific endpoints
  async getTasks(): Promise<ApiResponse<Task[]>> {
    const response = await this.request<{ tasks: Task[] }>('/tasks')
    return {
      ...response,
      data: response.data?.tasks || [],
      tasks: response.data?.tasks || []
    } as any
  }

  async getDocuments(): Promise<ApiResponse<Document[]>> {
    return this.getItems<Document>('document')
  }

  async getNotes(): Promise<ApiResponse<Note[]>> {
    return this.getItems<Note>('note')
  }

  async getLogs(): Promise<ApiResponse<DailyLog[]>> {
    return this.getItems<DailyLog>('log')
  }

  // Configuration
  async getConfig(): Promise<ApiResponse<AppConfig>> {
    return this.request<AppConfig>('/config')
  }

  async updateConfig(config: Partial<AppConfig>): Promise<ApiResponse<AppConfig>> {
    return this.request<AppConfig>('/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  // File operations
  async uploadFile(file: File): Promise<ApiResponse<{ url: string; path: string }>> {
    const formData = new FormData()
    formData.append('file', file)

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), this.timeout)

    try {
      const response = await fetch(`${this.baseURL}/upload`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      clearTimeout(timeoutId)
      throw error
    }
  }

  // Search
  async search(query: string, filters?: any): Promise<ApiResponse<WorkspaceItem[]>> {
    const params = new URLSearchParams({ q: query })
    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          params.append(key, String(value))
        }
      })
    }

    return this.request<WorkspaceItem[]>(`/search?${params}`)
  }
}

export const apiClient = new ApiClient()
export default apiClient