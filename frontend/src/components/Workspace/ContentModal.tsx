import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { X } from 'lucide-react'
import { debounce } from 'lodash-es'
import { useAppStore } from '@/store'
import { useTasks, useLogs, useDocuments, useNotes, useMemos } from '@/hooks/useApi'
import { useSuccess, useError } from '@/hooks/useNotifications'
import LoggingModal from './LoggingModal'
import { TaskFields } from './ContentModal/TaskFields'
import { DocumentFields } from './ContentModal/DocumentFields'
import { LogFields } from './ContentModal/LogFields'
import type { Task, Document, Note, DailyLog, Memo, WorkspaceItem } from '@/types'

// Constants
const DESCRIPTION_WORD_LIMIT = 300
const DESCRIPTION_CHAR_LIMIT = 2000
const API_ENDPOINTS = {
  INDEX_CONTENT: '/api/index-content'
}
const MESSAGES = {
  INDEX_SUCCESS: 'Content indexed successfully!',
  INDEX_FAILURE: 'Failed to index content. Please try again.',
  SAVE_FAILURE: 'Failed to save item. Please try again.',
  LOG_SUCCESS: 'Log entry saved successfully!'
}

const ContentModal = () => {
  const { modal, closeModal } = useAppStore()
  const { createTask, updateTask } = useTasks()
  const { createLog, updateLog } = useLogs()
  const { createDocument, updateDocument } = useDocuments()
  const { createNote, updateNote } = useNotes()
  const { createMemo, updateMemo } = useMemos()
  
  // Notification hooks
  const showSuccess = useSuccess()
  const showError = useError()
  
  // Refs for focus management
  const modalRef = useRef<HTMLDivElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)
  
  interface FormDataType {
    name: string
    description: string
    type: WorkspaceItem['type']
    priority: Task['priority']
    status: Task['status']
    dueDate: string
    assignee: string
    tags: string[]
    todo: string
    content: string
    date: string
    actual_hours: string
    format: Document['format'] | Memo['format']
    category: string
    mood: DailyLog['mood']
    productivity: number
  }

  const [formData, setFormData] = useState<FormDataType>({
    name: '',
    description: '',
    type: 'task',
    priority: 'medium',
    status: 'todo',
    dueDate: '',
    assignee: '',
    tags: [],
    todo: '',
    content: '',
    date: '',
    actual_hours: '',
    format: 'text',
    category: '',
    mood: 'neutral',
    productivity: 5,
  })
  
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Logging modal state
  const [showLoggingModal, setShowLoggingModal] = useState(false)
  const [loggingData, setLoggingData] = useState({
    hours: '',
    description: '',
  })
  const [loggingErrors, setLoggingErrors] = useState<Record<string, string>>({})
  const [isLoggingSubmitting, setIsLoggingSubmitting] = useState(false)

  const getContentType = useCallback(() => {
    return modal.contentType || modal.item?.type || 'task'
  }, [modal.contentType, modal.item?.type])

  const resetFormData = () => {
    const contentType = getContentType()
    const baseData = {
      name: '',
      description: '',
      type: contentType,
      priority: 'medium' as Task['priority'],
      status: contentType === 'task' ? 'todo' : undefined,
      dueDate: '',
      assignee: '',
      tags: [],
      todo: '',
      content: '',
      date: contentType === 'log' ? new Date().toISOString().split('T')[0] : '',
      actual_hours: '',
      format: 'text' as Document['format'],
      category: '',
      mood: 'neutral' as DailyLog['mood'],
      productivity: 5,
    }
    setFormData(baseData)
  }

  const populateFormFromItem = (item: WorkspaceItem) => {
    const baseData = {
      name: item.name || '',
      description: item.description || '',
      type: item.type,
      lastModified: item.lastModified,
    }

    switch (item.type) {
      case 'task':
        const task = item as Task
        setFormData({
          ...baseData,
          priority: task.priority || 'medium',
          status: task.status || 'todo',
          dueDate: task.dueDate ? new Date(task.dueDate).toISOString().split('T')[0] : '',
          assignee: task.assignee || '',
          tags: task.tags || [],
          todo: task.todo || '',
        })
        break
      
      case 'document':
        const doc = item as Document
        setFormData({
          ...baseData,
          content: doc.content || '',
          format: doc.format || 'text',
          tags: doc.tags || [],
        })
        break
      
      case 'note':
        const note = item as Note
        setFormData({
          ...baseData,
          content: note.content || '',
          category: note.category || '',
          tags: note.tags || [],
        })
        break
      
      case 'log':
        const log = item as DailyLog
        setFormData({
          ...baseData,
          content: log.content || '',
          date: log.date ? new Date(log.date).toISOString().split('T')[0] : '',
          actual_hours: log.actual_hours?.toString() || '',
          mood: log.mood || 'neutral',
          productivity: log.productivity || 5,
          tags: log.tags || [],
        })
        break
      
      case 'memo':
        const memo = item as Memo
        setFormData({
          ...baseData,
          content: memo.content || '',
          format: memo.format || 'markdown',
          tags: memo.tags || [],
        })
        break
      
      default:
        resetFormData()
    }
  }

  // Update form data when modal opens
  useEffect(() => {
    if (modal.isOpen && modal.item && modal.mode === 'edit') {
      populateFormFromItem(modal.item)
    } else if (modal.isOpen && modal.mode === 'add') {
      resetFormData()
    }
    setErrors({})
    // Reset logging modal state when task modal changes
    setShowLoggingModal(false)
    setLoggingData({ hours: '', description: '' })
    setLoggingErrors({})
  }, [modal.isOpen, modal.item, modal.mode, modal.contentType])

  // Handle escape key to close modal
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && modal.isOpen && !showLoggingModal) {
        closeModal()
      } else if (e.key === 'Escape' && showLoggingModal) {
        handleLoggingCancel()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [modal.isOpen, closeModal, showLoggingModal])

  // Focus management
  useEffect(() => {
    if (modal.isOpen && firstInputRef.current) {
      // Store the element that had focus before opening
      const previouslyFocused = document.activeElement as HTMLElement
      
      // Focus the first input after a short delay
      setTimeout(() => {
        firstInputRef.current?.focus()
      }, 100)
      
      // Return focus when closing
      return () => {
        previouslyFocused?.focus()
      }
    }
  }, [modal.isOpen])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    const contentType = getContentType()
    
    if (!formData.name.trim()) {
      newErrors.name = `${contentType.charAt(0).toUpperCase() + contentType.slice(1)} name is required`
    }
    
    if (formData.description && formData.description.trim().split(/\s+/).length > DESCRIPTION_WORD_LIMIT) {
      newErrors.description = `Description cannot exceed ${DESCRIPTION_WORD_LIMIT} words`
    }

    // Type-specific validation
    if (contentType === 'log') {
      if (formData.actual_hours && (isNaN(parseFloat(formData.actual_hours)) || parseFloat(formData.actual_hours) < 0)) {
        newErrors.actual_hours = 'Hours must be a valid positive number'
      }
      if (!formData.date.trim()) {
        newErrors.date = 'Date is required for logs'
      }
    }

    if ((contentType === 'document' || contentType === 'note' || contentType === 'memo') && !formData.content.trim()) {
      newErrors.content = 'Content is required'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const getApiMethods = () => {
    const contentType = getContentType()
    switch (contentType) {
      case 'task':
        return { create: createTask, update: updateTask }
      case 'document':
        return { create: createDocument, update: updateDocument }
      case 'note':
        return { create: createNote, update: updateNote }
      case 'log':
        return { create: createLog, update: updateLog }
      case 'memo':
        return { create: createMemo, update: updateMemo }
      default:
        return { create: createTask, update: updateTask }
    }
  }

  const prepareSubmissionData = useCallback(() => {
    const contentType = getContentType()
    const baseData = {
      name: formData.name,
      description: formData.description,
      type: contentType,
      lastModified: new Date(),
    }

    switch (contentType) {
      case 'task':
        return {
          ...baseData,
          priority: formData.priority,
          status: formData.status,
          dueDate: formData.dueDate ? new Date(formData.dueDate) : undefined,
          assignee: formData.assignee,
          tags: formData.tags,
          todo: formData.todo,
        }
      
      case 'document':
        return {
          ...baseData,
          content: formData.content,
          format: formData.format,
          tags: formData.tags,
        }
      
      case 'note':
        return {
          ...baseData,
          content: formData.content,
          category: formData.category,
          tags: formData.tags,
        }
      
      case 'log':
        return {
          ...baseData,
          content: formData.content,
          date: new Date(formData.date),
          actual_hours: formData.actual_hours ? parseFloat(formData.actual_hours) : undefined,
          mood: formData.mood,
          productivity: formData.productivity,
          tags: formData.tags,
        }
      
      case 'memo':
        return {
          ...baseData,
          content: formData.content,
          format: formData.format,
          tags: formData.tags,
        }
      
      default:
        return baseData
    }
  }, [formData, getContentType])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    
    try {
      const submissionData = prepareSubmissionData()
      const { create, update } = getApiMethods()

      if (modal.mode === 'edit' && modal.item) {
        await update(modal.item.id, submissionData)
      } else {
        await create({
          ...submissionData,
          id: crypto.randomUUID(),
        })
      }
      
      closeModal()
    } catch (error) {
      console.error('Failed to save item:', error)
      setErrors({ submit: MESSAGES.SAVE_FAILURE })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleIndex = async () => {
    if (!modal.item) return
    
    setIsSubmitting(true)
    
    try {
      const response = await fetch(API_ENDPOINTS.INDEX_CONTENT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: modal.item.type,
          id: modal.item.id,
          name: modal.item.name,
          content: formData.content || modal.item.content || '',
          description: modal.item.description || '',
        })
      })

      if (response.ok) {
        showSuccess(MESSAGES.INDEX_SUCCESS)
      } else {
        throw new Error('Failed to index content')
      }
    } catch (error) {
      console.error('Failed to index content:', error)
      showError(MESSAGES.INDEX_FAILURE)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target
    setFormData((prev: any) => ({ ...prev, [name]: value }))
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleTagsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const tags = e.target.value.split(',').map(tag => tag.trim()).filter(Boolean)
    setFormData((prev: any) => ({ ...prev, tags }))
  }

  const getWordCount = (text: string) => {
    return text.trim().split(/\s+/).filter(Boolean).length
  }

  // Logging modal functions (only for tasks)
  const handleLogButtonClick = () => {
    setShowLoggingModal(true)
  }

  const handleLoggingInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setLoggingData(prev => ({ ...prev, [name]: value }))
    
    if (loggingErrors[name]) {
      setLoggingErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const validateLoggingForm = () => {
    const newErrors: Record<string, string> = {}
    
    if (!loggingData.hours.trim()) {
      newErrors.hours = 'Logging hours is required'
    } else {
      const hours = parseFloat(loggingData.hours)
      if (isNaN(hours) || hours <= 0) {
        newErrors.hours = 'Logging hours must be positive'
      }
    }
    
    setLoggingErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleLoggingSubmit = useCallback(async (data: { hours: string; description: string }) => {
    setIsLoggingSubmitting(true)
    
    try {
      const task = modal.item as Task
      const hours = parseFloat(data.hours)
      
      const logEntry = {
        id: crypto.randomUUID(),
        type: 'log' as const,
        name: `Task Log: ${task.name}`,
        description: data.description || `Logged work on task: ${task.name}`,
        date: new Date(),
        content: `Task: ${task.name}\nDescription: ${data.description || 'No additional description'}\nHours worked: ${hours}`,
        lastModified: new Date(),
        actual_hours: hours,
        log_id: task.id,
        tags: ['task-log', ...(task.tags || [])],
      }
      
      await createLog(logEntry)
      
      showSuccess(MESSAGES.LOG_SUCCESS)
      setShowLoggingModal(false)
      setLoggingData({ hours: '', description: '' })
      setLoggingErrors({})
    } catch (error) {
      console.error('Failed to save log entry:', error)
      setLoggingErrors({ submit: 'Failed to save log entry. Please try again.' })
    } finally {
      setIsLoggingSubmitting(false)
    }
  }, [modal.item, createLog, showSuccess])

  const handleLoggingCancel = () => {
    setShowLoggingModal(false)
    setLoggingData({ hours: '', description: '' })
    setLoggingErrors({})
  }

  const getModalTitle = () => {
    const contentType = getContentType()
    const typeName = contentType.charAt(0).toUpperCase() + contentType.slice(1)
    return modal.mode === 'edit' ? `Edit ${typeName}` : `Add ${typeName}`
  }

  const renderTypeSpecificFields = () => {
    const contentType = getContentType()

    switch (contentType) {
      case 'task':
        return (
          <TaskFields 
            formData={formData}
            errors={errors}
            onChange={handleInputChange}
          />
        )

      case 'document':
        return (
          <DocumentFields
            formData={formData}
            errors={errors}
            onChange={handleInputChange}
          />
        )

      case 'note':
        return (
          <>
            <div className="form-group">
              <label htmlFor="category" className="form-label">Category</label>
              <input
                type="text"
                id="category"
                name="category"
                value={formData.category}
                onChange={handleInputChange}
                className="form-input"
                placeholder="Enter note category"
              />
            </div>

            <div className="form-group">
              <label htmlFor="content" className="form-label">Content *</label>
              <textarea
                id="content"
                name="content"
                value={formData.content}
                onChange={handleInputChange}
                className={`form-textarea ${errors.content ? 'error' : ''}`}
                placeholder="Enter note content"
                rows={12}
                required
              />
              {errors.content && <div className="form-error">{errors.content}</div>}
            </div>
          </>
        )

      case 'log':
        return (
          <LogFields
            formData={formData}
            errors={errors}
            onChange={handleInputChange}
          />
        )

      case 'memo':
        return (
          <>
            <div className="form-group">
              <label htmlFor="format" className="form-label">Format</label>
              <select
                id="format"
                name="format"
                value={formData.format}
                onChange={handleInputChange}
                className="form-select"
              >
                <option value="text">Plain Text</option>
                <option value="markdown">Markdown</option>
                <option value="rich">Rich Text</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="content" className="form-label">Content *</label>
              <textarea
                id="content"
                name="content"
                value={formData.content}
                onChange={handleInputChange}
                className={`form-textarea ${errors.content ? 'error' : ''}`}
                placeholder="Enter memo content"
                rows={15}
                required
              />
              {errors.content && <div className="form-error">{errors.content}</div>}
            </div>
          </>
        )

      default:
        return null
    }
  }

  if (!modal.isOpen) return null

  const contentType = getContentType()

  return (
    <>
      <div className="modal-overlay" onClick={closeModal}>
        <div 
          ref={modalRef}
          className="modal-content" 
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          tabIndex={-1}
        >
          <div className="modal-header">
            <h2 id="modal-title" className="modal-title">{getModalTitle()}</h2>
            <button 
              className="modal-close" 
              onClick={closeModal}
              aria-label="Close modal"
            >
              <X size={20} />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="modal-body">
            {errors.submit && (
              <div className="form-error" style={{ marginBottom: '1rem' }}>
                {errors.submit}
              </div>
            )}

            <div className="form-group">
              <label htmlFor="name" className="form-label">
                {contentType === 'task' ? 'Task' : contentType.charAt(0).toUpperCase() + contentType.slice(1)} Name *
              </label>
              <input
                ref={firstInputRef}
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className={`form-input ${errors.name ? 'error' : ''}`}
                placeholder={`Enter ${contentType} name`}
                required
                aria-label={`${contentType} name`}
                aria-invalid={!!errors.name}
                aria-describedby={errors.name ? 'name-error' : undefined}
              />
              {errors.name && <div id="name-error" className="form-error" role="alert">{errors.name}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="description" className="form-label">
                Description
                <span className="word-count">
                  ({getWordCount(formData.description)}/{DESCRIPTION_WORD_LIMIT} words)
                </span>
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                className={`form-textarea ${errors.description ? 'error' : ''}`}
                placeholder={`Enter ${contentType} description (max ${DESCRIPTION_WORD_LIMIT} words)`}
                rows={4}
                maxLength={DESCRIPTION_CHAR_LIMIT}
              />
              {errors.description && <div className="form-error">{errors.description}</div>}
            </div>

            {renderTypeSpecificFields()}

            <div className="form-group">
              <label htmlFor="tags" className="form-label">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                id="tags"
                name="tags"
                value={Array.isArray(formData.tags) ? formData.tags.join(', ') : ''}
                onChange={handleTagsChange}
                className="form-input"
                placeholder="work, personal, urgent"
              />
            </div>

            <div className="modal-footer">
              <button
                type="button"
                onClick={closeModal}
                className="btn btn-secondary"
                disabled={isSubmitting}
              >
                Cancel
              </button>
              {modal.mode === 'edit' && contentType === 'task' && (
                <button
                  type="button"
                  onClick={handleLogButtonClick}
                  className="btn btn-outline"
                  disabled={isSubmitting}
                >
                  Log
                </button>
              )}
              {modal.mode === 'edit' && (contentType === 'document' || contentType === 'note') && (
                <button
                  type="button"
                  onClick={handleIndex}
                  className="btn btn-outline"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Indexing...' : 'Index'}
                </button>
              )}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : modal.mode === 'edit' ? `Update ${contentType.charAt(0).toUpperCase() + contentType.slice(1)}` : `Create ${contentType.charAt(0).toUpperCase() + contentType.slice(1)}`}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Logging Modal */}
      <LoggingModal
        isOpen={showLoggingModal && contentType === 'task'}
        onClose={handleLoggingCancel}
        onSave={handleLoggingSubmit}
        task={modal.item as Task}
        loggingData={loggingData}
        onInputChange={handleLoggingInputChange}
        errors={loggingErrors}
        isSubmitting={isLoggingSubmitting}
      />
    </>
  )
}

export default ContentModal