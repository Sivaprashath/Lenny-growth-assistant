/**
 * Main App component — assembles sidebar, chat panel, and artifact panel.
 */
import { useEffect, useRef } from 'react'
import { Plus, MessageSquare, Trash2, Cpu, Wifi } from 'lucide-react'
import useStore from './store'
import MessageBubble from './components/chat/MessageBubble'
import ChatInput, { SUGGESTIONS } from './components/chat/ChatInput'
import ArtifactPanel from './components/artifact/ArtifactPanel'
import { formatDistanceToNow } from 'date-fns'

// ── Typing indicator ─────────────────────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="message-row ai">
      <div className="message-avatar ai-avatar">🧠</div>
      <div className="typing-indicator">
        <div className="typing-dot" />
        <div className="typing-dot" />
        <div className="typing-dot" />
      </div>
    </div>
  )
}

// ── Streaming message ─────────────────────────────────────────────────────────
function StreamingMessage({ content }) {
  return (
    <div className="message-row ai">
      <div className="message-avatar ai-avatar">🧠</div>
      <div className="message-content-wrapper">
        <div className="message-bubble ai-bubble">
          {content}
          <span style={{
            display: 'inline-block',
            width: 2,
            height: '1em',
            background: 'var(--accent-blue)',
            marginLeft: 2,
            animation: 'blink 1s step-end infinite',
          }} />
        </div>
      </div>
      <style>{`@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }`}</style>
    </div>
  )
}

// ── Welcome screen ────────────────────────────────────────────────────────────
function WelcomeScreen({ onSuggestion }) {
  return (
    <div className="welcome-screen">
      <div className="welcome-logo">🎙️</div>
      <h1 className="welcome-title">Lenny Growth Assistant</h1>
      <p className="welcome-subtitle">
        Your AI-powered advisor grounded in Lenny's Podcast transcripts.
        Ask product questions, generate essays, or create renderable artifacts.
      </p>
      <div className="suggestions-grid">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            className="suggestion-card"
            onClick={() => onSuggestion(s.q)}
          >
            <div className="suggestion-icon">{s.icon}</div>
            <div className="suggestion-title">{s.title}</div>
            <div className="suggestion-desc">{s.desc}</div>
          </button>
        ))}
      </div>
    </div>
  )
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar() {
  const {
    sessions, activeSessionId, createSession, setActiveSession,
    deleteSession, modelConfig,
  } = useStore()

  return (
    <nav className="sidebar" aria-label="Chat sessions">
      <div className="sidebar-header">
        <div className="logo-block">
          <div className="logo-icon">🎙️</div>
          <div className="logo-text">
            Lenny Growth
            <div className="logo-sub">AI Assistant</div>
          </div>
        </div>
        <button
          id="new-chat-btn"
          className="btn-new-chat"
          onClick={() => createSession()}
          aria-label="Start new chat"
        >
          <Plus size={14} /> New Chat
        </button>
      </div>

      <div className="sidebar-section-title">Recent Chats</div>

      <div className="sessions-list" role="list">
        {sessions.length === 0 && (
          <div style={{ padding: '12px 10px', fontSize: 12, color: 'var(--text-muted)', textAlign: 'center' }}>
            No chats yet.<br />Start a new chat above.
          </div>
        )}
        {sessions.map(session => (
          <div
            key={session.id}
            role="listitem"
            className={`session-item ${session.id === activeSessionId ? 'active' : ''}`}
            onClick={() => setActiveSession(session.id)}
          >
            <MessageSquare size={14} className="session-item-icon" />
            <div className="session-item-text">
              <div className="session-item-title">{session.title}</div>
              <div className="session-item-meta">
                {session.message_count} msg · {formatDistanceToNow(new Date(session.created_at), { addSuffix: true })}
              </div>
            </div>
            <button
              className="session-delete-btn"
              onClick={e => { e.stopPropagation(); deleteSession(session.id) }}
              aria-label="Delete session"
              title="Delete"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>

      {/* Model badge */}
      <div className="model-badge">
        <div className="model-dot" />
        <div className="model-text">
          <div className="model-label">
            {modelConfig?.current_provider === 'ollama' ? (
              <><Cpu size={10} style={{ display: 'inline', marginRight: 3 }} />Local Ollama</>
            ) : (
              <><Wifi size={10} style={{ display: 'inline', marginRight: 3 }} />Cloud</>
            )}
          </div>
          <div className="model-name">{modelConfig?.current_model || 'loading...'}</div>
        </div>
      </div>
    </nav>
  )
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function Toasts() {
  const { toasts } = useStore()
  return (
    <div className="toast-container" role="status" aria-live="polite">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          {t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : 'ℹ'} {t.message}
        </div>
      ))}
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const {
    activeSessionId, messages, isLoading, isStreaming, streamingContent,
    activeArtifact, loadSessions, loadModelConfig, sendMessage, createSession,
  } = useStore()

  const messagesEndRef = useRef(null)

  useEffect(() => {
    loadSessions()
    loadModelConfig()
  }, [])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, activeSessionId, isLoading, isStreaming, streamingContent])

  const currentMessages = activeSessionId ? (messages[activeSessionId] || []) : []

  const handleSuggestion = async (q) => {
    let session = activeSessionId
    if (!session) {
      const s = await createSession(q.slice(0, 50))
      session = s.id
    }
    await sendMessage(q, null)
  }

  const showWelcome = currentMessages.length === 0 && !isLoading && !isStreaming

  return (
    <div className="app-layout">
      <Sidebar />

      <div className="main-area">
        {/* Header */}
        <header className="chat-header">
          <div className="chat-header-left">
            <div>
              <div className="chat-header-title">
                {activeSessionId
                  ? (useStore.getState().sessions.find(s => s.id === activeSessionId)?.title || 'Chat')
                  : 'Lenny Growth Assistant'}
              </div>
              {activeSessionId && (
                <div className="chat-header-subtitle">
                  {currentMessages.length} messages
                </div>
              )}
            </div>
          </div>
          <div className="header-badges">
            <span className="badge badge-blue">RAG Grounded</span>
            <span className="badge badge-purple">Ship 30</span>
            <span className="badge badge-emerald">Artifacts</span>
          </div>
        </header>

        <div className="content-area">
          {/* Chat Panel */}
          <div className="chat-panel">
            <div className="messages-area" id="messages-area" role="log" aria-label="Chat messages">
              {showWelcome ? (
                <WelcomeScreen onSuggestion={handleSuggestion} />
              ) : (
                <>
                  {currentMessages.map(msg => (
                    <MessageBubble key={msg.id} message={msg} />
                  ))}
                  {isStreaming && streamingContent && (
                    <StreamingMessage content={streamingContent} />
                  )}
                  {isLoading && !isStreaming && <TypingIndicator />}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>

            <ChatInput />
          </div>

          {/* Artifact Panel — always mounted, hides when no artifact */}
          {activeArtifact && <ArtifactPanel />}
        </div>
      </div>

      <Toasts />
    </div>
  )
}
