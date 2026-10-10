/**
 * Message bubble — renders user and AI messages with full metadata.
 * AI messages: markdown rendering, source citations, artifact links.
 */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BookOpen, Zap, Clock, ExternalLink } from 'lucide-react'
import useStore from '../../store'
import { formatDistanceToNow } from 'date-fns'

const SKILL_LABELS = {
  rag_qa: { label: 'RAG Q&A', color: 'var(--accent-blue)', icon: '🔍' },
  ship_30_essay: { label: 'Ship 30 Essay', color: 'var(--accent-purple)', icon: '✍️' },
  artifact_markdown: { label: 'Markdown Doc', color: 'var(--accent-emerald)', icon: '📄' },
  artifact_html: { label: 'HTML Page', color: 'var(--accent-amber)', icon: '🌐' },
}

export default function MessageBubble({ message }) {
  const { fetchArtifact, activeArtifact, setActiveArtifact } = useStore()
  const isUser = message.role === 'user'
  const skill = message.skill_used ? SKILL_LABELS[message.skill_used] : null

  const timeAgo = message.created_at
    ? formatDistanceToNow(new Date(message.created_at), { addSuffix: true })
    : ''

  return (
    <div className={`message-row ${isUser ? 'user' : 'ai'}`}>
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? 'user-avatar' : 'ai-avatar'}`}>
        {isUser ? '👤' : '🧠'}
      </div>

      {/* Content */}
      <div className="message-content-wrapper">
        <div className={`message-bubble ${isUser ? 'user-bubble' : 'ai-bubble'}`}>
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>

        {/* Metadata row */}
        {!isUser && (
          <div className="message-meta">
            {skill && (
              <span className="meta-tag skill" style={{ color: skill.color }}>
                {skill.icon} {skill.label}
              </span>
            )}
            {message.latency_ms && (
              <span className="meta-tag">
                <Clock size={10} /> {Math.round(message.latency_ms)}ms
              </span>
            )}
            {message.sources?.length > 0 && (
              <span className="meta-tag source">
                <BookOpen size={10} /> {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
              </span>
            )}
            {timeAgo && (
              <span className="meta-tag" style={{ marginLeft: 'auto' }}>{timeAgo}</span>
            )}
          </div>
        )}

        {/* Sources panel */}
        {!isUser && message.sources?.length > 0 && (
          <div className="sources-panel">
            <div className="sources-title">
              <BookOpen size={11} /> Grounded Sources
            </div>
            {message.sources.map((src, i) => (
              <div key={i} className="source-item">
                <span className="source-ep">
                  {src.episode_number ? `Ep. ${src.episode_number}` : '—'}
                </span>
                <span className="source-title">
                  {src.episode_title}{src.guest ? ` — ${src.guest}` : ''}
                </span>
                <span className="source-score">{(src.relevance_score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        )}

        {/* Artifact link */}
        {!isUser && message.artifact_id && (
          <button
            className="artifact-link-btn"
            onClick={() => fetchArtifact(message.artifact_id)}
          >
            <ExternalLink size={12} />
            View Generated Artifact
          </button>
        )}
      </div>
    </div>
  )
}
