import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TaskModal from '@/components/Workspace/TaskModal'
import { useAppStore } from '@/store'
import { useTasks, useLogs } from '@/hooks/useApi'
import type { Task } from '@/types'

// Mock the hooks
vi.mock('@/store', () => ({
  useAppStore: vi.fn()
}))

vi.mock('@/hooks/useApi', () => ({
  useTasks: vi.fn(),
  useLogs: vi.fn()
}))

const mockCloseModal = vi.fn()
const mockCreateTask = vi.fn()
const mockUpdateTask = vi.fn()
const mockCreateDailyLog = vi.fn()

const mockTask: Task = {
  id: '1',
  name: 'Test Task',
  description: 'Test Description',
  type: 'task',
  status: 'todo',
  priority: 'medium',
  lastModified: new Date(),
  dueDate: new Date('2024-12-31'),
  assignee: 'John Doe',
  tags: ['test', 'work'],
  todo: 'Complete implementation'
}

describe('TaskModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAppStore as any).mockReturnValue({
      modal: {
        isOpen: true,
        mode: 'add',
        item: null
      },
      closeModal: mockCloseModal
    })
    ;(useTasks as any).mockReturnValue({
      createTask: mockCreateTask,
      updateTask: mockUpdateTask
    })
    
    ;(useLogs as any).mockReturnValue({
      createLog: mockCreateDailyLog
    })
  })

  describe('Basic Modal Functionality', () => {
    it('should render modal when open', () => {
      render(<TaskModal />)
      expect(screen.getByText('Add Task')).toBeInTheDocument()
      expect(screen.getByLabelText('Task Name *')).toBeInTheDocument()
    })

    it('should not render modal when closed', () => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: false,
          mode: 'add',
          item: null
        },
        closeModal: mockCloseModal
      })

      const { container } = render(<TaskModal />)
      expect(container.firstChild).toBeNull()
    })

    it('should close modal when close button is clicked', () => {
      render(<TaskModal />)
      const closeButton = screen.getByLabelText('Close modal')
      fireEvent.click(closeButton)
      expect(mockCloseModal).toHaveBeenCalled()
    })

    it('should close modal when overlay is clicked', () => {
      render(<TaskModal />)
      const overlay = document.querySelector('.modal-overlay')
      fireEvent.click(overlay!)
      expect(mockCloseModal).toHaveBeenCalled()
    })
  })

  describe('Form Validation', () => {
    it('should show error when task name is empty', async () => {
      render(<TaskModal />)
      const saveButton = screen.getByText('Create Task')
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Task name is required')).toBeInTheDocument()
      }, { timeout: 3000 })
      
      // Verify that createTask was not called due to validation failure
      expect(mockCreateTask).not.toHaveBeenCalled()
    })

    it('should validate description word count', async () => {
      render(<TaskModal />)
      const descriptionField = screen.getByLabelText(/Description/)
      
      // Create a description with more than 300 words
      const longDescription = 'word '.repeat(301)
      fireEvent.change(descriptionField, { target: { value: longDescription } })

      const saveButton = screen.getByText('Create Task')
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(screen.getByText('Description cannot exceed 300 words')).toBeInTheDocument()
      })
    })
  })

  describe('Edit Mode', () => {
    beforeEach(() => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: true,
          mode: 'edit',
          item: mockTask
        },
        closeModal: mockCloseModal
      })
    })

    it('should show "Edit Task" title in edit mode', () => {
      render(<TaskModal />)
      expect(screen.getByText('Edit Task')).toBeInTheDocument()
    })

    it('should populate form with existing task data', () => {
      render(<TaskModal />)
      
      expect(screen.getByDisplayValue('Test Task')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Test Description')).toBeInTheDocument()
      expect(screen.getByDisplayValue('medium')).toBeInTheDocument()
      expect(screen.getByDisplayValue('todo')).toBeInTheDocument()
      expect(screen.getByDisplayValue('John Doe')).toBeInTheDocument()
      expect(screen.getByDisplayValue('test, work')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Complete implementation')).toBeInTheDocument()
    })

    it('should show "Update Task" button in edit mode', () => {
      render(<TaskModal />)
      expect(screen.getByText('Update Task')).toBeInTheDocument()
    })
  })

  describe('Log Button Functionality', () => {

    it('should show Log button in edit mode', () => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: true,
          mode: 'edit',
          item: mockTask
        },
        closeModal: mockCloseModal
      })

      render(<TaskModal />)
      expect(screen.getByText('Log')).toBeInTheDocument()
    })

    it('should not show Log button in add mode', () => {
      render(<TaskModal />)
      expect(screen.queryByText('Log')).not.toBeInTheDocument()
    })

    it('should open logging modal when Log button is clicked', async () => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: true,
          mode: 'edit',
          item: mockTask
        },
        closeModal: mockCloseModal
      })

      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        expect(screen.getByText('Log Task Completion')).toBeInTheDocument()
        expect(screen.getByLabelText('Logging Hours *')).toBeInTheDocument()
      })
    })
  })

  describe('Logging Modal', () => {
    beforeEach(() => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: true,
          mode: 'edit',
          item: mockTask
        },
        closeModal: mockCloseModal
      })
    })

    it('should render logging modal with required fields', async () => {
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        expect(screen.getByText('Log Task Completion')).toBeInTheDocument()
        expect(screen.getByLabelText('Logging Hours *')).toBeInTheDocument()
        expect(screen.getByLabelText('Description')).toBeInTheDocument()
        expect(screen.getByText('Save Log')).toBeInTheDocument()
        expect(screen.getByText('Cancel')).toBeInTheDocument()
      })
    })

    it('should validate logging hours input', async () => {
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const saveButton = screen.getByText('Save Log')
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(screen.getByText('Logging hours is required')).toBeInTheDocument()
      })
    })

    it('should validate logging hours are positive', async () => {
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const hoursInput = screen.getByLabelText('Logging Hours *')
        fireEvent.change(hoursInput, { target: { value: '-1' } })
        
        const saveButton = screen.getByText('Save Log')
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(screen.getByText('Logging hours must be positive')).toBeInTheDocument()
      })
    })

    it('should save daily log with correct data', async () => {
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const hoursInput = screen.getByLabelText('Logging Hours *')
        const descriptionInput = screen.getByLabelText('Description')
        
        fireEvent.change(hoursInput, { target: { value: '2.5' } })
        fireEvent.change(descriptionInput, { target: { value: 'Completed task implementation' } })
        
        const saveButton = screen.getByText('Save Log')
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(mockCreateDailyLog).toHaveBeenCalledWith({
          id: expect.any(String),
          type: 'log',
          name: `Task Log: ${mockTask.name}`,
          description: 'Completed task implementation',
          date: expect.any(Date),
          content: expect.stringContaining('Task: Test Task'),
          lastModified: expect.any(Date),
          actual_hours: 2.5,
          log_id: mockTask.id,
          tags: ['task-log', ...mockTask.tags]
        })
      })
    })

    it('should close logging modal after successful save', async () => {
      mockCreateDailyLog.mockResolvedValue({ success: true })
      
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const hoursInput = screen.getByLabelText('Logging Hours *')
        fireEvent.change(hoursInput, { target: { value: '1' } })
        
        const saveButton = screen.getByText('Save Log')
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(screen.queryByText('Log Task Completion')).not.toBeInTheDocument()
      })
    })

    it('should show error message on save failure', async () => {
      mockCreateDailyLog.mockRejectedValue(new Error('Save failed'))
      
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const hoursInput = screen.getByLabelText('Logging Hours *')
        fireEvent.change(hoursInput, { target: { value: '1' } })
        
        const saveButton = screen.getByText('Save Log')
        fireEvent.click(saveButton)
      })

      await waitFor(() => {
        expect(screen.getByText('Failed to save log entry. Please try again.')).toBeInTheDocument()
      })
    })

    it('should close logging modal when Cancel is clicked', async () => {
      render(<TaskModal />)
      const logButton = screen.getByText('Log')
      fireEvent.click(logButton)

      await waitFor(() => {
        const cancelButton = screen.getByText('Cancel')
        fireEvent.click(cancelButton)
      })

      await waitFor(() => {
        expect(screen.queryByText('Log Task Completion')).not.toBeInTheDocument()
      })
    })
  })

  describe('Task Creation and Updates', () => {
    it('should create new task with correct data', async () => {
      render(<TaskModal />)
      
      const nameInput = screen.getByLabelText('Task Name *')
      const descriptionInput = screen.getByLabelText(/Description/)
      
      fireEvent.change(nameInput, { target: { value: 'New Task' } })
      fireEvent.change(descriptionInput, { target: { value: 'New Description' } })
      
      const saveButton = screen.getByText('Create Task')
      fireEvent.click(saveButton)

      await waitFor(() => {
        expect(mockCreateTask).toHaveBeenCalledWith({
          id: expect.any(String),
          type: 'task',
          name: 'New Task',
          description: 'New Description',
          priority: 'medium',
          status: 'todo',
          dueDate: undefined,
          assignee: '',
          tags: [],
          todo: '',
          lastModified: expect.any(Date)
        })
      })
    })

    it('should update existing task', async () => {
      ;(useAppStore as any).mockReturnValue({
        modal: {
          isOpen: true,
          mode: 'edit',
          item: mockTask
        },
        closeModal: mockCloseModal
      })

      render(<TaskModal />)
      
      const nameInput = screen.getByDisplayValue('Test Task')
      fireEvent.change(nameInput, { target: { value: 'Updated Task' } })
      
      const updateButton = screen.getByText('Update Task')
      fireEvent.click(updateButton)

      await waitFor(() => {
        expect(mockUpdateTask).toHaveBeenCalledWith(mockTask.id, expect.objectContaining({
          name: 'Updated Task'
        }))
      })
    })
  })
})