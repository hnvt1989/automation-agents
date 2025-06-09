import React from 'react'
import type { Task } from '@/types'

interface TaskFieldsProps {
  formData: {
    priority: Task['priority']
    status: Task['status']
    dueDate: string
    assignee: string
    todo: string
  }
  errors: Record<string, string>
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
}

export const TaskFields: React.FC<TaskFieldsProps> = ({ formData, errors, onChange }) => {
  return (
    <>
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="priority" className="form-label">Priority</label>
          <select
            id="priority"
            name="priority"
            value={formData.priority}
            onChange={onChange}
            className="form-select"
            aria-label="Task priority"
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
            onChange={onChange}
            className="form-select"
            aria-label="Task status"
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
            onChange={onChange}
            className="form-input"
            aria-label="Task due date"
          />
        </div>

        <div className="form-group">
          <label htmlFor="assignee" className="form-label">Assignee</label>
          <input
            type="text"
            id="assignee"
            name="assignee"
            value={formData.assignee}
            onChange={onChange}
            className="form-input"
            placeholder="Enter assignee name"
            aria-label="Task assignee"
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="todo" className="form-label">TODO Items</label>
        <textarea
          id="todo"
          name="todo"
          value={formData.todo}
          onChange={onChange}
          className="form-textarea"
          placeholder="Enter TODO items, subtasks, or detailed action items"
          rows={6}
          aria-label="Task TODO items"
        />
      </div>
    </>
  )
}

export default TaskFields