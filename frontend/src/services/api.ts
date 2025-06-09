import config, { getApiUrl } from '@/config'
import type { ApiResponse, WorkspaceItem, Task, Document, Note, DailyLog, AppConfig, Meeting, Memo, MeetingAnalysis, SuggestedTask } from '@/types'

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
    // For tasks, we can now use the ID directly since the backend supports it
    if (type === 'task') {
      console.log(`Updating task with ID ${id} directly (no index lookup needed)`)
      
      return this.request<T>(`/tasks/${id}`, {
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
    // For tasks, we can now use the ID directly since the backend supports it
    if (type === 'task') {
      console.log('=== DELETE TASK DEBUG (Frontend API) ===')
      console.log(`Timestamp: ${new Date().toISOString()}`)
      console.log('Deleting task with ID:', id)
      console.log('Type of ID being sent:', typeof id)
      console.log('ID value (JSON stringified):', JSON.stringify(id))
      console.log('ID length:', id.length)
      console.log('Stack trace:')
      console.trace()
      console.log(`Will send DELETE request to: /tasks/${id}`)
      
      try {
        const deleteResponse = await this.request<any>(`/tasks/${id}`, {
          method: 'DELETE',
        })
        
        console.log('Delete response from backend:', deleteResponse)
        
        return deleteResponse
      } catch (error) {
        console.error('Error during deletion:', error)
        throw error
      }
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

  async getMeetings(): Promise<ApiResponse<Meeting[]>> {
    return this.getItems<Meeting>('meeting')
  }

  async getMemos(): Promise<ApiResponse<Memo[]>> {
    return this.getItems<Memo>('memo')
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

  // Meeting Analysis
  async analyzeMeeting(meetingData: {
    meeting_content: string
    meeting_date: string
    meeting_title: string
  }): Promise<ApiResponse<{ analysis: MeetingAnalysis }>> {
    return this.request<{ analysis: MeetingAnalysis }>('/analyze-meeting', {
      method: 'POST',
      body: JSON.stringify(meetingData),
    })
  }

  // Task Creation from Analysis
  async createTaskFromSuggestion(suggestedTask: SuggestedTask): Promise<ApiResponse<{ task_id: string; enhanced_todo?: string }>> {
    return this.request<{ task_id: string; enhanced_todo?: string }>('/create-task-from-suggestion', {
      method: 'POST',
      body: JSON.stringify(suggestedTask),
    })
  }
}

export const apiClient = new ApiClient()

// Export specific methods for easier use in components
export const {
  getItems,
  getItem,
  createItem,
  updateItem,
  deleteItem,
  getTasks,
  getDocuments,
  getNotes,
  getLogs,
  getMeetings,
  getConfig,
  updateConfig,
  uploadFile,
  search,
  analyzeMeeting,
  createTaskFromSuggestion
} = apiClient

export default apiClient