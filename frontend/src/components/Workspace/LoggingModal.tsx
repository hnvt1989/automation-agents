import React from 'react'
import { X } from 'lucide-react'
import type { Task } from '@/types'

interface LoggingModalProps {
  isOpen: boolean
  onClose: () => void
  onSave: (data: { hours: string; description: string }) => Promise<void>
  task: Task | null
  loggingData: {
    hours: string
    description: string
  }
  onInputChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => void
  errors: Record<string, string>
  isSubmitting: boolean
}

export const LoggingModal: React.FC<LoggingModalProps> = ({
  isOpen,
  onClose,
  onSave,
  task,
  loggingData,
  onInputChange,
  errors,
  isSubmitting
}) => {
  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSave(loggingData)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Log Task Completion</h2>
          <button 
            className="modal-close" 
            onClick={onClose}
            aria-label="Close logging modal"
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
            <label htmlFor="logging-hours" className="form-label">
              Logging Hours *
            </label>
            <input
              type="number"
              id="logging-hours"
              name="hours"
              value={loggingData.hours}
              onChange={onInputChange}
              className={`form-input ${errors.hours ? 'error' : ''}`}
              placeholder="Enter hours worked"
              step="0.1"
              min="0"
              required
              aria-label="Hours worked"
              aria-invalid={!!errors.hours}
              aria-describedby={errors.hours ? 'hours-error' : undefined}
            />
            {errors.hours && (
              <div id="hours-error" className="form-error" role="alert">
                {errors.hours}
              </div>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="logging-description" className="form-label">
              Description
            </label>
            <textarea
              id="logging-description"
              name="description"
              value={loggingData.description}
              onChange={onInputChange}
              className="form-textarea"
              placeholder="Optional: Add details about the work completed"
              rows={4}
              aria-label="Work description"
            />
          </div>

          <div className="modal-footer">
            <button
              type="button"
              onClick={onClose}
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
              {isSubmitting ? 'Saving...' : 'Save Log'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default LoggingModal