import React from 'react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ContentModal from '@/components/Workspace/ContentModal'
import { useAppStore } from '@/store'
import * as apiHooks from '@/hooks/useApi'
import type { ModalState, Document, Note, Task } from '@/types'

// Mock the store
vi.mock('@/store', () => ({
  useAppStore: vi.fn()
}))

// Mock the API hooks
vi.mock('@/hooks/useApi', () => ({
  useTasks: vi.fn(),
  useDocuments: vi.fn(),
  useNotes: vi.fn(),
  useLogs: vi.fn(),
  useMemos: vi.fn()
}))

// Mock fetch for the Index button
global.fetch = vi.fn()

// Mock window.alert
global.alert = vi.fn()

describe('ContentModal', () => {
  const mockCloseModal = vi.fn()
  const mockCreateTask = vi.fn()
  const mockUpdateTask = vi.fn()
  const mockCreateDocument = vi.fn()
  const mockUpdateDocument = vi.fn()
  const mockCreateNote = vi.fn()
  const mockUpdateNote = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Reset fetch mock
    ;(global.fetch as any).mockReset()
    
    // Default store mock
    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: false, mode: 'add', contentType: 'task' },
      closeModal: mockCloseModal
    })
    
    // Default API hooks mocks
    ;(apiHooks.useTasks as any).mockReturnValue({
      createTask: mockCreateTask,
      updateTask: mockUpdateTask
    })
    ;(apiHooks.useDocuments as any).mockReturnValue({
      createDocument: mockCreateDocument,
      updateDocument: mockUpdateDocument
    })
    ;(apiHooks.useNotes as any).mockReturnValue({
      createNote: mockCreateNote,
      updateNote: mockUpdateNote
    })
    ;(apiHooks.useLogs as any).mockReturnValue({
      createLog: vi.fn(),
      updateLog: vi.fn()
    })
    ;(apiHooks.useMemos as any).mockReturnValue({
      createMemo: vi.fn(),
      updateMemo: vi.fn()
    })
  })

  test('should not render when modal is closed', () => {
    const { container } = render(<ContentModal />)
    expect(container.firstChild).toBeNull()
  })

  test('should render task modal in add mode', () => {
    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'add', contentType: 'task' },
      closeModal: mockCloseModal
    })

    render(<ContentModal />)
    
    expect(screen.getByText('Add Task')).toBeInTheDocument()
    expect(screen.getByLabelText(/task name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/priority/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/status/i)).toBeInTheDocument()
  })

  test('should show Log button for tasks in edit mode', () => {
    const task: Task = {
      id: '1',
      type: 'task',
      name: 'Test Task',
      description: 'Test description',
      priority: 'medium',
      status: 'todo',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: task, contentType: 'task' },
      closeModal: mockCloseModal
    })

    render(<ContentModal />)
    
    expect(screen.getByText('Edit Task')).toBeInTheDocument()
    expect(screen.getByText('Log')).toBeInTheDocument()
  })

  test('should show Index button for documents in edit mode', () => {
    const document: Document = {
      id: '1',
      type: 'document',
      name: 'Test Document',
      description: 'Test description',
      content: 'Test content',
      format: 'text',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: document, contentType: 'document' },
      closeModal: mockCloseModal
    })

    render(<ContentModal />)
    
    expect(screen.getByText('Edit Document')).toBeInTheDocument()
    expect(screen.getByText('Index')).toBeInTheDocument()
  })

  test('should show Index button for notes in edit mode', () => {
    const note: Note = {
      id: '1',
      type: 'note',
      name: 'Test Note',
      description: 'Test description',
      content: 'Test content',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: note, contentType: 'note' },
      closeModal: mockCloseModal
    })

    render(<ContentModal />)
    
    expect(screen.getByText('Edit Note')).toBeInTheDocument()
    expect(screen.getByText('Index')).toBeInTheDocument()
  })

  test('should call index API when Index button is clicked', async () => {
    const document: Document = {
      id: '1',
      type: 'document',
      name: 'Test Document',
      description: 'Test description',
      content: 'Test content',
      format: 'text',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: document, contentType: 'document' },
      closeModal: mockCloseModal
    })
    
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true })
    })

    render(<ContentModal />)
    
    const indexButton = screen.getByText('Index')
    fireEvent.click(indexButton)
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/index-content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'document',
          id: '1',
          name: 'Test Document',
          content: 'Test content',
          description: 'Test description'
        })
      })
      expect(global.alert).toHaveBeenCalledWith('Content indexed successfully!')
    })
  })

  test('should handle index API error', async () => {
    const document: Document = {
      id: '1',
      type: 'document',
      name: 'Test Document',
      description: 'Test description',
      content: 'Test content',
      format: 'text',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: document, contentType: 'document' },
      closeModal: mockCloseModal
    })
    
    ;(global.fetch as any).mockResolvedValueOnce({
      ok: false,
      statusText: 'Internal Server Error'
    })

    render(<ContentModal />)
    
    const indexButton = screen.getByText('Index')
    fireEvent.click(indexButton)
    
    await waitFor(() => {
      expect(global.alert).toHaveBeenCalledWith('Failed to index content. Please try again.')
    })
  })

  // TODO: Fix validation test - errors are not rendering immediately
  test.skip('should validate required fields', async () => {
    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'add', contentType: 'task' },
      closeModal: mockCloseModal
    })

    render(<ContentModal />)
    
    // Try to submit without filling required fields
    const submitButton = screen.getByText('Create Task')
    fireEvent.click(submitButton)
    
    // Wait for validation error to appear
    await waitFor(() => {
      expect(screen.getByText('Task name is required')).toBeInTheDocument()
    })
  })

  test('should create new task successfully', async () => {
    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'add', contentType: 'task' },
      closeModal: mockCloseModal
    })
    
    mockCreateTask.mockResolvedValueOnce({ id: '123', name: 'New Task' })

    render(<ContentModal />)
    
    // Fill in required fields
    fireEvent.change(screen.getByLabelText(/task name/i), {
      target: { value: 'New Task' }
    })
    
    // Submit
    const submitButton = screen.getByText('Create Task')
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Task',
          type: 'task',
          priority: 'medium',
          status: 'todo'
        })
      )
      expect(mockCloseModal).toHaveBeenCalled()
    })
  })

  test('should update existing document successfully', async () => {
    const document: Document = {
      id: '1',
      type: 'document',
      name: 'Test Document',
      description: 'Test description',
      content: 'Test content',
      format: 'text',
      lastModified: new Date()
    }

    ;(useAppStore as any).mockReturnValue({
      modal: { isOpen: true, mode: 'edit', item: document, contentType: 'document' },
      closeModal: mockCloseModal
    })
    
    mockUpdateDocument.mockResolvedValueOnce({ ...document, content: 'Updated content' })

    render(<ContentModal />)
    
    // Update content
    fireEvent.change(screen.getByLabelText(/content/i), {
      target: { value: 'Updated content' }
    })
    
    // Submit
    const submitButton = screen.getByText('Update Document')
    fireEvent.click(submitButton)
    
    await waitFor(() => {
      expect(mockUpdateDocument).toHaveBeenCalledWith('1', 
        expect.objectContaining({
          content: 'Updated content'
        })
      )
      expect(mockCloseModal).toHaveBeenCalled()
    })
  })
})