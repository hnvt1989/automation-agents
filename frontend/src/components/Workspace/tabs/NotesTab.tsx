import { useEffect, useState } from 'react'
import { Calendar, Users, ChevronRight, Zap } from 'lucide-react'
import { useAppStore } from '@/store'
import { Meeting } from '@/types'
import { getMeetings } from '@/services/api'

const NotesTab = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const setModal = useAppStore((state) => state.setModal)

  useEffect(() => {
    loadMeetings()
  }, [])

  const loadMeetings = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await getMeetings()
      if (response.success && response.data) {
        // The backend returns meetings in a 'meetings' property
        const meetingsData = (response as any).meetings || response.data || []
        setMeetings(meetingsData)
      } else {
        setError('Failed to load meetings')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load meetings')
      console.error('Error loading meetings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleViewMeeting = (meeting: Meeting) => {
    setModal({
      isOpen: true,
      mode: 'view',
      item: meeting
    })
  }

  const handleAnalyzeMeeting = (meeting: Meeting, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering the view modal
    setModal({
      isOpen: true,
      mode: 'view',
      item: meeting
    })
    // The analyze functionality will be handled by the MeetingModal component
  }

  if (loading) {
    return (
      <div className="items-list">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <span>Loading meeting notes from API...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="items-list">
        <div className="error-state">
          <p className="error-message">❌ Error: {error}</p>
          <p className="error-details">Make sure the backend server is running with: <code>uvicorn src.api_server:app --reload</code></p>
          <button onClick={loadMeetings} className="btn btn-outline btn-sm">
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (meetings.length === 0) {
    return (
      <div className="items-list">
        <div className="empty-state">
          <div className="empty-state-icon">
            <Users size={32} />
          </div>
          <h3 className="empty-state-title">No Meeting Notes</h3>
          <p className="empty-state-description">
            No meeting notes found from API. Meeting notes will appear here once available.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="items-list">
      <div className="items-header">
        <h3>Meeting Notes</h3>
        <span className="items-count">{meetings.length} meeting{meetings.length !== 1 ? 's' : ''}</span>
      </div>
      
      <div className="items-grid">
        {meetings.map((meeting, index) => (
          <div
            key={meeting.id || index}
            className="item-card meeting-card"
            onClick={() => handleViewMeeting(meeting)}
          >
            <div className="item-header">
              <div className="item-icon meeting-icon">
                <Users size={16} />
              </div>
              <h4 className="item-title">{meeting.event || meeting.name}</h4>
              <button
                className="analyze-btn"
                onClick={(e) => handleAnalyzeMeeting(meeting, e)}
                title="Analyze meeting and suggest tasks"
              >
                <Zap size={14} />
              </button>
            </div>

            <div className="item-meta">
              <div className="meta-item">
                <Calendar size={12} />
                <span>{meeting.date}</span>
                {meeting.time && <span>{meeting.time}</span>}
              </div>
            </div>

            {meeting.content && (
              <div className="item-preview">
                {meeting.content.slice(0, 150)}
                {meeting.content.length > 150 && '...'}
              </div>
            )}

            <div className="item-footer">
              <span className="item-type">Meeting Note</span>
              <ChevronRight size={14} />
            </div>
          </div>
        ))}
      </div>
      
      <style jsx>{`
        .error-state {
          text-align: center;
          padding: 2rem;
        }
        
        .error-message {
          color: #ef4444;
          font-size: 1.1rem;
          margin-bottom: 0.5rem;
        }
        
        .error-details {
          color: #6b7280;
          margin-bottom: 1rem;
        }
        
        .error-details code {
          background: #f3f4f6;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-family: monospace;
        }
        
        .loading-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          gap: 1rem;
        }
        
        .loading-spinner {
          width: 40px;
          height: 40px;
          border: 3px solid #e5e7eb;
          border-top-color: #3b82f6;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .items-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1rem;
          padding: 1rem;
        }
        
        .item-card {
          background: #fff;
          border: 1px solid #e5e7eb;
          border-radius: 0.5rem;
          padding: 1rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .item-card:hover {
          border-color: #3b82f6;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        .item-header {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
        }
        
        .item-icon {
          width: 32px;
          height: 32px;
          background: #eff6ff;
          border-radius: 0.375rem;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #3b82f6;
        }
        
        .item-title {
          flex: 1;
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
        }
        
        .analyze-btn {
          background: #fef3c7;
          color: #f59e0b;
          border: none;
          padding: 0.375rem;
          border-radius: 0.375rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .analyze-btn:hover {
          background: #fde68a;
          transform: scale(1.1);
        }
        
        .item-meta {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
          color: #6b7280;
          font-size: 0.875rem;
        }
        
        .meta-item {
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }
        
        .item-preview {
          color: #4b5563;
          font-size: 0.875rem;
          line-height: 1.5;
          margin-bottom: 0.75rem;
        }
        
        .item-footer {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding-top: 0.75rem;
          border-top: 1px solid #e5e7eb;
        }
        
        .item-type {
          background: #e0e7ff;
          color: #4338ca;
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 500;
        }
      `}</style>
    </div>
  )
}

export default NotesTab