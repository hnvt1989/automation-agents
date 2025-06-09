import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TasksTab from '@/components/Workspace/tabs/TasksTab'
import { useAppStore } from '@/store'
import { useTasks } from '@/hooks/useApi'
import type { Task } from '@/types'

// Mock the hooks
vi.mock('@/store', () => ({
  useAppStore: vi.fn()
}))

vi.mock('@/hooks/useApi', () => ({
  useTasks: vi.fn()
}))

vi.mock('@/utils', () => ({
  getStatusColor: vi.fn((status) => status),
  formatRelativeTime: vi.fn((date) => 'a few minutes ago')
}))

const mockSetModal = vi.fn()
const mockUpdateTask = vi.fn()
const mockDeleteTask = vi.fn()
const mockFetchTasks = vi.fn()

const mockTasks: Task[] = [
  {
    id: '1',
    name: 'Personal Task 1',
    description: 'A personal task',
    type: 'task',
    status: 'todo',
    priority: 'high',
    lastModified: new Date(),
    tags: ['personal']
  },
  {
    id: '2',
    name: 'Work Task 1',
    description: 'A work task',
    type: 'task',
    status: 'in_progress',
    priority: 'medium',
    lastModified: new Date(),
    tags: ['work']
  },
  {
    id: '3',
    name: 'Personal Task 2',
    description: 'Another personal task',
    type: 'task',
    status: 'completed',
    priority: 'low',
    lastModified: new Date(),
    tags: ['personal']
  },
  {
    id: '4',
    name: 'Work Task 2',
    description: 'Another work task',
    type: 'task',
    status: 'todo',
    priority: 'high',
    lastModified: new Date(),
    tags: ['work']
  }
]

describe('TasksTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAppStore as any).mockReturnValue({
      setModal: mockSetModal
    })
    ;(useTasks as any).mockReturnValue({
      tasks: mockTasks,
      fetchTasks: mockFetchTasks,
      updateTask: mockUpdateTask,
      deleteTask: mockDeleteTask,
      loading: false
    })
  })

  describe('Task Type Filtering', () => {
    it('should show all tasks by default', () => {
      render(<TasksTab />)
      expect(screen.getByText('Personal Task 1')).toBeInTheDocument()
      expect(screen.getByText('Work Task 1')).toBeInTheDocument()
      expect(screen.getByText('Personal Task 2')).toBeInTheDocument()
      expect(screen.getByText('Work Task 2')).toBeInTheDocument()
    })

    it('should filter tasks by personal type', async () => {
      render(<TasksTab />)
      
      const typeFilter = screen.getByDisplayValue('All Types')
      fireEvent.change(typeFilter, { target: { value: 'personal' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Task 1')).toBeInTheDocument()
        expect(screen.getByText('Personal Task 2')).toBeInTheDocument()
        expect(screen.queryByText('Work Task 1')).not.toBeInTheDocument()
        expect(screen.queryByText('Work Task 2')).not.toBeInTheDocument()
      })
    })

    it('should filter tasks by work type', async () => {
      render(<TasksTab />)
      
      const typeFilter = screen.getByDisplayValue('All Types')
      fireEvent.change(typeFilter, { target: { value: 'work' } })
      
      await waitFor(() => {
        expect(screen.getByText('Work Task 1')).toBeInTheDocument()
        expect(screen.getByText('Work Task 2')).toBeInTheDocument()
        expect(screen.queryByText('Personal Task 1')).not.toBeInTheDocument()
        expect(screen.queryByText('Personal Task 2')).not.toBeInTheDocument()
      })
    })

    it('should reset to show all tasks when "All Types" is selected', async () => {
      render(<TasksTab />)
      
      const typeFilter = screen.getByDisplayValue('All Types')
      
      // First filter by personal
      fireEvent.change(typeFilter, { target: { value: 'personal' } })
      await waitFor(() => {
        expect(screen.queryByText('Work Task 1')).not.toBeInTheDocument()
      })
      
      // Then reset to all
      fireEvent.change(typeFilter, { target: { value: 'all' } })
      await waitFor(() => {
        expect(screen.getByText('Personal Task 1')).toBeInTheDocument()
        expect(screen.getByText('Work Task 1')).toBeInTheDocument()
        expect(screen.getByText('Personal Task 2')).toBeInTheDocument()
        expect(screen.getByText('Work Task 2')).toBeInTheDocument()
      })
    })
  })

  describe('Priority Sorting', () => {
    it('should sort tasks by priority (high to low)', async () => {
      render(<TasksTab />)
      
      const sortSelect = screen.getByDisplayValue('Last Modified')
      fireEvent.change(sortSelect, { target: { value: 'priority-desc' } })
      
      await waitFor(() => {
        const taskElements = screen.getAllByTestId('task-item')
        const taskNames = taskElements.map(el => el.querySelector('.item-title')?.textContent)
        
        // High priority tasks should come first
        const highPriorityTasks = taskNames.filter((_, index) => 
          mockTasks.find(task => task.name === taskNames[index])?.priority === 'high'
        )
        expect(highPriorityTasks.length).toBeGreaterThan(0)
      })
    })

    it('should sort tasks by priority (low to high)', async () => {
      render(<TasksTab />)
      
      const sortSelect = screen.getByDisplayValue('Last Modified')
      fireEvent.change(sortSelect, { target: { value: 'priority-asc' } })
      
      await waitFor(() => {
        const taskElements = screen.getAllByTestId('task-item')
        const taskNames = taskElements.map(el => el.querySelector('.item-title')?.textContent)
        
        // Low priority tasks should come first
        const lowPriorityTasks = taskNames.filter((_, index) => 
          mockTasks.find(task => task.name === taskNames[index])?.priority === 'low'
        )
        expect(lowPriorityTasks.length).toBeGreaterThan(0)
      })
    })

    it('should maintain sorting when applying other filters', async () => {
      render(<TasksTab />)
      
      // Set priority sorting to high-to-low
      const sortSelect = screen.getByDisplayValue('Last Modified')
      fireEvent.change(sortSelect, { target: { value: 'priority-desc' } })
      
      // Apply work type filter
      const typeFilter = screen.getByDisplayValue('All Types')
      fireEvent.change(typeFilter, { target: { value: 'work' } })
      
      await waitFor(() => {
        const taskElements = screen.getAllByTestId('task-item')
        expect(taskElements.length).toBe(2) // Only work tasks
        
        const taskNames = taskElements.map(el => el.querySelector('.item-title')?.textContent)
        const priorities = taskNames.map(name => 
          mockTasks.find(task => task.name === name)?.priority
        )
        
        // Should be sorted by priority (high first)
        expect(priorities[0]).toBe('high')
        expect(priorities[1]).toBe('medium')
      })
    })
  })

  describe('Completion State Filtering', () => {
    it('should show all tasks when "All" completion state is selected', () => {
      render(<TasksTab />)
      
      const completionFilter = screen.getByTestId('completion-state-filter')
      expect(completionFilter).toHaveValue('all')
      
      expect(screen.getByText('Personal Task 1')).toBeInTheDocument()
      expect(screen.getByText('Work Task 1')).toBeInTheDocument()
      expect(screen.getByText('Personal Task 2')).toBeInTheDocument()
      expect(screen.getByText('Work Task 2')).toBeInTheDocument()
    })

    it('should filter active tasks (todo and in_progress)', async () => {
      render(<TasksTab />)
      
      const completionFilter = screen.getByTestId('completion-state-filter')
      fireEvent.change(completionFilter, { target: { value: 'active' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Task 1')).toBeInTheDocument() // todo
        expect(screen.getByText('Work Task 1')).toBeInTheDocument() // in_progress
        expect(screen.getByText('Work Task 2')).toBeInTheDocument() // todo
        expect(screen.queryByText('Personal Task 2')).not.toBeInTheDocument() // completed
      })
    })

    it('should filter done tasks (completed and cancelled)', async () => {
      const tasksWithCancelled = [
        ...mockTasks,
        {
          id: '5',
          name: 'Cancelled Task',
          description: 'A cancelled task',
          type: 'task',
          status: 'cancelled',
          priority: 'low',
          lastModified: new Date(),
          tags: ['work']
        }
      ]
      ;(useTasks as any).mockReturnValue({
        tasks: tasksWithCancelled,
        fetchTasks: mockFetchTasks,
        updateTask: mockUpdateTask,
        deleteTask: mockDeleteTask,
        loading: false
      })

      render(<TasksTab />)
      
      const completionFilter = screen.getByTestId('completion-state-filter')
      fireEvent.change(completionFilter, { target: { value: 'done' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Task 2')).toBeInTheDocument() // completed
        expect(screen.getByText('Cancelled Task')).toBeInTheDocument() // cancelled
        expect(screen.queryByText('Personal Task 1')).not.toBeInTheDocument() // todo
        expect(screen.queryByText('Work Task 1')).not.toBeInTheDocument() // in_progress
        expect(screen.queryByText('Work Task 2')).not.toBeInTheDocument() // todo
      })
    })

    it('should work with both status filter and completion state filter', async () => {
      render(<TasksTab />)
      
      // Set completion state to active
      const completionFilter = screen.getByTestId('completion-state-filter')
      fireEvent.change(completionFilter, { target: { value: 'active' } })
      
      // Set status filter to todo
      const statusFilter = screen.getByDisplayValue('All Status')
      fireEvent.change(statusFilter, { target: { value: 'todo' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Task 1')).toBeInTheDocument() // todo
        expect(screen.getByText('Work Task 2')).toBeInTheDocument() // todo
        expect(screen.queryByText('Work Task 1')).not.toBeInTheDocument() // in_progress (filtered by status)
        expect(screen.queryByText('Personal Task 2')).not.toBeInTheDocument() // completed (filtered by completion state)
      })
    })
  })

  describe('Combined Filtering and Sorting', () => {
    it('should apply both type filter and priority sorting together', async () => {
      render(<TasksTab />)
      
      // Filter by personal type
      const typeFilter = screen.getByDisplayValue('All Types')
      fireEvent.change(typeFilter, { target: { value: 'personal' } })
      
      // Sort by priority (high to low)
      const sortSelect = screen.getByDisplayValue('Last Modified')
      fireEvent.change(sortSelect, { target: { value: 'priority-desc' } })
      
      await waitFor(() => {
        const taskElements = screen.getAllByTestId('task-item')
        expect(taskElements.length).toBe(2) // Only personal tasks
        
        const taskNames = taskElements.map(el => el.querySelector('.item-title')?.textContent)
        
        // Should contain only personal tasks
        expect(taskNames).toContain('Personal Task 1')
        expect(taskNames).toContain('Personal Task 2')
        expect(taskNames).not.toContain('Work Task 1')
        expect(taskNames).not.toContain('Work Task 2')
        
        // Should be sorted by priority (high priority first)
        const priorities = taskNames.map(name => 
          mockTasks.find(task => task.name === name)?.priority
        )
        expect(priorities[0]).toBe('high') // Personal Task 1
        expect(priorities[1]).toBe('low')  // Personal Task 2
      })
    })
  })
})