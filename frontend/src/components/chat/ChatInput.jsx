/**
 * ChatInput — skill selector + auto-growing textarea + send button.
 * Handles Ctrl+Enter / Enter to send, skill override selection.
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Zap } from 'lucide-react'
import useStore from '../../store'

const SKILLS = [
  { id: null, label: '🔍 Q&A', title: 'Grounded Q&A from transcripts' },
  { id: 'ship_30_essay', label: '✍️ Essay', title: 'Generate a Ship 30 for 30 essay' },
  { id: 'artifact_markdown', label: '📄 Markdown', title: 'Create a Markdown document' },
  { id: 'artifact_html', label: '🌐 HTML', title: 'Generate an HTML/CSS page' },
]

const SUGGESTIONS = [
  { icon: '🚀', title: 'Growth loops', desc: 'How did Airbnb build compounding growth loops?', q: 'How did Airbnb build compounding growth loops?' },
  { icon: '📊', title: 'North Star metric', desc: 'What makes a good North Star metric?', q: 'What makes a good North Star metric and how should I pick one?' },
  { icon: '✅', title: 'Product-market fit', desc: 'How do you know when you have PMF?', q: 'How do you know when you have found product-market fit? What are the signals?' },
  { icon: '💰', title: 'Pricing strategy', desc: 'Pricing tactics for early-stage startups', q: 'What pricing strategies work best for early-stage B2B SaaS startups?' },
]

export default function ChatInput() {
  const [input, setInput] = useState('')
  const [selectedSkill, setSelectedSkill] = useState(null)
  const textareaRef = useRef(null)
  const { sendMessage, isLoading, isStreaming, activeSessionId, createSession } = useStore()

  // Auto-grow textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (ta) {
      ta.style.height = 'auto'
      ta.style.height = Math.min(ta.scrollHeight, 200) + 'px'
    }
  }, [input])

  const handleSend = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading || isStreaming) return

    let sessionId = activeSessionId
    if (!sessionId) {
      const session = await createSession(trimmed.slice(0, 50))
      sessionId = session.id
    }

    setInput('')
    await sendMessage(trimmed, selectedSkill)
  }, [input, isLoading, isStreaming, activeSessionId, selectedSkill, sendMessage, createSession])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSuggestion = async (q) => {
    setInput(q)
    textareaRef.current?.focus()
  }

  return (
    <div className="input-area">
      <div className="input-container">
        {/* Skill selector */}
        <div className="skill-selector">
          {SKILLS.map(skill => (
            <button
              key={skill.id || 'default'}
              className={`skill-btn ${selectedSkill === skill.id ? 'active' : ''}`}
              onClick={() => setSelectedSkill(selectedSkill === skill.id ? null : skill.id)}
              title={skill.title}
            >
              {skill.label}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="input-box">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedSkill === 'ship_30_essay'
                ? 'What topic should the essay cover?'
                : selectedSkill === 'artifact_html'
                ? 'Describe the HTML page to generate...'
                : selectedSkill === 'artifact_markdown'
                ? 'What document should I create?'
                : 'Ask anything about product, growth, or strategy...'
            }
            rows={1}
            disabled={isLoading || isStreaming}
          />
          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!input.trim() || isLoading || isStreaming}
            aria-label="Send message"
          >
            {isLoading || isStreaming ? (
              <span style={{ width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.8s linear infinite' }} />
            ) : (
              <Send size={14} />
            )}
          </button>
        </div>

        <p className="input-hint">
          Enter to send · Shift+Enter for new line · Powered by {useStore.getState().modelConfig?.current_model || 'local Ollama'}
        </p>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

export { SUGGESTIONS }
