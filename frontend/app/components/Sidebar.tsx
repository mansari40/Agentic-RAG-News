"use client"
import { useState, useEffect } from "react"
import { Activity, Trash2, RefreshCw, Database, ChevronRight, ChevronLeft, Plus, MessageSquare, X } from "lucide-react"
import { getHealth, clearMemory } from "../lib/api"
import { loadCosts, loadSessions, deleteSession, clearAll } from "../lib/storage"
import type { ChatSession } from "../lib/storage"
import type { QueryCostEntry } from "../lib/types"

const TOOL_OPTIONS = [
  { key: "search_tavily_specialist", label: "Tavily Specialist" },
  { key: "search_mediastack",        label: "MediaStack" },
  { key: "search_tavily_web",        label: "Tavily Web" },
  { key: "search_baseline",          label: "Baseline DB" },
]
const ALL_TOOL_KEYS = TOOL_OPTIONS.map(t => t.key)

interface Props {
  mode: "baseline" | "agentic"
  setMode: (m: "baseline" | "agentic") => void
  onQuickQuery: (q: string) => void
  onNewChat: () => void
  onSwitchSession: (id: string) => void
  researchMode: boolean
  setResearchMode: (v: boolean) => void
  allowedTools: string[]
  setAllowedTools: (tools: string[]) => void
  dateFrom: string
  setDateFrom: (d: string) => void
  dateTo: string
  setDateTo: (d: string) => void
  sessionId: string
}

export function Sidebar({ mode, setMode, onQuickQuery, onNewChat, onSwitchSession, researchMode, setResearchMode, allowedTools, setAllowedTools, dateFrom, setDateFrom, dateTo, setDateTo, sessionId }: Props) {
  const [health, setHealth] = useState<{ version?: string; pipelines?: Record<string, string> } | null>(null)
  const [costs, setCosts] = useState<QueryCostEntry[]>([])
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [clearing, setClearing] = useState(false)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    getHealth().then(setHealth)
    const interval = setInterval(() => getHealth().then(setHealth), 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const refresh = () => {
      setCosts(loadCosts())
      setSessions(loadSessions())
    }
    refresh()
    const interval = setInterval(refresh, 2000)
    return () => clearInterval(interval)
  }, [sessionId])

  const sessionCost = costs.reduce((s, c) => s + c.cost_usd, 0)
  const sessionTokens = costs.reduce((s, c) => s + c.total_tokens, 0)

  const handleClearMemory = async () => {
    setClearing(true)
    await clearMemory()
    setTimeout(() => setClearing(false), 1000)
  }

  return (
    <aside className={`flex flex-col h-full border-r border-border bg-surface text-text transition-all duration-300 overflow-hidden ${collapsed ? "w-12" : "w-64"}`}>
      {/* Logo */}
      <div className="py-4 border-b border-border shrink-0">
        {collapsed ? (
          <div className="flex justify-center">
            <button
              onClick={() => setCollapsed(false)}
              className="w-7 h-7 flex items-center justify-center rounded-md text-text-3 hover:text-text hover:bg-surface-2 transition-colors"
              title="Expand sidebar"
            >
              <ChevronRight size={15} />
            </button>
          </div>
        ) : (
          <div className="px-3 flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center text-sm shrink-0"
              style={{ background: "linear-gradient(135deg, rgba(15, 118, 110, 0.95), rgba(4, 79, 80, 0.95))", border: "1px solid #0f766e" }}>
              🌲
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-text leading-none">Timber Intel</p>
              <p className="text-xs text-text-3 leading-none mt-0.5">German Market AI</p>
            </div>
            <button
              onClick={() => setCollapsed(true)}
              className="shrink-0 w-6 h-6 flex items-center justify-center rounded-md text-text-3 hover:text-text hover:bg-surface-2 transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft size={14} />
            </button>
          </div>
        )}
      </div>

      {!collapsed && (
        <>
          {/*Scrollable middle*/}
          <div className="flex-1 overflow-y-auto min-h-0">

          {/* API Status */}
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${health ? "bg-accent" : "bg-red"}`}
                style={{ boxShadow: health ? "0 0 6px #4ade80" : "0 0 6px #f87171" }} />
              <span className="text-xs font-semibold text-text">
                {health ? "API online" : "API offline"}
              </span>
              {health?.pipelines && (
                <span className="text-xs font-semibold text-emerald-700 ml-auto">
                  {Object.values(health.pipelines).every(v => v === "ready") ? "All ready" : "Partial"}
                </span>
              )}
            </div>
          </div>

          {/* New Chat button */}
          <div className="px-3 py-2.5 border-b border-border">
            <button
              onClick={onNewChat}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200"
              style={{ background: "linear-gradient(135deg, rgba(15,118,110,0.12), rgba(4,79,80,0.08))", border: "1px solid #0f766e", color: "#0f766e" }}
            >
              <Plus size={13} />
              New Chat
            </button>
          </div>

          {/* Mode selector */}
          <div className="px-4 py-3 border-b border-border space-y-2">
            <p className="text-xs font-semibold text-text uppercase tracking-wider">RAG Mode</p>
            {(["baseline", "agentic"] as const).map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-2 ${
                  mode === m
                    ? "bg-surface-2 border border-border-2 text-text"
                    : "text-text-3 hover:text-text-2 hover:bg-surface"
                }`}
              >
                {m === "baseline" ? <Database size={13} /> : <Activity size={13} className="text-accent" />}
                <div>
                  <div className="text-text font-semibold">{m === "baseline" ? "Baseline RAG" : "Agentic RAG"}</div>
                  <div className="text-text-2 font-medium">
                  </div>
                </div>
                {mode === m && <ChevronRight size={15} className="ml-auto text-accent" />}
              </button>
            ))}
          </div>

          {/* Tool selector — agentic only */}
          {mode === "agentic" && (
            <div className="px-4 py-3 border-b border-border space-y-2">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold text-text uppercase tracking-wider">Tools</p>
                <button
                  onClick={() =>
                    setAllowedTools(
                      allowedTools.length === ALL_TOOL_KEYS.length ? [] : [...ALL_TOOL_KEYS]
                    )
                  }
                  className="text-xs text-accent hover:underline"
                >
                  {allowedTools.length === ALL_TOOL_KEYS.length ? "None" : "All"}
                </button>
              </div>
              {TOOL_OPTIONS.map(({ key, label }) => {
                const checked = allowedTools.includes(key)
                return (
                  <label key={key} className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() =>
                        setAllowedTools(
                          checked
                            ? allowedTools.filter(k => k !== key)
                            : [...allowedTools, key]
                        )
                      }
                      className="w-3.5 h-3.5 rounded accent-teal-600"
                    />
                    <span className={`text-xs ${checked ? "text-text font-medium" : "text-text-3"} group-hover:text-text-2 transition-colors`}>
                      {label}
                    </span>
                  </label>
                )
              })}
            </div>
          )}

          {/* Date range — both modes */}
          <div className="px-4 py-3 border-b border-border space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-text uppercase tracking-wider">Date Range</p>
              <button
                onClick={() => { setDateFrom("2026-01-01"); setDateTo(new Date().toISOString().split("T")[0]) }}
                className="text-xs text-text-3 hover:text-text-2 hover:underline"
              >
                Reset
              </button>
            </div>
            <div className="space-y-1.5">
              <div>
                <p className="text-xs text-text-3 mb-0.5">From</p>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  className="w-full text-xs px-2 py-1.5 rounded-lg border border-border bg-surface-2 text-text focus:outline-none focus:border-border-2"
                />
              </div>
              <div>
                <p className="text-xs text-text-3 mb-0.5">To</p>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  className="w-full text-xs px-2 py-1.5 rounded-lg border border-border bg-surface-2 text-text focus:outline-none focus:border-border-2"
                />
              </div>
            </div>
          </div>

          {/* Session cost */}
          {sessionCost > 0 && (
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs font-semibold text-text uppercase tracking-wider mb-2">Session Cost</p>
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-text font-medium">Total cost</span>
                  <span className="font-mono font-semibold text-amber">${sessionCost.toFixed(5)}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text font-medium">Tokens</span>
                  <span className="font-mono font-semibold text-blue">{sessionTokens.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-text font-medium">Queries</span>
                  <span className="font-mono font-semibold text-accent">{costs.length}</span>
                </div>
              </div>
            </div>
          )}

          {/* Recent chats */}
          {sessions.length > 0 && (
            <div className="px-4 py-3 border-b border-border">
              <p className="text-xs font-semibold text-text uppercase tracking-wider mb-2">Recent Chats</p>
              <div className="space-y-1">
                {sessions.slice(0, 8).map(s => (
                  <div
                    key={s.id}
                    className={`group flex items-center gap-1.5 rounded-lg px-2 py-1.5 transition-colors ${
                      s.id === sessionId
                        ? "bg-surface-2 text-text font-medium border border-border"
                        : "text-text-3 hover:text-text-2 hover:bg-surface"
                    }`}
                  >
                    <MessageSquare size={10} className="shrink-0 opacity-60" />
                    <button
                      onClick={() => onSwitchSession(s.id)}
                      className="flex-1 text-left text-xs truncate"
                    >
                      {s.title || "New Chat"}
                    </button>
                    <button
                      onClick={() => { deleteSession(s.id); setSessions(prev => prev.filter(x => x.id !== s.id)) }}
                      className="shrink-0 opacity-0 group-hover:opacity-100 text-text-3 hover:text-red transition-all"
                    >
                      <X size={11} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          </div>{/*end scrollable middle*/}

          {/* Controls at bottom — pinned */}
          <div className="px-4 py-3 border-t border-border shrink-0 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-3">Research Mode</span>
              <button
                onClick={() => setResearchMode(!researchMode)}
                className={`w-10 h-5 rounded-full transition-all duration-200 relative ${researchMode ? "bg-accent-dim" : "bg-surface-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full transition-all duration-200 ${researchMode ? "left-5 bg-accent" : "left-0.5 bg-text-3"}`} />
              </button>
            </div>

            <button
              onClick={handleClearMemory}
              disabled={clearing}
              className="btn-ghost w-full text-xs flex items-center gap-2"
            >
              <RefreshCw size={11} className={clearing ? "animate-spin" : ""} />
              {clearing ? "Clearing…" : "Clear Agent Memory"}
            </button>

            <button
              onClick={() => { clearAll(); setCosts([]); setSessions([]) }}
              className="btn-ghost w-full text-xs flex items-center gap-2 text-red-400 hover:text-red"
            >
              <Trash2 size={11} />
              Clear All Data
            </button>
          </div>
        </>
      )}

      {/* Collapsed: API status dot */}
      {collapsed && (
        <div className="flex justify-center pt-3">
          <div className={`w-2 h-2 rounded-full ${health ? "bg-accent" : "bg-red"}`}
            style={{ boxShadow: health ? "0 0 6px #4ade80" : "0 0 6px #f87171" }} />
        </div>
      )}
    </aside>
  )
}
