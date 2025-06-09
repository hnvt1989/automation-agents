import React, { useState } from 'react'
import { MeetingAnalysis, SuggestedTask } from '@/types'
import { createTaskFromSuggestion } from '@/services/api'

interface TaskSuggestionModalProps {
  isOpen: boolean
  onClose: () => void
  analysis: MeetingAnalysis
}

export const TaskSuggestionModal: React.FC<TaskSuggestionModalProps> = ({
  isOpen,
  onClose,
  analysis
}) => {
  const [selectedTasks, setSelectedTasks] = useState<Set<number>>(new Set())
  const [isCreating, setIsCreating] = useState(false)
  const [createResults, setCreateResults] = useState<{
    success: number
    failed: number
    errors: string[]
  } | null>(null)

  const handleTaskToggle = (index: number) => {
    const newSelected = new Set(selectedTasks)
    if (newSelected.has(index)) {
      newSelected.delete(index)
    } else {
      newSelected.add(index)
    }
    setSelectedTasks(newSelected)
  }

  const handleCreateTasks = async () => {
    if (selectedTasks.size === 0) return

    setIsCreating(true)
    setCreateResults(null)

    const results = {
      success: 0,
      failed: 0,
      errors: [] as string[]
    }

    const selectedTasksArray = Array.from(selectedTasks).map(index => analysis.suggested_tasks[index])

    for (const task of selectedTasksArray) {
      try {
        const response = await createTaskFromSuggestion(task)
        if (response.success) {
          results.success++
        } else {
          results.failed++
          results.errors.push(response.error || `Failed to create task: ${task.title}`)
        }
      } catch (error) {
        results.failed++
        results.errors.push(`Failed to create task "${task.title}": ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    }

    setCreateResults(results)
    setIsCreating(false)

    // Clear selection if all tasks were created successfully
    if (results.failed === 0) {
      setSelectedTasks(new Set())
    }
  }

  const getPriorityClass = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'priority-high'
      case 'medium':
        return 'priority-medium'
      case 'low':
        return 'priority-low'
      default:
        return 'priority-medium'
    }
  }

  const formatConfidence = (confidence: number) => {
    return `${Math.round(confidence * 100)}%`
  }

  const getResultMessage = () => {
    if (!createResults) return null

    const { success, failed, errors } = createResults
    const total = success + failed

    if (failed === 0) {
      return `${success} task${success === 1 ? '' : 's'} created successfully!`
    } else if (success === 0) {
      return `Failed to create ${failed} task${failed === 1 ? '' : 's'}`
    } else {
      return `${success} of ${total} tasks created successfully`
    }
  }

  if (!isOpen) {
    return null
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Task Suggestions</h2>
          <button
            className="close-button"
            onClick={onClose}
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="analysis-summary">
            <h3>Meeting Analysis Summary</h3>
            <p>{analysis.summary}</p>
            <div className="confidence-score">
              <strong>Confidence: {formatConfidence(analysis.confidence_score)}</strong>
            </div>
          </div>

          {analysis.key_decisions.length > 0 && (
            <div className="analysis-section">
              <h4>Key Decisions:</h4>
              <ul>
                {analysis.key_decisions.map((decision, index) => (
                  <li key={index}>{decision}</li>
                ))}
              </ul>
            </div>
          )}

          {analysis.action_items.length > 0 && (
            <div className="analysis-section">
              <h4>Action Items:</h4>
              <ul>
                {analysis.action_items.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {analysis.participants.length > 0 && (
            <div className="analysis-section">
              <h4>Participants:</h4>
              <p>{analysis.participants.join(', ')}</p>
            </div>
          )}

          <div className="suggested-tasks-section">
            <h3>Suggested Tasks</h3>
            <p className="task-count">
              {selectedTasks.size} task{selectedTasks.size === 1 ? '' : 's'} selected
            </p>

            {analysis.suggested_tasks.length === 0 ? (
              <p className="no-tasks">No tasks suggested from this meeting.</p>
            ) : (
              <div className="tasks-list">
                {analysis.suggested_tasks.map((task, index) => (
                  <div
                    key={index}
                    className={`task-suggestion ${selectedTasks.has(index) ? 'selected' : ''}`}
                  >
                    <div className="task-header">
                      <label className="task-checkbox">
                        <input
                          type="checkbox"
                          checked={selectedTasks.has(index)}
                          onChange={() => handleTaskToggle(index)}
                        />
                        <span className="task-title">{task.title}</span>
                      </label>
                      <div className="task-meta">
                        <span className={`priority-badge ${getPriorityClass(task.priority)}`}>
                          {task.priority}
                        </span>
                        <span className="confidence-badge">
                          Confidence: {formatConfidence(task.confidence)}
                        </span>
                      </div>
                    </div>

                    <div className="task-details">
                      <p className="task-description">{task.description}</p>
                      
                      <div className="task-info">
                        <div className="info-item">
                          <strong>Category:</strong> {task.category}
                        </div>
                        <div className="info-item">
                          <strong>Assignee:</strong> {task.assignee || 'Unassigned'}
                        </div>
                        <div className="info-item">
                          <strong>Due:</strong> {task.deadline || 'No deadline'}
                        </div>
                      </div>

                      <div className="task-context">
                        <strong>Context:</strong> {task.context}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {createResults && (
            <div className="create-results">
              <div className={`result-message ${createResults.failed === 0 ? 'success' : 'warning'}`}>
                {getResultMessage()}
              </div>
              {createResults.errors.length > 0 && (
                <div className="error-details">
                  <h4>Errors:</h4>
                  <ul>
                    {createResults.errors.map((error, index) => (
                      <li key={index} className="error-item">{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleCreateTasks}
            disabled={selectedTasks.size === 0 || isCreating}
          >
            {isCreating 
              ? 'Creating tasks...' 
              : `Create Selected Tasks (${selectedTasks.size})`
            }
          </button>
        </div>
      </div>
    </div>
  )
}

export default TaskSuggestionModal