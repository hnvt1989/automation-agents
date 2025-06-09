import React from 'react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import LoggingModal from '@/components/Workspace/LoggingModal'
import type { Task } from '@/types'

describe('LoggingModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSave = vi.fn()
  const mockOnInputChange = vi.fn()

  const mockTask: Task = {
    id: '1',
    type: 'task',
    name: 'Test Task',
    description: 'Test Description',
    priority: 'medium',
    status: 'todo',
    lastModified: new Date()
  }

  const defaultProps = {
    isOpen: true,
    onClose: mockOnClose,
    onSave: mockOnSave,
    task: mockTask,
    loggingData: { hours: '', description: '' },
    onInputChange: mockOnInputChange,
    errors: {},
    isSubmitting: false
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  test('should not render when isOpen is false', () => {
    const { container } = render(
      <LoggingModal {...defaultProps} isOpen={false} />
    )
    
    expect(container.firstChild).toBeNull()
  })

  test('should render when isOpen is true', () => {
    render(<LoggingModal {...defaultProps} />)
    
    expect(screen.getByText('Log Task Completion')).toBeInTheDocument()
    expect(screen.getByLabelText('Hours worked')).toBeInTheDocument()
    expect(screen.getByLabelText('Work description')).toBeInTheDocument()
  })

  test('should call onClose when clicking overlay', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const overlay = screen.getByRole('dialog').parentElement
    fireEvent.click(overlay!)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  test('should not close when clicking modal content', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const modal = screen.getByRole('dialog')
    fireEvent.click(modal)
    
    expect(mockOnClose).not.toHaveBeenCalled()
  })

  test('should call onClose when close button is clicked', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const closeButton = screen.getByLabelText('Close logging modal')
    fireEvent.click(closeButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  test('should call onClose when cancel button is clicked', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  test('should display form values correctly', () => {
    render(
      <LoggingModal
        {...defaultProps}
        loggingData={{ hours: '2.5', description: 'Completed task work' }}
      />
    )
    
    const hoursInput = screen.getByLabelText('Hours worked') as HTMLInputElement
    const descriptionInput = screen.getByLabelText('Work description') as HTMLTextAreaElement
    
    expect(hoursInput.value).toBe('2.5')
    expect(descriptionInput.value).toBe('Completed task work')
  })

  test('should call onInputChange when input values change', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const hoursInput = screen.getByLabelText('Hours worked')
    fireEvent.change(hoursInput, { target: { name: 'hours', value: '3' } })
    
    expect(mockOnInputChange).toHaveBeenCalledWith(
      expect.objectContaining({
        target: expect.objectContaining({
          name: 'hours',
          value: '3'
        })
      })
    )
  })

  test('should display validation errors', () => {
    render(
      <LoggingModal
        {...defaultProps}
        errors={{
          hours: 'Hours is required',
          submit: 'Failed to save'
        }}
      />
    )
    
    expect(screen.getByText('Hours is required')).toBeInTheDocument()
    expect(screen.getByText('Failed to save')).toBeInTheDocument()
  })

  test('should show loading state when submitting', () => {
    render(
      <LoggingModal {...defaultProps} isSubmitting={true} />
    )
    
    const submitButton = screen.getByText('Saving...')
    const cancelButton = screen.getByText('Cancel')
    
    expect(submitButton).toBeDisabled()
    expect(cancelButton).toBeDisabled()
  })

  test('should call onSave when form is submitted', async () => {
    mockOnSave.mockResolvedValueOnce(undefined)
    
    render(
      <LoggingModal
        {...defaultProps}
        loggingData={{ hours: '2', description: 'Work done' }}
      />
    )
    
    const form = screen.getByRole('dialog').querySelector('form')!
    fireEvent.submit(form)
    
    await waitFor(() => {
      expect(mockOnSave).toHaveBeenCalledWith({
        hours: '2',
        description: 'Work done'
      })
    })
  })

  test('should have proper accessibility attributes', () => {
    render(<LoggingModal {...defaultProps} />)
    
    const modal = screen.getByRole('dialog')
    expect(modal).toHaveAttribute('aria-modal', 'true')
    expect(modal).toHaveAttribute('aria-labelledby', 'modal-title')
    
    const hoursInput = screen.getByLabelText('Hours worked')
    expect(hoursInput).toHaveAttribute('aria-label', 'Hours worked')
    expect(hoursInput).toHaveAttribute('required')
    
    // Test error state accessibility
    const { rerender } = render(
      <LoggingModal {...defaultProps} errors={{ hours: 'Required' }} />
    )
    
    const hoursInputWithError = screen.getByLabelText('Hours worked')
    expect(hoursInputWithError).toHaveAttribute('aria-invalid', 'true')
    expect(hoursInputWithError).toHaveAttribute('aria-describedby', 'hours-error')
  })
})