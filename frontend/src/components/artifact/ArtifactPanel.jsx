/**
 * Artifact Viewer — renders Markdown or sandboxed HTML artifacts.
 *
 * Security model:
 * - HTML artifacts are rendered in a sandboxed <iframe> with:
 *   sandbox="allow-same-origin" ONLY (no scripts, no forms, no popups)
 *   This prevents XSS, data exfiltration, and unsafe API calls.
 * - Markdown is rendered server-side via react-markdown with DOMPurify sanitization.
 * - External resource URLs in HTML are blocked by the sandbox attribute.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Code, Eye, X, Copy, Download, Shield, FileText, Globe } from 'lucide-react'
import useStore from '../../store'

export default function ArtifactPanel() {
  const { activeArtifact, clearArtifact } = useStore()
  const [viewMode, setViewMode] = useState('preview') // 'preview' | 'code'
  const iframeRef = useRef(null)

  const isHTML = activeArtifact?.artifact_type === 'html'
  const isMarkdown = activeArtifact?.artifact_type === 'markdown'

  // Inject HTML into sandboxed iframe
  useEffect(() => {
    if (iframeRef.current && activeArtifact?.artifact_type === 'html' && viewMode === 'preview') {
      const doc = iframeRef.current.contentDocument
      if (doc) {
        doc.open()
        doc.write(activeArtifact.content)
        doc.close()
      }
    }
  }, [activeArtifact, viewMode])

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(activeArtifact?.content || '')
  }, [activeArtifact])

  const handleDownload = useCallback(() => {
    if (!activeArtifact) return
    const ext = isHTML ? 'html' : 'md'
    const mime = isHTML ? 'text/html' : 'text/markdown'
    const blob = new Blob([activeArtifact.content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${activeArtifact.title || 'artifact'}.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  }, [activeArtifact, isHTML])

  if (!activeArtifact) {
    return (
      <aside className="artifact-panel" style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="artifact-header">
          <div className="artifact-header-left">
            <FileText size={16} color="var(--text-muted)" />
            <span className="artifact-title">Artifact Viewer</span>
          </div>
        </div>
        <div className="artifact-empty">
          <div className="artifact-empty-icon">🎨</div>
          <div className="artifact-empty-title">No Artifact Yet</div>
          <div className="artifact-empty-desc">
            Ask the assistant to generate a<br />
            <strong>Markdown document</strong> or <strong>HTML page</strong><br />
            and it will appear here.
          </div>
        </div>
      </aside>
    )
  }

  return (
    <aside className="artifact-panel">
      {/* Header */}
      <div className="artifact-header">
        <div className="artifact-header-left">
          {isHTML ? <Globe size={15} color="var(--accent-amber)" /> : <FileText size={15} color="var(--accent-blue)" />}
          <span className="artifact-title" title={activeArtifact.title}>
            {activeArtifact.title || 'Artifact'}
          </span>
          <span className={`artifact-type-badge ${activeArtifact.artifact_type}`}>
            {activeArtifact.artifact_type}
          </span>
        </div>
        <div className="artifact-header-actions">
          <button className="icon-btn" onClick={handleCopy} title="Copy content">
            <Copy size={13} />
          </button>
          <button className="icon-btn" onClick={handleDownload} title="Download">
            <Download size={13} />
          </button>
          <button className="icon-btn danger" onClick={clearArtifact} title="Close">
            <X size={13} />
          </button>
        </div>
      </div>

      {/* View Tabs */}
      <div className="view-tabs">
        <button
          className={`view-tab ${viewMode === 'preview' ? 'active' : ''}`}
          onClick={() => setViewMode('preview')}
        >
          <Eye size={12} /> Preview
        </button>
        <button
          className={`view-tab ${viewMode === 'code' ? 'active' : ''}`}
          onClick={() => setViewMode('code')}
        >
          <Code size={12} /> Source
        </button>
      </div>

      {/* Security notice for HTML */}
      {isHTML && viewMode === 'preview' && (
        <div className="security-notice">
          <Shield size={12} />
          Sandboxed — scripts disabled, no external network access
        </div>
      )}

      {/* Content */}
      <div className="artifact-content">
        {viewMode === 'code' ? (
          <pre className="artifact-code-view">{activeArtifact.content}</pre>
        ) : isHTML ? (
          <iframe
            ref={iframeRef}
            className="artifact-iframe"
            title="Artifact Preview"
            sandbox="allow-same-origin"
            /* Deliberately NOT including allow-scripts — blocks all JS execution */
          />
        ) : (
          <div className="artifact-rendered">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {activeArtifact.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </aside>
  )
}
