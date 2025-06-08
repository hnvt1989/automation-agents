import { StickyNote } from 'lucide-react'

const NotesTab = () => {
  return (
    <div className="items-list">
      <div className="empty-state">
        <div className="empty-state-icon">
          <StickyNote size={32} />
        </div>
        <h3 className="empty-state-title">Notes Tab</h3>
        <p className="empty-state-description">
          Note management coming soon...
        </p>
      </div>
    </div>
  )
}

export default NotesTab