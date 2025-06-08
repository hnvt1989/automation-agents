import { useState, useCallback } from 'react'
import { apiClient } from '@/services/api'
import { useAppStore } from '@/store'
import type { ApiResponse, AppError } from '@/types'

interface UseApiState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

interface UseApiReturn<T> extends UseApiState<T> {
  execute: (...args: any[]) => Promise<T | null>
  reset: () => void
}

export function useApi<T>(
  apiCall: (...args: any[]) => Promise<ApiResponse<T>>,
  onSuccess?: (data: T) => void,
  onError?: (error: AppError) => void
): UseApiReturn<T> {
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: false,
    error: null,
  })

  const addError = useAppStore((state) => state.addError)

  const execute = useCallback(
    async (...args: any[]): Promise<T | null> => {
      setState((prev) => ({ ...prev, loading: true, error: null }))

      try {
        const response = await apiCall(...args)
        
        if (response.success && response.data) {
          setState({
            data: response.data,
            loading: false,
            error: null,
          })
          onSuccess?.(response.data)
          return response.data
        } else {
          const errorMessage = response.error || 'Unknown error occurred'
          setState({
            data: null,
            loading: false,
            error: errorMessage,
          })
          
          const appError: AppError = {
            code: 'API_ERROR',
            message: errorMessage,
            timestamp: new Date(),
          }
          
          addError(appError)
          onError?.(appError)
          return null
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Network error'
        setState({
          data: null,
          loading: false,
          error: errorMessage,
        })
        
        const appError: AppError = {
          code: 'NETWORK_ERROR',
          message: errorMessage,
          details: error,
          timestamp: new Date(),
        }
        
        addError(appError)
        onError?.(appError)
        return null
      }
    },
    [apiCall, onSuccess, onError, addError]
  )

  const reset = useCallback(() => {
    setState({
      data: null,
      loading: false,
      error: null,
    })
  }, [])

  return {
    ...state,
    execute,
    reset,
  }
}

// Specialized hooks for common operations
export function useTasks() {
  const { setTasks, addTask, updateTask, deleteTask } = useAppStore()

  const fetchTasks = useApi(
    () => apiClient.getTasks(),
    (tasks) => setTasks(tasks)
  )

  const createTask = useApi(
    (task: Omit<any, 'id'>) => apiClient.createItem('task', task),
    (task) => addTask(task)
  )

  const editTask = useApi(
    (id: string, updates: Partial<any>) => apiClient.updateItem('task', id, updates),
    (task) => updateTask(task.id, task)
  )

  const removeTask = useApi(
    (id: string) => apiClient.deleteItem('task', id),
    () => {},
    () => {}
  )

  const deleteTaskAction = useCallback(
    async (id: string) => {
      const result = await removeTask.execute(id)
      if (result !== null) {
        deleteTask(id)
      }
      return result
    },
    [removeTask, deleteTask]
  )

  return {
    tasks: useAppStore((state) => state.tasks),
    fetchTasks: fetchTasks.execute,
    createTask: createTask.execute,
    updateTask: editTask.execute,
    deleteTask: deleteTaskAction,
    loading: fetchTasks.loading || createTask.loading || editTask.loading || removeTask.loading,
    error: fetchTasks.error || createTask.error || editTask.error || removeTask.error,
  }
}

export function useDocuments() {
  const { setDocuments, addDocument, updateDocument, deleteDocument } = useAppStore()

  const fetchDocuments = useApi(
    () => apiClient.getDocuments(),
    (documents) => setDocuments(documents)
  )

  const createDocument = useApi(
    (document: Omit<any, 'id'>) => apiClient.createItem('document', document),
    (document) => addDocument(document)
  )

  const editDocument = useApi(
    (id: string, updates: Partial<any>) => apiClient.updateItem('document', id, updates),
    (document) => updateDocument(document.id, document)
  )

  const removeDocument = useApi(
    (id: string) => apiClient.deleteItem('document', id),
    () => {},
    () => {}
  )

  const deleteDocumentAction = useCallback(
    async (id: string) => {
      const result = await removeDocument.execute(id)
      if (result !== null) {
        deleteDocument(id)
      }
      return result
    },
    [removeDocument, deleteDocument]
  )

  return {
    documents: useAppStore((state) => state.documents),
    fetchDocuments: fetchDocuments.execute,
    createDocument: createDocument.execute,
    updateDocument: editDocument.execute,
    deleteDocument: deleteDocumentAction,
    loading: fetchDocuments.loading || createDocument.loading || editDocument.loading || removeDocument.loading,
    error: fetchDocuments.error || createDocument.error || editDocument.error || removeDocument.error,
  }
}

export function useNotes() {
  const { setNotes, addNote, updateNote, deleteNote } = useAppStore()

  const fetchNotes = useApi(
    () => apiClient.getNotes(),
    (notes) => setNotes(notes)
  )

  const createNote = useApi(
    (note: Omit<any, 'id'>) => apiClient.createItem('note', note),
    (note) => addNote(note)
  )

  const editNote = useApi(
    (id: string, updates: Partial<any>) => apiClient.updateItem('note', id, updates),
    (note) => updateNote(note.id, note)
  )

  const removeNote = useApi(
    (id: string) => apiClient.deleteItem('note', id),
    () => {},
    () => {}
  )

  const deleteNoteAction = useCallback(
    async (id: string) => {
      const result = await removeNote.execute(id)
      if (result !== null) {
        deleteNote(id)
      }
      return result
    },
    [removeNote, deleteNote]
  )

  return {
    notes: useAppStore((state) => state.notes),
    fetchNotes: fetchNotes.execute,
    createNote: createNote.execute,
    updateNote: editNote.execute,
    deleteNote: deleteNoteAction,
    loading: fetchNotes.loading || createNote.loading || editNote.loading || removeNote.loading,
    error: fetchNotes.error || createNote.error || editNote.error || removeNote.error,
  }
}

export function useLogs() {
  const { setLogs, addLog, updateLog, deleteLog } = useAppStore()

  const fetchLogs = useApi(
    () => apiClient.getLogs(),
    (logs) => setLogs(logs)
  )

  const createLog = useApi(
    (log: Omit<any, 'id'>) => apiClient.createItem('log', log),
    (log) => addLog(log)
  )

  const editLog = useApi(
    (id: string, updates: Partial<any>) => apiClient.updateItem('log', id, updates),
    (log) => updateLog(log.id, log)
  )

  const removeLog = useApi(
    (id: string) => apiClient.deleteItem('log', id),
    () => {},
    () => {}
  )

  const deleteLogAction = useCallback(
    async (id: string) => {
      const result = await removeLog.execute(id)
      if (result !== null) {
        deleteLog(id)
      }
      return result
    },
    [removeLog, deleteLog]
  )

  return {
    logs: useAppStore((state) => state.logs),
    fetchLogs: fetchLogs.execute,
    createLog: createLog.execute,
    updateLog: editLog.execute,
    deleteLog: deleteLogAction,
    loading: fetchLogs.loading || createLog.loading || editLog.loading || removeLog.loading,
    error: fetchLogs.error || createLog.error || editLog.error || removeLog.error,
  }
}

export function useConfig() {
  const { setConfig } = useAppStore()

  const fetchConfig = useApi(
    () => apiClient.getConfig(),
    (config) => setConfig(config),
    (error) => {
      // Don't treat config loading errors as critical
      console.warn('Could not load config from backend:', error.message)
    }
  )

  const saveConfig = useApi(
    (updates: Partial<any>) => apiClient.updateConfig(updates),
    (config) => setConfig(config)
  )

  return {
    config: useAppStore((state) => state.config),
    fetchConfig: fetchConfig.execute,
    updateConfig: saveConfig.execute,
    loading: fetchConfig.loading || saveConfig.loading,
    error: fetchConfig.error || saveConfig.error,
  }
}