import type { Message, QueryCostEntry } from "./types"

const MESSAGES_KEY = "timber_messages"
const COSTS_KEY = "timber_costs"
const CURRENT_SESSION_KEY = "timber_current_session"
const SESSIONS_KEY = "timber_sessions"

export interface ChatSession {
  id: string
  title: string      // first user message, truncated
  createdAt: number
  updatedAt: number
}

// ── Session metadata list ─────────────────────────────────────────────────

export function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem(SESSIONS_KEY) || "[]")
  } catch { return [] }
}

export function saveSessions(sessions: ChatSession[]) {
  if (typeof window === "undefined") return
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions.slice(0, 20)))
}

export function upsertSession(id: string, title: string) {
  const sessions = loadSessions()
  const existing = sessions.find(s => s.id === id)
  if (existing) {
    existing.updatedAt = Date.now()
    if (!existing.title && title) existing.title = title
  } else {
    sessions.unshift({ id, title, createdAt: Date.now(), updatedAt: Date.now() })
  }
  saveSessions(sessions.sort((a, b) => b.updatedAt - a.updatedAt))
}

// ── Session ID management ──────────────────────────────────────────────────

export function getCurrentSessionId(): string {
  if (typeof window === "undefined") return "default"
  let id = localStorage.getItem(CURRENT_SESSION_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(CURRENT_SESSION_KEY, id)
  }
  return id
}

export function setCurrentSessionId(id: string) {
  if (typeof window === "undefined") return
  localStorage.setItem(CURRENT_SESSION_KEY, id)
}

// ── Session-scoped message storage ────────────────────────────────────────

export function loadSessionMessages(sessionId: string): Message[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem(`${MESSAGES_KEY}_${sessionId}`) || "[]")
  } catch { return [] }
}

export function saveSessionMessages(sessionId: string, messages: Message[]) {
  if (typeof window === "undefined") return
  localStorage.setItem(`${MESSAGES_KEY}_${sessionId}`, JSON.stringify(messages.slice(-100)))
}

export function clearChat(sessionId: string) {
  if (typeof window === "undefined") return
  localStorage.removeItem(`${MESSAGES_KEY}_${sessionId}`)
}

// ── Cost storage (global — never cleared by New Chat) ─────────────────────

export function loadCosts(): QueryCostEntry[] {
  if (typeof window === "undefined") return []
  try {
    return JSON.parse(localStorage.getItem(COSTS_KEY) || "[]")
  } catch { return [] }
}

export function saveCosts(costs: QueryCostEntry[]) {
  if (typeof window === "undefined") return
  localStorage.setItem(COSTS_KEY, JSON.stringify(costs))
}

// ── Legacy helpers (kept for any external callers) ────────────────────────

export function loadMessages(): Message[] {
  return loadSessionMessages(getCurrentSessionId())
}

export function saveMessages(messages: Message[]) {
  saveSessionMessages(getCurrentSessionId(), messages)
}

// ── Wipe everything (Clear All Data button) ───────────────────────────────

export function clearAll() {
  if (typeof window === "undefined") return
  localStorage.removeItem(COSTS_KEY)
  localStorage.removeItem(CURRENT_SESSION_KEY)
  localStorage.removeItem(SESSIONS_KEY)
  // Remove all session message keys
  const keysToRemove: string[] = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key && key.startsWith(MESSAGES_KEY)) keysToRemove.push(key)
  }
  keysToRemove.forEach(k => localStorage.removeItem(k))
}
