import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import LogsTab from '@/components/Workspace/tabs/LogsTab'
import { useAppStore } from '@/store'
import { useLogs } from '@/hooks/useApi'
import type { DailyLog } from '@/types'

// Mock the hooks
vi.mock('@/store', () => ({
  useAppStore: vi.fn()
}))

vi.mock('@/hooks/useApi', () => ({
  useLogs: vi.fn()
}))

vi.mock('@/utils', () => ({
  getStatusColor: vi.fn((status) => status),
  formatRelativeTime: vi.fn((date) => 'a few minutes ago')
}))

const mockSetModal = vi.fn()
const mockUpdateLog = vi.fn()
const mockDeleteLog = vi.fn()

const mockLogs: DailyLog[] = [
  {
    id: '1',
    name: 'Personal Log 1',
    description: 'Personal activities today',
    type: 'log',
    date: new Date(),
    content: 'Had a good workout and read a book',
    lastModified: new Date(),
    mood: 'positive',
    productivity: 8,
    tags: ['personal']
  },
  {
    id: '2',
    name: 'Work Log 1',
    description: 'Work activities today',
    type: 'log',
    date: new Date(),
    content: 'Completed the project milestone',
    lastModified: new Date(),
    mood: 'positive',
    productivity: 9,
    tags: ['work']
  },
  {
    id: '3',
    name: 'Personal Log 2',
    description: 'Another personal log',
    type: 'log',
    date: new Date(),
    content: 'Spent time with family',
    lastModified: new Date(),
    mood: 'positive',
    productivity: 7,
    tags: ['personal']
  },
  {
    id: '4',
    name: 'Work Log 2',
    description: 'Another work log',
    type: 'log',
    date: new Date(),
    content: 'Attended important meeting',
    lastModified: new Date(),
    mood: 'neutral',
    productivity: 6,
    tags: ['work']
  }
]

describe('LogsTab', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAppStore as any).mockReturnValue({
      setModal: mockSetModal
    })
    ;(useLogs as any).mockReturnValue({
      logs: mockLogs,
      updateLog: mockUpdateLog,
      deleteLog: mockDeleteLog,
      loading: false
    })
  })

  describe('Daily Log Tag Filtering', () => {
    it('should show all logs by default', () => {
      render(<LogsTab />)
      expect(screen.getByText('Personal Log 1')).toBeInTheDocument()
      expect(screen.getByText('Work Log 1')).toBeInTheDocument()
      expect(screen.getByText('Personal Log 2')).toBeInTheDocument()
      expect(screen.getByText('Work Log 2')).toBeInTheDocument()
    })

    it('should filter logs by personal tag', async () => {
      render(<LogsTab />)
      
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Log 1')).toBeInTheDocument()
        expect(screen.getByText('Personal Log 2')).toBeInTheDocument()
        expect(screen.queryByText('Work Log 1')).not.toBeInTheDocument()
        expect(screen.queryByText('Work Log 2')).not.toBeInTheDocument()
      })
    })

    it('should filter logs by work tag', async () => {
      render(<LogsTab />)
      
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'work' } })
      
      await waitFor(() => {
        expect(screen.getByText('Work Log 1')).toBeInTheDocument()
        expect(screen.getByText('Work Log 2')).toBeInTheDocument()
        expect(screen.queryByText('Personal Log 1')).not.toBeInTheDocument()
        expect(screen.queryByText('Personal Log 2')).not.toBeInTheDocument()
      })
    })

    it('should reset to show all logs when "All Tags" is selected', async () => {
      render(<LogsTab />)
      
      const tagFilter = screen.getByDisplayValue('All Tags')
      
      // First filter by personal
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      await waitFor(() => {
        expect(screen.queryByText('Work Log 1')).not.toBeInTheDocument()
      })
      
      // Then reset to all
      fireEvent.change(tagFilter, { target: { value: 'all' } })
      await waitFor(() => {
        expect(screen.getByText('Personal Log 1')).toBeInTheDocument()
        expect(screen.getByText('Work Log 1')).toBeInTheDocument()
        expect(screen.getByText('Personal Log 2')).toBeInTheDocument()
        expect(screen.getByText('Work Log 2')).toBeInTheDocument()
      })
    })

    it('should show empty state when no logs match the filter', async () => {
      // Mock logs that don't have 'personal' tags for this test
      const logsWithoutPersonalTags = mockLogs.filter(log => !log.tags?.includes('personal'))
      ;(useLogs as any).mockReturnValue({
        logs: logsWithoutPersonalTags,
        updateLog: mockUpdateLog,
        deleteLog: mockDeleteLog,
        loading: false
      })

      render(<LogsTab />)
      
      // Apply personal filter - should show no results
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      
      await waitFor(() => {
        expect(screen.getByText('No logs match your filters')).toBeInTheDocument()
      })
    })

    it('should maintain search functionality when tag filter is applied', async () => {
      render(<LogsTab />)
      
      // Apply personal tag filter
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      
      // Search within personal logs
      const searchInput = screen.getByPlaceholderText('Search logs...')
      fireEvent.change(searchInput, { target: { value: 'workout' } })
      
      await waitFor(() => {
        expect(screen.getByText('Personal Log 1')).toBeInTheDocument()
        expect(screen.queryByText('Personal Log 2')).not.toBeInTheDocument()
        expect(screen.queryByText('Work Log 1')).not.toBeInTheDocument()
        expect(screen.queryByText('Work Log 2')).not.toBeInTheDocument()
      })
    })

    it('should show correct count when filters are applied', async () => {
      render(<LogsTab />)
      
      // Initially shows all logs
      expect(screen.getByText('4 logs')).toBeInTheDocument()
      
      // Filter by personal
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      
      await waitFor(() => {
        expect(screen.getByText('2 logs (4 total)')).toBeInTheDocument()
      })
    })

    it('should handle logs with multiple tags correctly', async () => {
      // Create a log with multiple tags
      const logsWithMultipleTags = [
        ...mockLogs,
        {
          id: '5',
          name: 'Mixed Log',
          description: 'Log with both tags',
          type: 'log' as const,
          date: new Date(),
          content: 'Work meeting about personal development',
          lastModified: new Date(),
          mood: 'positive' as const,
          productivity: 8,
          tags: ['personal', 'work']
        }
      ]

      ;(useLogs as any).mockReturnValue({
        logs: logsWithMultipleTags,
        updateLog: mockUpdateLog,
        deleteLog: mockDeleteLog,
        loading: false
      })

      render(<LogsTab />)
      
      // Filter by personal - should include the mixed log
      const tagFilter = screen.getByDisplayValue('All Tags')
      fireEvent.change(tagFilter, { target: { value: 'personal' } })
      
      await waitFor(() => {
        expect(screen.getByText('Mixed Log')).toBeInTheDocument()
        expect(screen.getByText('Personal Log 1')).toBeInTheDocument()
        expect(screen.getByText('Personal Log 2')).toBeInTheDocument()
      })
      
      // Filter by work - should also include the mixed log
      fireEvent.change(tagFilter, { target: { value: 'work' } })
      
      await waitFor(() => {
        expect(screen.getByText('Mixed Log')).toBeInTheDocument()
        expect(screen.getByText('Work Log 1')).toBeInTheDocument()
        expect(screen.getByText('Work Log 2')).toBeInTheDocument()
      })
    })
  })
})