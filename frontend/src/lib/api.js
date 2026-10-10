/**
 * API client — all backend communication goes through here.
 * Base URL auto-detected (Vite proxy in dev, same-origin in prod).
 */

const BASE_URL = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || err.error || `HTTP ${res.status}`)
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  // Sessions
  createSession: (data) => request('/api/sessions', { method: 'POST', body: JSON.stringify(data) }),
  listSessions: () => request('/api/sessions'),
  deleteSession: (id) => request(`/api/sessions/${id}`, { method: 'DELETE' }),

  // Chat
  sendMessage: (sessionId, data) =>
    request(`/api/sessions/${sessionId}/chat`, { method: 'POST', body: JSON.stringify(data) }),
  getMessages: (sessionId) => request(`/api/sessions/${sessionId}/messages`),

  // Artifacts
  getArtifact: (id) => request(`/api/artifacts/${id}`),

  // System
  health: () => request('/api/health'),
  modelConfig: () => request('/api/model'),
  reindex: () => request('/api/kb/reindex', { method: 'POST' }),
}

/**
 * SSE streaming — returns an async generator of text deltas.
 * @param {string} sessionId
 * @param {object} data - ChatRequest body
 */
export async function* streamMessage(sessionId, data) {
  const url = `${BASE_URL}/api/sessions/${sessionId}/stream`
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })

  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Stream failed: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    const text = decoder.decode(value, { stream: true })
    const lines = text.split('\n')
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const payload = JSON.parse(line.slice(6))
          if (payload.error) throw new Error(payload.error)
          if (payload.done) return payload.content
          if (payload.delta) yield payload.delta
        } catch (e) {
          if (e.message !== 'Unexpected end of JSON input') throw e
        }
      }
    }
  }
}
