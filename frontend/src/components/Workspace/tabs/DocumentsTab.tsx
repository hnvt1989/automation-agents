import { FileText } from 'lucide-react'

const DocumentsTab = () => {
  return (
    <div className="items-list">
      <div className="empty-state">
        <div className="empty-state-icon">
          <FileText size={32} />
        </div>
        <h3 className="empty-state-title">Documents Tab</h3>
        <p className="empty-state-description">
          Document management coming soon...
        </p>
      </div>
    </div>
  )
}

export default DocumentsTab