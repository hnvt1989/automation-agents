import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { isDevtoolsEnabled } from '@/config'
import type { 
  AppState, 
  ChatMessage, 
  Task, 
  Document, 
  Note, 
  DailyLog, 
  Meeting,
  AppConfig, 
  ModalState, 
  AppError,
  SearchFilters,
  SortOption,
  WorkspaceItem
} from '@/types'

interface AppStore extends AppState {
  // Chat actions
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void
  clearMessages: () => void
  setConnectionStatus: (isConnected: boolean) => void
  setTypingStatus: (isTyping: boolean) => void

  // Workspace actions
  setTasks: (tasks: Task[]) => void
  addTask: (task: Task) => void
  updateTask: (id: string, updates: Partial<Task>) => void
  deleteTask: (id: string) => void

  setDocuments: (documents: Document[]) => void
  addDocument: (document: Document) => void
  updateDocument: (id: string, updates: Partial<Document>) => void
  deleteDocument: (id: string) => void

  setNotes: (notes: Note[]) => void
  addNote: (note: Note) => void
  updateNote: (id: string, updates: Partial<Note>) => void
  deleteNote: (id: string) => void

  setLogs: (logs: DailyLog[]) => void
  addLog: (log: DailyLog) => void
  updateLog: (id: string, updates: Partial<DailyLog>) => void
  deleteLog: (id: string) => void

  setMeetings: (meetings: Meeting[]) => void
  addMeeting: (meeting: Meeting) => void
  updateMeeting: (id: string, updates: Partial<Meeting>) => void
  deleteMeeting: (id: string) => void

  // UI actions
  setActiveTab: (tab: string) => void
  setModal: (modal: ModalState) => void
  closeModal: () => void
  setLoading: (isLoading: boolean) => void
  addError: (error: AppError) => void
  removeError: (errorId: string) => void
  clearErrors: () => void

  // Configuration actions
  setConfig: (config: AppConfig) => void
  updateConfig: (updates: Partial<AppConfig>) => void

  // Search and filter actions
  setSearchFilters: (filters: SearchFilters) => void
  setSortOption: (sort: SortOption) => void
  
  // Bulk operations
  bulkDeleteItems: (type: WorkspaceItem['type'], ids: string[]) => void
  bulkUpdateItems: (type: WorkspaceItem['type'], updates: { id: string; data: Partial<WorkspaceItem> }[]) => void
}

const initialConfig: AppConfig = {
  paths: {
    localFileDir: '',
    knowledgeBaseDir: '',
  },
  preferences: {
    theme: 'auto',
    language: 'en',
    autoSave: true,
    notifications: true,
  },
  api: {
    baseUrl: '/api',
    timeout: 10000,
  },
}

const initialFilters: SearchFilters = {
  query: '',
  type: [],
  status: [],
  tags: [],
}

const initialSort: SortOption = {
  field: 'lastModified',
  direction: 'desc',
}

export const useAppStore = create<AppStore>()(
  isDevtoolsEnabled() 
    ? devtools(
        persist(
          (set) => ({
        // Initial state
        messages: [],
        isConnected: false,
        isTyping: false,
        tasks: [],
        documents: [],
        notes: [],
        logs: [],
        meetings: [],
        activeTab: 'tasks',
        modal: { isOpen: false, mode: 'add', contentType: 'task' },
        isLoading: false,
        errors: [],
        config: initialConfig,
        searchFilters: initialFilters,
        sortOption: initialSort,

        // Chat actions
        addMessage: (message) => {
          const newMessage: ChatMessage = {
            ...message,
            id: crypto.randomUUID(),
            timestamp: new Date(),
          }
          set((state) => ({
            messages: [...state.messages, newMessage],
          }))
        },

        updateMessage: (id, updates) => {
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === id ? { ...msg, ...updates } : msg
            ),
          }))
        },

        clearMessages: () => {
          set({ messages: [] })
        },

        setConnectionStatus: (isConnected) => {
          set({ isConnected })
        },

        setTypingStatus: (isTyping) => {
          set({ isTyping })
        },

        // Task actions
        setTasks: (tasks) => set({ tasks }),
        
        addTask: (task) => {
          set((state) => ({
            tasks: [...state.tasks, task],
          }))
        },

        updateTask: (id, updates) => {
          set((state) => ({
            tasks: state.tasks.map((task) =>
              task.id === id ? { ...task, ...updates, lastModified: new Date() } : task
            ),
          }))
        },

        deleteTask: (id) => {
          set((state) => ({
            tasks: state.tasks.filter((task) => task.id !== id),
          }))
        },

        // Document actions
        setDocuments: (documents) => set({ documents }),
        
        addDocument: (document) => {
          set((state) => ({
            documents: [...state.documents, document],
          }))
        },

        updateDocument: (id, updates) => {
          set((state) => ({
            documents: state.documents.map((doc) =>
              doc.id === id ? { ...doc, ...updates, lastModified: new Date() } : doc
            ),
          }))
        },

        deleteDocument: (id) => {
          set((state) => ({
            documents: state.documents.filter((doc) => doc.id !== id),
          }))
        },

        // Note actions
        setNotes: (notes) => set({ notes }),
        
        addNote: (note) => {
          set((state) => ({
            notes: [...state.notes, note],
          }))
        },

        updateNote: (id, updates) => {
          set((state) => ({
            notes: state.notes.map((note) =>
              note.id === id ? { ...note, ...updates, lastModified: new Date() } : note
            ),
          }))
        },

        deleteNote: (id) => {
          set((state) => ({
            notes: state.notes.filter((note) => note.id !== id),
          }))
        },

        // Log actions
        setLogs: (logs) => set({ logs }),
        
        addLog: (log) => {
          set((state) => ({
            logs: [...state.logs, log],
          }))
        },

        updateLog: (id, updates) => {
          set((state) => ({
            logs: state.logs.map((log) =>
              log.id === id ? { ...log, ...updates, lastModified: new Date() } : log
            ),
          }))
        },

        deleteLog: (id) => {
          set((state) => ({
            logs: state.logs.filter((log) => log.id !== id),
          }))
        },

        // Meeting actions
        setMeetings: (meetings) => set({ meetings }),
        
        addMeeting: (meeting) => {
          set((state) => ({
            meetings: [...state.meetings, meeting],
          }))
        },

        updateMeeting: (id, updates) => {
          set((state) => ({
            meetings: state.meetings.map((meeting) =>
              meeting.id === id ? { ...meeting, ...updates, lastModified: new Date() } : meeting
            ),
          }))
        },

        deleteMeeting: (id) => {
          set((state) => ({
            meetings: state.meetings.filter((meeting) => meeting.id !== id),
          }))
        },

        // UI actions
        setActiveTab: (activeTab) => set({ activeTab }),

        setModal: (modal) => set({ modal }),

        closeModal: () => set({ modal: { isOpen: false, mode: 'add', contentType: 'task' } }),

        setLoading: (isLoading) => set({ isLoading }),

        addError: (error) => {
          set((state) => ({
            errors: [...state.errors, error],
          }))
        },

        removeError: (errorId) => {
          set((state) => ({
            errors: state.errors.filter((error) => error.code !== errorId),
          }))
        },

        clearErrors: () => set({ errors: [] }),

        // Configuration actions
        setConfig: (config) => set({ config }),

        updateConfig: (updates) => {
          set((state) => ({
            config: { ...state.config, ...updates },
          }))
        },

        // Search and filter actions
        setSearchFilters: (searchFilters) => set({ searchFilters }),

        setSortOption: (sortOption) => set({ sortOption }),

        // Bulk operations
        bulkDeleteItems: (type, ids) => {
          set((state) => {
            switch (type) {
              case 'task':
                return { ...state, tasks: state.tasks.filter((item) => !ids.includes(item.id)) }
              case 'document':
                return { ...state, documents: state.documents.filter((item) => !ids.includes(item.id)) }
              case 'note':
                return { ...state, notes: state.notes.filter((item) => !ids.includes(item.id)) }
              case 'log':
                return { ...state, logs: state.logs.filter((item) => !ids.includes(item.id)) }
              case 'meeting':
                return { ...state, meetings: state.meetings.filter((item) => !ids.includes(item.id)) }
              default:
                return state
            }
          })
        },

        bulkUpdateItems: (type, updates) => {
          set((state) => {
            const updateMap = new Map(updates.map(({ id, data }) => [id, data]))
            
            switch (type) {
              case 'task':
                return {
                  ...state,
                  tasks: state.tasks.map((item) =>
                    updateMap.has(item.id) 
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'document':
                return {
                  ...state,
                  documents: state.documents.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'note':
                return {
                  ...state,
                  notes: state.notes.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'log':
                return {
                  ...state,
                  logs: state.logs.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'meeting':
                return {
                  ...state,
                  meetings: state.meetings.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              default:
                return state
            }
          })
        },
          }),
          {
            name: 'automation-agents-store',
            partialize: (state) => ({
              config: state.config,
              activeTab: state.activeTab,
              searchFilters: state.searchFilters,
              sortOption: state.sortOption,
            }),
          }
        ),
        { name: 'AutomationAgentsStore' }
      )
    : persist(
        (set) => ({
        // Initial state
        messages: [],
        isConnected: false,
        isTyping: false,
        tasks: [],
        documents: [],
        notes: [],
        logs: [],
        meetings: [],
        activeTab: 'tasks',
        modal: { isOpen: false, mode: 'add', contentType: 'task' },
        isLoading: false,
        errors: [],
        config: initialConfig,
        searchFilters: initialFilters,
        sortOption: initialSort,

        // Chat actions
        addMessage: (message) => {
          const newMessage: ChatMessage = {
            ...message,
            id: crypto.randomUUID(),
            timestamp: new Date(),
          }
          set((state) => ({
            messages: [...state.messages, newMessage],
          }))
        },

        updateMessage: (id, updates) => {
          set((state) => ({
            messages: state.messages.map((msg) =>
              msg.id === id ? { ...msg, ...updates } : msg
            ),
          }))
        },

        clearMessages: () => {
          set({ messages: [] })
        },

        setConnectionStatus: (isConnected) => {
          set({ isConnected })
        },

        setTypingStatus: (isTyping) => {
          set({ isTyping })
        },

        // Task actions
        setTasks: (tasks) => set({ tasks }),
        
        addTask: (task) => {
          set((state) => ({
            tasks: [...state.tasks, task],
          }))
        },

        updateTask: (id, updates) => {
          set((state) => ({
            tasks: state.tasks.map((task) =>
              task.id === id ? { ...task, ...updates, lastModified: new Date() } : task
            ),
          }))
        },

        deleteTask: (id) => {
          set((state) => ({
            tasks: state.tasks.filter((task) => task.id !== id),
          }))
        },

        // Document actions
        setDocuments: (documents) => set({ documents }),
        
        addDocument: (document) => {
          set((state) => ({
            documents: [...state.documents, document],
          }))
        },

        updateDocument: (id, updates) => {
          set((state) => ({
            documents: state.documents.map((doc) =>
              doc.id === id ? { ...doc, ...updates, lastModified: new Date() } : doc
            ),
          }))
        },

        deleteDocument: (id) => {
          set((state) => ({
            documents: state.documents.filter((doc) => doc.id !== id),
          }))
        },

        // Note actions
        setNotes: (notes) => set({ notes }),
        
        addNote: (note) => {
          set((state) => ({
            notes: [...state.notes, note],
          }))
        },

        updateNote: (id, updates) => {
          set((state) => ({
            notes: state.notes.map((note) =>
              note.id === id ? { ...note, ...updates, lastModified: new Date() } : note
            ),
          }))
        },

        deleteNote: (id) => {
          set((state) => ({
            notes: state.notes.filter((note) => note.id !== id),
          }))
        },

        // Log actions
        setLogs: (logs) => set({ logs }),
        
        addLog: (log) => {
          set((state) => ({
            logs: [...state.logs, log],
          }))
        },

        updateLog: (id, updates) => {
          set((state) => ({
            logs: state.logs.map((log) =>
              log.id === id ? { ...log, ...updates, lastModified: new Date() } : log
            ),
          }))
        },

        deleteLog: (id) => {
          set((state) => ({
            logs: state.logs.filter((log) => log.id !== id),
          }))
        },

        // Meeting actions
        setMeetings: (meetings) => set({ meetings }),
        
        addMeeting: (meeting) => {
          set((state) => ({
            meetings: [...state.meetings, meeting],
          }))
        },

        updateMeeting: (id, updates) => {
          set((state) => ({
            meetings: state.meetings.map((meeting) =>
              meeting.id === id ? { ...meeting, ...updates, lastModified: new Date() } : meeting
            ),
          }))
        },

        deleteMeeting: (id) => {
          set((state) => ({
            meetings: state.meetings.filter((meeting) => meeting.id !== id),
          }))
        },

        // UI actions
        setActiveTab: (activeTab) => set({ activeTab }),

        setModal: (modal) => set({ modal }),

        closeModal: () => set({ modal: { isOpen: false, mode: 'add', contentType: 'task' } }),

        setLoading: (isLoading) => set({ isLoading }),

        addError: (error) => {
          set((state) => ({
            errors: [...state.errors, error],
          }))
        },

        removeError: (errorId) => {
          set((state) => ({
            errors: state.errors.filter((error) => error.code !== errorId),
          }))
        },

        clearErrors: () => set({ errors: [] }),

        // Configuration actions
        setConfig: (config) => set({ config }),

        updateConfig: (updates) => {
          set((state) => ({
            config: { ...state.config, ...updates },
          }))
        },

        // Search and filter actions
        setSearchFilters: (searchFilters) => set({ searchFilters }),

        setSortOption: (sortOption) => set({ sortOption }),

        // Bulk operations
        bulkDeleteItems: (type, ids) => {
          set((state) => {
            switch (type) {
              case 'task':
                return { ...state, tasks: state.tasks.filter((item) => !ids.includes(item.id)) }
              case 'document':
                return { ...state, documents: state.documents.filter((item) => !ids.includes(item.id)) }
              case 'note':
                return { ...state, notes: state.notes.filter((item) => !ids.includes(item.id)) }
              case 'log':
                return { ...state, logs: state.logs.filter((item) => !ids.includes(item.id)) }
              case 'meeting':
                return { ...state, meetings: state.meetings.filter((item) => !ids.includes(item.id)) }
              default:
                return state
            }
          })
        },

        bulkUpdateItems: (type, updates) => {
          set((state) => {
            const updateMap = new Map(updates.map(({ id, data }) => [id, data]))
            
            switch (type) {
              case 'task':
                return {
                  ...state,
                  tasks: state.tasks.map((item) =>
                    updateMap.has(item.id) 
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'document':
                return {
                  ...state,
                  documents: state.documents.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'note':
                return {
                  ...state,
                  notes: state.notes.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'log':
                return {
                  ...state,
                  logs: state.logs.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              case 'meeting':
                return {
                  ...state,
                  meetings: state.meetings.map((item) =>
                    updateMap.has(item.id)
                      ? { ...item, ...updateMap.get(item.id), lastModified: new Date() }
                      : item
                  ),
                }
              default:
                return state
            }
          })
        },
        }),
        {
          name: 'automation-agents-store',
          partialize: (state) => ({
            config: state.config,
            activeTab: state.activeTab,
            searchFilters: state.searchFilters,
            sortOption: state.sortOption,
          }),
        }
      )
)

export default useAppStore