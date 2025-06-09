import { useState, useMemo, useEffect } from 'react'
import { Plus, Edit2, Trash2, FileText, Check } from 'lucide-react'
import { useAppStore } from '@/store'
import { useDocuments } from '@/hooks/useApi'
import { formatRelativeTime } from '@/utils'
import type { Document } from '@/types'

const DocumentsTab = () => {
  const { documents, fetchDocuments, updateDocument, deleteDocument, loading } = useDocuments()
  const { setModal } = useAppStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [formatFilter, setFormatFilter] = useState('all')
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments()
  }, [])

  // Filter and search documents
  const filteredDocuments = useMemo(() => {
    let filtered = documents.filter((doc) => {
      const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.content?.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesFormat = formatFilter === 'all' || doc.format === formatFilter
      
      return matchesSearch && matchesFormat
    })

    // Sort by last modified
    filtered.sort((a, b) => new Date(b.lastModified).getTime() - new Date(a.lastModified).getTime())

    return filtered
  }, [documents, searchQuery, formatFilter])

  const handleAddDocument = () => {
    setModal({
      isOpen: true,
      mode: 'add',
      contentType: 'document',
    })
  }

  const handleEditDocument = (document: Document) => {
    setModal({
      isOpen: true,
      mode: 'edit',
      item: document,
      contentType: 'document',
    })
  }

  const handleDeleteDocument = async (documentId: string) => {
    if (confirm('Are you sure you want to delete this document?')) {
      await deleteDocument(documentId)
    }
  }

  const handleSelectItem = (documentId: string) => {
    const newSelected = new Set(selectedItems)
    if (newSelected.has(documentId)) {
      newSelected.delete(documentId)
    } else {
      newSelected.add(documentId)
    }
    setSelectedItems(newSelected)
  }

  const handleSelectAll = () => {
    if (selectedItems.size === filteredDocuments.length) {
      setSelectedItems(new Set())
    } else {
      setSelectedItems(new Set(filteredDocuments.map(doc => doc.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (confirm(`Are you sure you want to delete ${selectedItems.size} documents?`)) {
      await Promise.all(Array.from(selectedItems).map(id => deleteDocument(id)))
      setSelectedItems(new Set())
    }
  }

  const totalDocuments = documents.length

  return (
    <div className="items-list">
      <div className="items-header">
        <div className="items-count">
          {filteredDocuments.length} documents
          {filteredDocuments.length !== totalDocuments && ` (${totalDocuments} total)`}
        </div>
        <button className="add-button" onClick={handleAddDocument}>
          <Plus size={16} />
          Add Document
        </button>
      </div>

      <div className="search-filters">
        <input
          type="text"
          placeholder="Search documents..."
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
          <span>Loading documents...</span>
        </div>
      )}

      {!loading && filteredDocuments.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">
            <FileText size={32} />
          </div>
          <h3 className="empty-state-title">
            {documents.length === 0 ? 'No documents yet' : 'No documents match your filters'}
          </h3>
          <p className="empty-state-description">
            {documents.length === 0 
              ? 'Get started by creating your first document to store and organize your information.'
              : 'Try adjusting your search or filter criteria to find the documents you\'re looking for.'
            }
          </p>
          {documents.length === 0 && (
            <button className="btn btn-primary" onClick={handleAddDocument}>
              <Plus size={16} />
              Create Your First Document
            </button>
          )}
        </div>
      )}

      {!loading && filteredDocuments.length > 0 && (
        <>
          <div className="list-header">
            <label className="select-all-checkbox">
              <input
                type="checkbox"
                checked={selectedItems.size === filteredDocuments.length}
                onChange={handleSelectAll}
              />
              Select All
            </label>
          </div>

          {filteredDocuments.map((document) => (
            <div
              key={document.id}
              className={`workspace-item ${selectedItems.has(document.id) ? 'selected' : ''}`}
              data-testid="document-item"
            >
              <div
                className={`item-checkbox ${selectedItems.has(document.id) ? 'checked' : ''}`}
                onClick={() => handleSelectItem(document.id)}
              >
                {selectedItems.has(document.id) && <Check size={12} />}
              </div>

              <div className="item-icon document">
                <FileText size={20} />
              </div>

              <div className="item-content">
                <div className="item-title">{document.name}</div>
                {document.description && (
                  <div className="item-description">{document.description}</div>
                )}
                {document.content && (
                  <div className="item-content-preview">
                    {document.content.substring(0, 150)}{document.content.length > 150 ? '...' : ''}
                  </div>
                )}
                <div className="item-meta">
                  <span className="item-format">{document.format}</span>
                  <span>Updated {formatRelativeTime(document.lastModified)}</span>
                  {document.tags && document.tags.length > 0 && (
                    <span className="item-tags">
                      {document.tags.map(tag => (
                        <span key={tag} className="tag">{tag}</span>
                      ))}
                    </span>
                  )}
                </div>
              </div>

              <div className="item-actions">
                <button
                  className="item-action-button"
                  onClick={() => handleEditDocument(document)}
                  title="Edit document"
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="item-action-button danger"
                  onClick={() => handleDeleteDocument(document.id)}
                  title="Delete document"
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

export default DocumentsTab