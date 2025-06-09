import React from 'react'
import type { DailyLog } from '@/types'

interface LogFieldsProps {
  formData: {
    date: string
    actual_hours: string
    mood: DailyLog['mood']
    productivity: number
    content: string
  }
  errors: Record<string, string>
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
}

export const LogFields: React.FC<LogFieldsProps> = ({ formData, errors, onChange }) => {
  return (
    <>
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="date" className="form-label">Date *</label>
          <input
            type="date"
            id="date"
            name="date"
            value={formData.date}
            onChange={onChange}
            className={`form-input ${errors.date ? 'error' : ''}`}
            required
            aria-label="Log date"
            aria-invalid={!!errors.date}
            aria-describedby={errors.date ? 'date-error' : undefined}
          />
          {errors.date && (
            <div id="date-error" className="form-error" role="alert">
              {errors.date}
            </div>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="actual_hours" className="form-label">Hours</label>
          <input
            type="number"
            id="actual_hours"
            name="actual_hours"
            value={formData.actual_hours}
            onChange={onChange}
            className={`form-input ${errors.actual_hours ? 'error' : ''}`}
            placeholder="Enter hours worked"
            step="0.1"
            min="0"
            aria-label="Hours worked"
            aria-invalid={!!errors.actual_hours}
            aria-describedby={errors.actual_hours ? 'hours-error' : undefined}
          />
          {errors.actual_hours && (
            <div id="hours-error" className="form-error" role="alert">
              {errors.actual_hours}
            </div>
          )}
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="mood" className="form-label">Mood</label>
          <select
            id="mood"
            name="mood"
            value={formData.mood}
            onChange={onChange}
            className="form-select"
            aria-label="Log mood"
          >
            <option value="positive">Positive</option>
            <option value="neutral">Neutral</option>
            <option value="negative">Negative</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="productivity" className="form-label">Productivity (1-10)</label>
          <input
            type="number"
            id="productivity"
            name="productivity"
            value={formData.productivity}
            onChange={onChange}
            className="form-input"
            min="1"
            max="10"
            aria-label="Productivity score"
          />
        </div>
      </div>

      <div className="form-group">
        <label htmlFor="content" className="form-label">Content *</label>
        <textarea
          id="content"
          name="content"
          value={formData.content}
          onChange={onChange}
          className={`form-textarea ${errors.content ? 'error' : ''}`}
          placeholder="Enter log content"
          rows={8}
          required
          aria-label="Log content"
          aria-invalid={!!errors.content}
          aria-describedby={errors.content ? 'log-content-error' : undefined}
        />
        {errors.content && (
          <div id="log-content-error" className="form-error" role="alert">
            {errors.content}
          </div>
        )}
      </div>
    </>
  )
}

export default LogFields