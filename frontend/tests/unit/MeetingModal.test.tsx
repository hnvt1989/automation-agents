/**
 * Tests for MeetingModal component with analyze functionality
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MeetingModal } from '../../src/components/Workspace/MeetingModal'
import * as api from '../../src/services/api'

// Mock the API
vi.mock('../../src/services/api', () => ({
  analyzeMeeting: vi.fn(),
  createTaskFromSuggestion: vi.fn(),
  getMeetingContent: vi.fn()
}))

// Mock the store
const mockStore = {
  modal: {
    isOpen: true,
    mode: 'view' as const,
    item: {
      id: 'meeting-1',
      name: 'Team Standup',
      type: 'meeting' as const,
      date: '2025-06-08',
      event: 'Team Standup',
      content: 'Meeting content here...',
      lastModified: new Date()
    }
  },
  closeModal: vi.fn(),
  setModal: vi.fn()
}

vi.mock('../../src/store', () => ({
  useStore: vi.fn(() => mockStore)
}))

describe('MeetingModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders meeting modal with basic information', () => {
    render(<MeetingModal />)
    
    expect(screen.getByRole('heading', { name: 'Team Standup' })).toBeInTheDocument()
    expect(screen.getByText('Meeting content here...')).toBeInTheDocument()
  })

  it('shows analyze button when viewing a meeting', () => {
    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    expect(analyzeButton).toBeInTheDocument()
    expect(analyzeButton).not.toBeDisabled()
  })

  it('disables analyze button while analysis is in progress', async () => {
    const mockAnalyzeMeeting = vi.mocked(api.analyzeMeeting)
    mockAnalyzeMeeting.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    fireEvent.click(analyzeButton)

    await waitFor(() => {
      expect(screen.getByText('Analyzing...')).toBeInTheDocument()
    })
  })

  it('calls analyze API when analyze button is clicked', async () => {
    const mockAnalyzeMeeting = vi.mocked(api.analyzeMeeting)
    mockAnalyzeMeeting.mockResolvedValue({
      success: true,
      analysis: {
        meeting_date: '2025-06-08',
        meeting_title: 'Team Standup',
        summary: 'Team discussed project progress',
        suggested_tasks: [
          {
            title: 'Update documentation',
            description: 'Update the project README',
            priority: 'high',
            deadline: '2025-06-15',
            assignee: 'John',
            category: 'documentation',
            confidence: 0.9,
            context: 'Discussed during meeting'
          }
        ],
        key_decisions: ['Extend deadline by one week'],
        action_items: ['Review code', 'Update docs'],
        next_steps: ['Schedule follow-up'],
        participants: ['Alice', 'Bob'],
        confidence_score: 0.85
      }
    })

    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    fireEvent.click(analyzeButton)

    await waitFor(() => {
      expect(mockAnalyzeMeeting).toHaveBeenCalledWith({
        meeting_content: 'Meeting content here...',
        meeting_date: '2025-06-08',
        meeting_title: 'Team Standup'
      })
    })
  })

  it('shows task suggestions modal after successful analysis', async () => {
    const mockAnalyzeMeeting = vi.mocked(api.analyzeMeeting)
    mockAnalyzeMeeting.mockResolvedValue({
      success: true,
      analysis: {
        meeting_date: '2025-06-08',
        meeting_title: 'Team Standup',
        summary: 'Team discussed project progress',
        suggested_tasks: [
          {
            title: 'Update documentation',
            description: 'Update the project README',
            priority: 'high',
            deadline: '2025-06-15',
            assignee: 'John',
            category: 'documentation',
            confidence: 0.9,
            context: 'Discussed during meeting'
          }
        ],
        key_decisions: [],
        action_items: [],
        next_steps: [],
        participants: [],
        confidence_score: 0.85
      }
    })

    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    fireEvent.click(analyzeButton)

    await waitFor(() => {
      expect(screen.getByText('Task Suggestions')).toBeInTheDocument()
      expect(screen.getByText('Update documentation')).toBeInTheDocument()
      expect(screen.getByText('high')).toBeInTheDocument()
    })
  })

  it('displays error message when analysis fails', async () => {
    const mockAnalyzeMeeting = vi.mocked(api.analyzeMeeting)
    mockAnalyzeMeeting.mockResolvedValue({
      success: false,
      error: 'Analysis failed due to network error'
    })

    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    fireEvent.click(analyzeButton)

    await waitFor(() => {
      expect(screen.getByText('Analysis failed due to network error')).toBeInTheDocument()
    })
  })

  it('handles API errors gracefully', async () => {
    const mockAnalyzeMeeting = vi.mocked(api.analyzeMeeting)
    mockAnalyzeMeeting.mockRejectedValue(new Error('Network error'))

    render(<MeetingModal />)
    
    const analyzeButton = screen.getByText('Analyze')
    fireEvent.click(analyzeButton)

    await waitFor(() => {
      expect(screen.getByText(/Failed to analyze meeting/)).toBeInTheDocument()
    })
  })

  it('closes modal when close button is clicked', () => {
    render(<MeetingModal />)
    
    const closeButton = screen.getByLabelText('Close')
    fireEvent.click(closeButton)

    expect(mockStore.closeModal).toHaveBeenCalled()
  })

  it('shows empty state when no meeting is selected', () => {
    const emptyStore = {
      ...mockStore,
      modal: {
        ...mockStore.modal,
        item: null
      }
    }

    const { useStore } = require('../../src/store')
    vi.mocked(useStore).mockReturnValueOnce(emptyStore)

    render(<MeetingModal />)
    
    expect(screen.getByText('No meeting selected')).toBeInTheDocument()
  })

  it('shows correct modal title based on mode', () => {
    const editStore = {
      ...mockStore,
      modal: {
        ...mockStore.modal,
        mode: 'edit' as const
      }
    }

    const { useStore } = require('../../src/store')
    vi.mocked(useStore).mockReturnValueOnce(editStore)

    render(<MeetingModal />)
    
    expect(screen.getByText('Edit Meeting')).toBeInTheDocument()
  })
})