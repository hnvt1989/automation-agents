import { Settings } from 'lucide-react'

const Configuration = () => {
  return (
    <div className="items-list">
      <div className="empty-state">
        <div className="empty-state-icon">
          <Settings size={32} />
        </div>
        <h3 className="empty-state-title">Configuration</h3>
        <p className="empty-state-description">
          Configuration management coming soon...
        </p>
      </div>
    </div>
  )
}

export default Configuration