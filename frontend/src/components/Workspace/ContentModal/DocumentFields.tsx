import React from 'react'
import type { Document } from '@/types'

interface DocumentFieldsProps {
  formData: {
    format: Document['format']
    content: string
  }
  errors: Record<string, string>
  onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void
}

export const DocumentFields: React.FC<DocumentFieldsProps> = ({ formData, errors, onChange }) => {
  return (
    <>
      <div className="form-group">
        <label htmlFor="format" className="form-label">Format</label>
        <select
          id="format"
          name="format"
          value={formData.format}
          onChange={onChange}
          className="form-select"
          aria-label="Document format"
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
          onChange={onChange}
          className={`form-textarea ${errors.content ? 'error' : ''}`}
          placeholder="Enter document content"
          rows={15}
          required
          aria-label="Document content"
          aria-invalid={!!errors.content}
          aria-describedby={errors.content ? 'content-error' : undefined}
        />
        {errors.content && (
          <div id="content-error" className="form-error" role="alert">
            {errors.content}
          </div>
        )}
      </div>
    </>
  )
}

export default DocumentFields