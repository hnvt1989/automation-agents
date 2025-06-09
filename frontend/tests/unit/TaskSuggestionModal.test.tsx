/**
 * Tests for TaskSuggestionModal component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TaskSuggestionModal } from '../../src/components/Workspace/TaskSuggestionModal'
import * as api from '../../src/services/api'

// Mock the API
vi.mock('../../src/services/api', () => ({
  createTaskFromSuggestion: vi.fn()
}))

const mockSuggestedTasks = [
  {
    title: 'Update documentation',
    description: 'Update the project README with latest changes',
    priority: 'high',
    deadline: '2025-06-15',
    assignee: 'John',
    category: 'documentation',
    confidence: 0.9,
    context: 'Discussed during team meeting'
  },
  {
    title: 'Review code changes',
    description: 'Review the recent pull requests',
    priority: 'medium',
    deadline: null,
    assignee: 'Alice',
    category: 'review',
    confidence: 0.8,
    context: 'Action item from standup'
  },
  {
    title: 'Schedule follow-up meeting',
    description: 'Schedule a meeting to discuss next steps',
    priority: 'low',
    deadline: '2025-06-10',
    assignee: null,
    category: 'communication',
    confidence: 0.7,
    context: 'Mentioned as next step'
  }
]

const mockAnalysis = {
  meeting_date: '2025-06-08',
  meeting_title: 'Team Standup',
  summary: 'Team discussed project progress and next steps',
  suggested_tasks: mockSuggestedTasks,
  key_decisions: ['Extend deadline by one week'],
  action_items: ['Review code', 'Update docs'],
  next_steps: ['Schedule follow-up'],
  participants: ['Alice', 'Bob', 'John'],
  confidence_score: 0.85
}

describe('TaskSuggestionModal', () => {
  const mockProps = {
    isOpen: true,
    onClose: vi.fn(),
    analysis: mockAnalysis
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal with analysis summary', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    expect(screen.getByText('Task Suggestions')).toBeInTheDocument()
    expect(screen.getByText('Team discussed project progress and next steps')).toBeInTheDocument()
    expect(screen.getByText('Confidence: 85%')).toBeInTheDocument()
  })

  it('displays all suggested tasks', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    expect(screen.getByText('Update documentation')).toBeInTheDocument()
    expect(screen.getByText('Review code changes')).toBeInTheDocument()
    expect(screen.getByText('Schedule follow-up meeting')).toBeInTheDocument()
  })

  it('shows task details correctly', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    // Check first task details
    expect(screen.getByText('Update the project README with latest changes')).toBeInTheDocument()
    expect(screen.getByText('Assignee: John')).toBeInTheDocument()
    expect(screen.getByText('Due: 2025-06-15')).toBeInTheDocument()
    expect(screen.getByText('Confidence: 90%')).toBeInTheDocument()
  })

  it('handles tasks with no assignee or deadline', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    expect(screen.getByText('Assignee: Unassigned')).toBeInTheDocument()
    expect(screen.getByText('Due: No deadline')).toBeInTheDocument()
  })

  it('allows selecting and deselecting tasks', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkboxes = screen.getAllByRole('checkbox')
    
    // Initially all should be unchecked
    checkboxes.forEach(checkbox => {
      expect(checkbox).not.toBeChecked()
    })
    
    // Click first checkbox
    fireEvent.click(checkboxes[0])
    expect(checkboxes[0]).toBeChecked()
    
    // Click again to deselect
    fireEvent.click(checkboxes[0])
    expect(checkboxes[0]).not.toBeChecked()
  })

  it('shows correct count of selected tasks', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkboxes = screen.getAllByRole('checkbox')
    
    // Initially 0 selected
    expect(screen.getByText('0 tasks selected')).toBeInTheDocument()
    
    // Select 2 tasks
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])
    
    expect(screen.getByText('2 tasks selected')).toBeInTheDocument()
  })

  it('disables create button when no tasks selected', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const createButton = screen.getByText('Create Selected Tasks')
    expect(createButton).toBeDisabled()
  })

  it('enables create button when tasks are selected', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)
    
    const createButton = screen.getByText('Create Selected Tasks')
    expect(createButton).not.toBeDisabled()
  })

  it('calls API to create tasks when create button is clicked', async () => {
    const mockCreateTask = vi.mocked(api.createTaskFromSuggestion)
    mockCreateTask.mockResolvedValue({ success: true, task_id: 'task-123' })

    render(<TaskSuggestionModal {...mockProps} />)
    
    // Select first task
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)
    
    // Click create button
    const createButton = screen.getByText('Create Selected Tasks')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith(mockSuggestedTasks[0])
    })
  })

  it('shows loading state while creating tasks', async () => {
    const mockCreateTask = vi.mocked(api.createTaskFromSuggestion)
    mockCreateTask.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)
    
    const createButton = screen.getByText('Create Selected Tasks')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('Creating tasks...')).toBeInTheDocument()
    })
  })

  it('handles task creation errors gracefully', async () => {
    const mockCreateTask = vi.mocked(api.createTaskFromSuggestion)
    mockCreateTask.mockRejectedValue(new Error('Network error'))

    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)
    
    const createButton = screen.getByText('Create Selected Tasks')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText(/Failed to create task/)).toBeInTheDocument()
    })
  })

  it('shows success message after tasks are created', async () => {
    const mockCreateTask = vi.mocked(api.createTaskFromSuggestion)
    mockCreateTask.mockResolvedValue({ success: true, task_id: 'task-123' })

    render(<TaskSuggestionModal {...mockProps} />)
    
    const checkbox = screen.getAllByRole('checkbox')[0]
    fireEvent.click(checkbox)
    
    const createButton = screen.getByText('Create Selected Tasks')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('1 task created successfully!')).toBeInTheDocument()
    })
  })

  it('handles partial success when creating multiple tasks', async () => {
    const mockCreateTask = vi.mocked(api.createTaskFromSuggestion)
    mockCreateTask
      .mockResolvedValueOnce({ success: true, task_id: 'task-123' })
      .mockRejectedValueOnce(new Error('Failed'))

    render(<TaskSuggestionModal {...mockProps} />)
    
    // Select two tasks
    const checkboxes = screen.getAllByRole('checkbox')
    fireEvent.click(checkboxes[0])
    fireEvent.click(checkboxes[1])
    
    const createButton = screen.getByText('Create Selected Tasks')
    fireEvent.click(createButton)

    await waitFor(() => {
      expect(screen.getByText('1 of 2 tasks created successfully')).toBeInTheDocument()
    })
  })

  it('closes modal when close button is clicked', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const closeButton = screen.getByLabelText('Close')
    fireEvent.click(closeButton)

    expect(mockProps.onClose).toHaveBeenCalled()
  })

  it('closes modal when cancel button is clicked', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const cancelButton = screen.getByText('Cancel')
    fireEvent.click(cancelButton)

    expect(mockProps.onClose).toHaveBeenCalled()
  })

  it('does not render when isOpen is false', () => {
    render(<TaskSuggestionModal {...mockProps} isOpen={false} />)
    
    expect(screen.queryByText('Task Suggestions')).not.toBeInTheDocument()
  })

  it('shows priority badges with correct styling', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    const highPriorityBadge = screen.getByText('high')
    const mediumPriorityBadge = screen.getByText('medium')
    const lowPriorityBadge = screen.getByText('low')

    expect(highPriorityBadge).toHaveClass('priority-high')
    expect(mediumPriorityBadge).toHaveClass('priority-medium')
    expect(lowPriorityBadge).toHaveClass('priority-low')
  })

  it('shows category information', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    expect(screen.getByText('documentation')).toBeInTheDocument()
    expect(screen.getByText('review')).toBeInTheDocument()
    expect(screen.getByText('communication')).toBeInTheDocument()
  })

  it('displays meeting analysis details', () => {
    render(<TaskSuggestionModal {...mockProps} />)
    
    expect(screen.getByText('Key Decisions:')).toBeInTheDocument()
    expect(screen.getByText('Extend deadline by one week')).toBeInTheDocument()
    
    expect(screen.getByText('Action Items:')).toBeInTheDocument()
    expect(screen.getByText('Review code')).toBeInTheDocument()
    expect(screen.getByText('Update docs')).toBeInTheDocument()
    
    expect(screen.getByText('Participants:')).toBeInTheDocument()
    expect(screen.getByText('Alice, Bob, John')).toBeInTheDocument()
  })
})