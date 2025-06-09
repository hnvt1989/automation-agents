import React from 'react'
import { describe, test, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import NotificationToast from '@/components/common/NotificationToast'

describe('NotificationToast', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('should render success notification', () => {
    render(
      <NotificationToast
        id="1"
        message="Success message"
        type="success"
        onClose={mockOnClose}
      />
    )

    expect(screen.getByText('Success message')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveClass('notification-toast', 'toast-success')
  })

  test('should render error notification', () => {
    render(
      <NotificationToast
        id="1"
        message="Error message"
        type="error"
        onClose={mockOnClose}
      />
    )

    expect(screen.getByText('Error message')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveClass('notification-toast', 'toast-error')
  })

  test('should render info notification', () => {
    render(
      <NotificationToast
        id="1"
        message="Info message"
        type="info"
        onClose={mockOnClose}
      />
    )

    expect(screen.getByText('Info message')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveClass('notification-toast', 'toast-info')
  })

  test('should call onClose when close button is clicked', () => {
    render(
      <NotificationToast
        id="test-id"
        message="Test message"
        type="success"
        onClose={mockOnClose}
      />
    )

    const closeButton = screen.getByLabelText('Close notification')
    fireEvent.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledWith('test-id')
  })

  test('should auto-close after default duration', () => {
    render(
      <NotificationToast
        id="auto-close"
        message="Auto close message"
        type="info"
        onClose={mockOnClose}
      />
    )

    expect(mockOnClose).not.toHaveBeenCalled()

    // Fast-forward time
    vi.advanceTimersByTime(5000)

    expect(mockOnClose).toHaveBeenCalledWith('auto-close')
  })

  test('should auto-close after custom duration', () => {
    render(
      <NotificationToast
        id="custom-duration"
        message="Custom duration message"
        type="info"
        onClose={mockOnClose}
        duration={3000}
      />
    )

    expect(mockOnClose).not.toHaveBeenCalled()

    // Fast-forward time
    vi.advanceTimersByTime(3000)

    expect(mockOnClose).toHaveBeenCalledWith('custom-duration')
  })

  test('should not auto-close when duration is 0', () => {
    render(
      <NotificationToast
        id="no-auto-close"
        message="No auto close"
        type="error"
        onClose={mockOnClose}
        duration={0}
      />
    )

    // Fast-forward time
    vi.advanceTimersByTime(10000)

    expect(mockOnClose).not.toHaveBeenCalled()
  })

  test('should have proper accessibility attributes', () => {
    render(
      <NotificationToast
        id="a11y-test"
        message="Accessibility test"
        type="success"
        onClose={mockOnClose}
      />
    )

    const alert = screen.getByRole('alert')
    expect(alert).toHaveAttribute('aria-live', 'polite')
  })
})