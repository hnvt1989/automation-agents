import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useAppStore } from '@/store'
import { useTasks } from '@/hooks/useApi'
import type { Task } from '@/types'

const TaskModal = () => {
  const { modal, closeModal } = useAppStore()
  const { createTask, updateTask } = useTasks()
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    priority: 'medium' as Task['priority'],
    status: 'todo' as Task['status'],
    dueDate: '',
    assignee: '',
    tags: [] as string[],
  })
  
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

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
      })
    }
    setErrors({})
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

  if (!modal.isOpen) return null

  return (
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
              rows={4}
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

          <div className="modal-footer">
            <button
              type="button"
              onClick={closeModal}
              className="btn btn-secondary"
              disabled={isSubmitting}
            >
              Cancel
            </button>
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
  )
}

export default TaskModal