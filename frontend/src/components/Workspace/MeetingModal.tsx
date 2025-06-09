import React, { useState, useEffect } from 'react'
import { useAppStore } from '@/store'
import { analyzeMeeting } from '@/services/api'
import { Meeting, MeetingAnalysis } from '@/types'
import { TaskSuggestionModal } from './TaskSuggestionModal'

export const MeetingModal: React.FC = () => {
  const { modal, closeModal } = useAppStore()
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<MeetingAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showTaskSuggestions, setShowTaskSuggestions] = useState(false)

  const meeting = modal.item as Meeting

  useEffect(() => {
    // Reset state when modal opens/closes
    if (!modal.isOpen) {
      setAnalysis(null)
      setError(null)
      setShowTaskSuggestions(false)
      setIsAnalyzing(false)
    }
  }, [modal.isOpen])

  const handleAnalyze = async () => {
    if (!meeting || !meeting.content) {
      setError('No meeting content to analyze')
      return
    }

    setIsAnalyzing(true)
    setError(null)

    try {
      const response = await analyzeMeeting({
        meeting_content: meeting.content,
        meeting_date: meeting.date,
        meeting_title: meeting.event || meeting.name
      })

      if (response.success && response.data?.analysis) {
        setAnalysis(response.data.analysis)
        setShowTaskSuggestions(true)
      } else {
        setError(response.error || 'Analysis failed')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to analyze meeting')
    } finally {
      setIsAnalyzing(false)
    }
  }

  const handleCloseTaskSuggestions = () => {
    setShowTaskSuggestions(false)
  }

  if (!modal.isOpen || !meeting) {
    return null
  }

  const getModalTitle = () => {
    switch (modal.mode) {
      case 'add':
        return 'Add Meeting'
      case 'edit':
        return 'Edit Meeting'
      case 'view':
      default:
        return meeting.event || meeting.name || 'Meeting Details'
    }
  }

  return (
    <>
      <div className="modal-overlay" onClick={closeModal}>
        <div className="modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h2>{getModalTitle()}</h2>
            <button
              className="close-button"
              onClick={closeModal}
              aria-label="Close"
            >
              ×
            </button>
          </div>

          <div className="modal-body">
            {!meeting ? (
              <div className="empty-state">
                <p>No meeting selected</p>
              </div>
            ) : (
              <div className="meeting-details">
                <div className="meeting-info">
                  <div className="info-row">
                    <label>Date:</label>
                    <span>{meeting.date}</span>
                  </div>
                  {meeting.time && (
                    <div className="info-row">
                      <label>Time:</label>
                      <span>{meeting.time}</span>
                    </div>
                  )}
                  <div className="info-row">
                    <label>Event:</label>
                    <span>{meeting.event}</span>
                  </div>
                  {meeting.participants && meeting.participants.length > 0 && (
                    <div className="info-row">
                      <label>Participants:</label>
                      <span>{meeting.participants.join(', ')}</span>
                    </div>
                  )}
                  {meeting.location && (
                    <div className="info-row">
                      <label>Location:</label>
                      <span>{meeting.location}</span>
                    </div>
                  )}
                </div>

                {meeting.content && (
                  <div className="meeting-content">
                    <label>Meeting Notes:</label>
                    <div className="content-text">
                      {meeting.content}
                    </div>
                  </div>
                )}

                {error && (
                  <div className="error-message">
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button 
              className="btn btn-secondary" 
              onClick={closeModal}
            >
              Close
            </button>
            {modal.mode === 'view' && meeting?.content && (
              <button
                className="btn btn-primary"
                onClick={handleAnalyze}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? 'Analyzing...' : 'Analyze'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Task Suggestions Modal */}
      {analysis && (
        <TaskSuggestionModal
          isOpen={showTaskSuggestions}
          onClose={handleCloseTaskSuggestions}
          analysis={analysis}
        />
      )}
    </>
  )
}

export default MeetingModal