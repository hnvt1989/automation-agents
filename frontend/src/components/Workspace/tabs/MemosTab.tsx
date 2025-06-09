import { useState, useMemo, useEffect } from 'react'
import { Plus, Edit2, Trash2, FileText, Check, BookOpen } from 'lucide-react'
import { useAppStore } from '@/store'
import { useMemos } from '@/hooks/useApi'
import { formatRelativeTime } from '@/utils'
import type { Memo } from '@/types'

const MemosTab = () => {
  const { memos, fetchMemos, updateMemo, deleteMemo, loading } = useMemos()
  const { setModal } = useAppStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [formatFilter, setFormatFilter] = useState('all')
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())

  // Fetch memos on mount
  useEffect(() => {
    fetchMemos()
  }, [])

  // Filter and search memos
  const filteredMemos = useMemo(() => {
    let filtered = memos.filter((memo) => {
      const matchesSearch = memo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          memo.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          memo.content?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesFormat = formatFilter === 'all' || memo.format === formatFilter
      
      return matchesSearch && matchesFormat
    })

    // Sort by last modified
    filtered.sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime())

    return filtered
  }, [memos, searchQuery, formatFilter])

  const handleAddMemo = () => {
    setModal({
      isOpen: true,
      mode: 'add',
      contentType: 'memo',
    })
  }

  const handleEditMemo = (memo: Memo) => {
    setModal({
      isOpen: true,
      mode: 'edit',
      item: memo,
      contentType: 'memo',
    })
  }

  const handleDeleteMemo = async (memoId: string) => {
    if (confirm('Are you sure you want to delete this memo?')) {
      await deleteMemo(memoId)
    }
  }

  const handleSelectItem = (memoId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(memoId)) {
      newSelected.delete(memoId)
    } else {
      newSelected.add(memoId)
    }
    setSelectedItems(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedItems.size === filteredMemos.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(filteredMemos.map(memo => memo.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (confirm(`Are you sure you want to delete ${selectedItems.size} memos?`)) {
      await Promise.all(Array.from(selectedItems).map(id => deleteMemo(id)))
      setSelectedItems(new Set())
    }
  }

  const totalMemos = memos.length

  return (
    <div className="items-list">
      <div className="items-header">
        <div className="items-count">
          {filteredMemos.length} memos
          {filteredMemos.length !== totalMemos && ` (${totalMemos} total)`}
        </div>
        <button className="add-button" onClick={handleAddMemo}>
          <Plus size={16} />
          Add Memo
        </button>
      </div>

      <div className="search-filters">
        <input
          type="text"
          placeholder="Search memos..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
        
        <select
          value={formatFilter}
          onChange={(e) => setFormatFilter(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Formats</option>
          <option value="text">Plain Text</option>
          <option value="markdown">Markdown</option>
          <option value="rich">Rich Text</option>
        </select>
      </div>

      {selectedItems.size > 0 && (
        <div className="bulk-actions">
          <span className="bulk-actions-text">
            {selectedItems.size} selected
          </span>
          <button
            className="bulk-action-button danger"
            onClick={handleBulkDelete}
          >
            Delete Selected
          </button>
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner" />
          <span>Loading memos...</span>
        </div>
      )}

      {!loading && filteredMemos.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <BookOpen size={32} />
          </div>
          <h3 className="empty-state-title">
            {memos.length === 0 ? 'No memos yet' : 'No memos match your filters'}
          </h3>
          <p className="empty-state-description">
            {memos.length === 0 
              ? 'Get started by creating your first memo to capture quick notes and ideas.'
              : 'Try adjusting your search or filter criteria to find the memos you\'re looking for.'
            }
          </p>
          {memos.length === 0 && (
            <button className="btn btn-primary" onClick={handleAddMemo}>
              <Plus size={16} />
              Create Your First Memo
            </button>
          )}
        </div>
      )}

      {!loading && filteredMemos.length > 0 && (
        <>
          <div className="list-header">
            <label className="select-all-checkbox">
              <input
                type="checkbox"
                checked={selectedItems.size === filteredMemos.length}
                onChange={handleSelectAll}
              />
              Select All
            </label>
          </div>

          {filteredMemos.map((memo) => (
            <div
              key={memo.id}
              className={`workspace-item ${selectedItems.has(memo.id) ? 'selected' : ''}`}
              data-testid="memo-item"
            >
              <div
                className={`item-checkbox ${selectedItems.has(memo.id) ? 'checked' : ''}`}
                onClick={() => handleSelectItem(memo.id)}
              >
                {selectedItems.has(memo.id) && <Check size={12} />}
              </div>

              <div className="item-icon memo">
                <BookOpen size={20} />
              </div>

              <div className="item-content">
                <div className="item-title">{memo.name}</div>
                {memo.description && (
                  <div className="item-description">{memo.description}</div>
                )}
                {memo.content && (
                  <div className="item-preview">
                    {memo.content.slice(0, 100)}
                    {memo.content.length > 100 && '...'}
                  </div>
                )}
                <div className="item-meta">
                  <span className="item-format">{memo.format}</span>
                  <span className="item-date">
                    {formatRelativeTime(memo.lastModified)}
                  </span>
                  {memo.tags && memo.tags.length > 0 && (
                    <div className="item-tags">
                      {memo.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="tag">
                          {tag}
                        </span>
                      ))}
                      {memo.tags.length > 3 && (
                        <span className="tag-more">+{memo.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="item-actions">
                <button
                  className="action-button edit"
                  onClick={() => handleEditMemo(memo)}
                  title="Edit memo"
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="action-button delete"
                  onClick={() => handleDeleteMemo(memo.id)}
                  title="Delete memo"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

export default MemosTab 