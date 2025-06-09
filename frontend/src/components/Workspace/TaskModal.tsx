import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useAppStore } from '@/store'
import { useTasks, useLogs } from '@/hooks/useApi'
import type { Task } from '@/types'

const TaskModal = () => {
  const { modal, closeModal } = useAppStore()
  const { createTask, updateTask } = useTasks()
  const { createLog } = useLogs()
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    priority: 'medium' as Task['priority'],
    status: 'todo' as Task['status'],
    dueDate: '',
    assignee: '',
    tags: [] as string[],
    todo: '',
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

  // Update form data when modal opens with existing task
  useEffect(() => {
    if (modal.isOpen && modal.item && modal.mode === 'edit') {
      const task = modal.item as Task
      setFormData({
        name: task.name || '',
        description: task.description || '',
        priority: task.priority || 'medium',
        status: task.status || 'todo',
        dueDate: task.dueDate ? new Date(task.dueDate).toISOString().split('T')[0] : '',
        assignee: task.assignee || '',
        tags: task.tags || [],
        todo: task.todo || '',
      })
    } else if (modal.isOpen && modal.mode === 'add') {
      // Reset form for new task
      setFormData({
        name: '',
        description: '',
        priority: 'medium',
        status: 'todo',
        dueDate: '',
        assignee: '',
        tags: [],
        todo: '',
      })
    }
    setErrors({})
    // Reset logging modal state when task modal changes
    setShowLoggingModal(false)
    setLoggingData({ hours: '', description: '' })
    setLoggingErrors({})
  }, [modal.isOpen, modal.item, modal.mode])

  const validateForm = () => {
    const newErrors: Record<string, string> = {}
    
    if (!formData.name.trim()) {
      newErrors.name = 'Task name is required'
    }
    
    if (formData.description && formData.description.trim().split(/\s+/).length > 300) {
      newErrors.description = 'Description cannot exceed 300 words'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsSubmitting(true)
    
    try {
      const taskData = {
        ...formData,
        dueDate: formData.dueDate ? new Date(formData.dueDate) : undefined,
        lastModified: new Date(),
      }

      if (modal.mode === 'edit' && modal.item) {
        await updateTask(modal.item.id, taskData)
      } else {
        await createTask({
          ...taskData,
          id: crypto.randomUUID(),
          type: 'task' as const,
        })
      }
      
      closeModal()
    } catch (error) {
      console.error('Failed to save task:', error)
      setErrors({ submit: 'Failed to save task. Please try again.' })
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
    
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }))
    }
  }

  const handleTagsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const tags = e.target.value.split(',').map(tag => tag.trim()).filter(Boolean)
    setFormData(prev => ({ ...prev, tags }))
  }

  const getWordCount = (text: string) => {
    return text.trim().split(/\s+/).filter(Boolean).length
  }

  // Logging modal functions
  const handleLogButtonClick = () => {
    setShowLoggingModal(true)
  }

  const handleLoggingInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target
    setLoggingData(prev => ({ ...prev, [name]: value }))
    
    // Clear error when user starts typing
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

  const handleLoggingSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateLoggingForm()) {
      return
    }

    setIsLoggingSubmitting(true)
    
    try {
      const task = modal.item as Task
      const hours = parseFloat(loggingData.hours)
      
      const logEntry = {
        id: crypto.randomUUID(),
        type: 'log' as const,
        name: `Task Log: ${task.name}`,
        description: loggingData.description || `Logged work on task: ${task.name}`,
        date: new Date(),
        content: `Task: ${task.name}\nDescription: ${loggingData.description || 'No additional description'}\nHours worked: ${hours}`,
        lastModified: new Date(),
        actual_hours: hours,
        log_id: task.id,
        tags: ['task-log', ...(task.tags || [])],
      }
      
      await createLog(logEntry)
      
      // Close logging modal
      setShowLoggingModal(false)
      setLoggingData({ hours: '', description: '' })
      setLoggingErrors({})
    } catch (error) {
      console.error('Failed to save log entry:', error)
      setLoggingErrors({ submit: 'Failed to save log entry. Please try again.' })
    } finally {
      setIsLoggingSubmitting(false)
    }
  }

  const handleLoggingCancel = () => {
    setShowLoggingModal(false)
    setLoggingData({ hours: '', description: '' })
    setLoggingErrors({})
  }

  if (!modal.isOpen) return null

  return (
    <>
      <div className="modal-overlay" onClick={closeModal}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2 className="modal-title">
              {modal.mode === 'edit' ? 'Edit Task' : 'Add Task'}
            </h2>
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
                Task Name *
              </label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                className={`form-input ${errors.name ? 'error' : ''}`}
                placeholder="Enter task name"
                required
              />
              {errors.name && <div className="form-error">{errors.name}</div>}
            </div>

            <div className="form-group">
              <label htmlFor="description" className="form-label">
                Description
                <span className="word-count">
                  ({getWordCount(formData.description)}/300 words)
                </span>
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleInputChange}
                className={`form-textarea ${errors.description ? 'error' : ''}`}
                placeholder="Enter task description (max 300 words)"
                rows={8}
                maxLength={2000} // Rough character limit to prevent extremely long text
              />
              {errors.description && <div className="form-error">{errors.description}</div>}
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="priority" className="form-label">Priority</label>
                <select
                  id="priority"
                  name="priority"
                  value={formData.priority}
                  onChange={handleInputChange}
                  className="form-select"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="status" className="form-label">Status</label>
                <select
                  id="status"
                  name="status"
                  value={formData.status}
                  onChange={handleInputChange}
                  className="form-select"
                >
                  <option value="todo">To Do</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="dueDate" className="form-label">Due Date</label>
                <input
                  type="date"
                  id="dueDate"
                  name="dueDate"
                  value={formData.dueDate}
                  onChange={handleInputChange}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label htmlFor="assignee" className="form-label">Assignee</label>
                <input
                  type="text"
                  id="assignee"
                  name="assignee"
                  value={formData.assignee}
                  onChange={handleInputChange}
                  className="form-input"
                  placeholder="Enter assignee name"
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="tags" className="form-label">
                Tags (comma-separated)
              </label>
              <input
                type="text"
                id="tags"
                name="tags"
                value={formData.tags.join(', ')}
                onChange={handleTagsChange}
                className="form-input"
                placeholder="work, personal, urgent"
              />
            </div>

            <div className="form-group">
              <label htmlFor="todo" className="form-label">
                TODO Items
              </label>
              <textarea
                id="todo"
                name="todo"
                value={formData.todo}
                onChange={handleInputChange}
                className="form-textarea"
                placeholder="Enter TODO items, subtasks, or detailed action items"
                rows={6}
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
              {modal.mode === 'edit' && (
                <button
                  type="button"
                  onClick={handleLogButtonClick}
                  className="btn btn-outline"
                  disabled={isSubmitting}
                >
                  Log
                </button>
              )}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : modal.mode === 'edit' ? 'Update Task' : 'Create Task'}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Logging Modal */}
      {showLoggingModal && (
        <div className="modal-overlay" onClick={handleLoggingCancel}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Log Task Completion</h2>
              <button 
                className="modal-close" 
                onClick={handleLoggingCancel}
                aria-label="Close logging modal"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleLoggingSubmit} className="modal-body">
              {loggingErrors.submit && (
                <div className="form-error" style={{ marginBottom: '1rem' }}>
                  {loggingErrors.submit}
                </div>
              )}

              <div className="form-group">
                <label htmlFor="logging-hours" className="form-label">
                  Logging Hours *
                </label>
                <input
                  type="number"
                  id="logging-hours"
                  name="hours"
                  value={loggingData.hours}
                  onChange={handleLoggingInputChange}
                  className={`form-input ${loggingErrors.hours ? 'error' : ''}`}
                  placeholder="Enter hours worked"
                  step="0.1"
                  min="0"
                  required
                />
                {loggingErrors.hours && <div className="form-error">{loggingErrors.hours}</div>}
              </div>

              <div className="form-group">
                <label htmlFor="logging-description" className="form-label">
                  Description
                </label>
                <textarea
                  id="logging-description"
                  name="description"
                  value={loggingData.description}
                  onChange={handleLoggingInputChange}
                  className="form-textarea"
                  placeholder="Optional: Add details about the work completed"
                  rows={4}
                />
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  onClick={handleLoggingCancel}
                  className="btn btn-secondary"
                  disabled={isLoggingSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isLoggingSubmitting}
                >
                  {isLoggingSubmitting ? 'Saving...' : 'Save Log'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default TaskModal