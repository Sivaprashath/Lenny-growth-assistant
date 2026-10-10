/**
 * Global state store using Zustand.
 * Manages sessions, messages, active artifact, loading states, and model info.
 */
import { create } from 'zustand'
import { api, streamMessage } from '../lib/api'

const useStore = create((set, get) => ({
  // Sessions
  sessions: [],
  activeSessionId: null,

  // Messages per session
  messages: {},

  // Active artifact shown in the panel
  activeArtifact: null,

  // UI state
  isLoading: false,
  isStreaming: false,
  streamingContent: '',
  error: null,

  // Model info
  modelConfig: null,

  // Toast notifications
  toasts: [],

  // ── Toast helpers ────────────────────────────────────────────────────────

  addToast: (message, type = 'info') => {
    const id = Date.now()
    set(s => ({ toasts: [...s.toasts, { id, message, type }] }))
    setTimeout(() => {
      set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
    }, 4000)
  },

  // ── Sessions ─────────────────────────────────────────────────────────────

  loadSessions: async () => {
    try {
      const data = await api.listSessions()
      set({ sessions: data.sessions })
    } catch (e) {
      console.warn('Failed to load sessions:', e.message)
    }
  },

  createSession: async (title) => {
    const session = await api.createSession({ title })
    set(s => ({ sessions: [session, ...s.sessions], activeSessionId: session.id, messages: { ...s.messages, [session.id]: [] } }))
    return session
  },

  setActiveSession: async (sessionId) => {
    set({ activeSessionId: sessionId, activeArtifact: null })
    // Load messages if not cached
    const { messages } = get()
    if (!messages[sessionId]) {
      try {
        const msgs = await api.getMessages(sessionId)
        set(s => ({ messages: { ...s.messages, [sessionId]: msgs } }))
      } catch (e) {
        console.error('Failed to load messages:', e)
      }
    }
  },

  deleteSession: async (sessionId) => {
    await api.deleteSession(sessionId)
    set(s => {
      const newSessions = s.sessions.filter(ses => ses.id !== sessionId)
      const newMessages = { ...s.messages }
      delete newMessages[sessionId]
      return {
        sessions: newSessions,
        activeSessionId: s.activeSessionId === sessionId
          ? (newSessions[0]?.id || null)
          : s.activeSessionId,
        messages: newMessages,
      }
    })
    get().addToast('Session deleted', 'info')
  },

  // ── Messaging ─────────────────────────────────────────────────────────────

  sendMessage: async (content, skillOverride = null, useStream = false) => {
    const { activeSessionId, addToast } = get()
    if (!activeSessionId || !content.trim()) return

    // Optimistic user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    set(s => ({
      messages: {
        ...s.messages,
        [activeSessionId]: [...(s.messages[activeSessionId] || []), tempUserMsg],
      },
    }))

    if (useStream) {
      set({ isStreaming: true, streamingContent: '' })
      try {
        let fullContent = ''
        for await (const delta of streamMessage(activeSessionId, { message: content, skill_override: skillOverride })) {
          fullContent += delta
          set({ streamingContent: fullContent })
        }
        // Replace streaming with final message
        const aiMsg = {
          id: `stream-${Date.now()}`,
          role: 'assistant',
          content: fullContent,
          skill_used: skillOverride || 'rag_qa',
          created_at: new Date().toISOString(),
        }
        set(s => ({
          messages: {
            ...s.messages,
            [activeSessionId]: [...(s.messages[activeSessionId] || []), aiMsg],
          },
          isStreaming: false,
          streamingContent: '',
        }))
      } catch (e) {
        set({ isStreaming: false, streamingContent: '' })
        addToast(e.message || 'Stream failed', 'error')
      }
    } else {
      set({ isLoading: true })
      try {
        const data = await api.sendMessage(activeSessionId, {
          message: content,
          skill_override: skillOverride,
        })

        // Update messages
        const msgs = await api.getMessages(activeSessionId)
        set(s => ({
          messages: { ...s.messages, [activeSessionId]: msgs },
          isLoading: false,
        }))

        // Show artifact if generated
        if (data.artifact) {
          set({ activeArtifact: data.artifact })
          addToast(`${data.artifact.artifact_type.toUpperCase()} artifact generated`, 'success')
        }

        // Update session in list
        set(s => ({
          sessions: s.sessions.map(ses =>
            ses.id === activeSessionId ? { ...ses, message_count: (ses.message_count || 0) + 2 } : ses
          ),
        }))
      } catch (e) {
        set({ isLoading: false })
        addToast(e.message || 'Failed to send message', 'error')
      }
    }
  },

  // ── Artifacts ─────────────────────────────────────────────────────────────

  setActiveArtifact: (artifact) => set({ activeArtifact: artifact }),
  clearArtifact: () => set({ activeArtifact: null }),

  fetchArtifact: async (id) => {
    try {
      const artifact = await api.getArtifact(id)
      set({ activeArtifact: artifact })
    } catch (e) {
      get().addToast('Failed to load artifact', 'error')
    }
  },

  // ── Model ─────────────────────────────────────────────────────────────────

  loadModelConfig: async () => {
    try {
      const config = await api.modelConfig()
      set({ modelConfig: config })
    } catch (e) {
      console.warn('Could not load model config')
    }
  },
}))

export default useStore
