"use client"
import { useState, useCallback, useEffect } from "react"
import { MessageSquare, FlaskConical, TrendingUp, HelpCircle, GitBranch } from "lucide-react"
import { Sidebar } from "./components/Sidebar"
import { ChatTab } from "./components/ChatTab"
import { ABTestTab } from "./components/ABTestTab"
import { AnalyticsTab } from "./components/AnalyticsTab"
import { HelpTab } from "./components/HelpTab"
import { ArchitectureTab } from "./components/ArchitectureTab"
import { clearMemory } from "./lib/api"
import { getCurrentSessionId, setCurrentSessionId } from "./lib/storage"

const TABS = [
  { id: "chat",         label: "Chat",         icon: MessageSquare },
  { id: "ab",           label: "A/B Test",     icon: FlaskConical },
  { id: "analytics",    label: "Analytics",    icon: TrendingUp },
  { id: "architecture", label: "Architecture", icon: GitBranch },
  { id: "help",         label: "Overview",     icon: HelpCircle },
] as const

type TabId = typeof TABS[number]["id"]

const ALL_TOOLS = ["search_tavily_specialist", "search_mediastack", "search_tavily_web", "search_baseline"]
const TODAY = new Date().toISOString().split("T")[0]

export default function Home() {
  const [tab, setTab] = useState<TabId>("chat")
  const [mode, setMode] = useState<"baseline" | "agentic">("agentic")
  const [researchMode, setResearchMode] = useState(false)
  const [pendingQuery, setPendingQuery] = useState<string | null>(null)
  const [allowedTools, setAllowedTools] = useState<string[]>(ALL_TOOLS)
  const [dateFrom, setDateFrom] = useState("2026-01-01")
  const [dateTo, setDateTo] = useState(TODAY)
  const [sessionId, setSessionId] = useState<string>("default")

  // Initialise sessionId from localStorage after hydration
  useEffect(() => {
    setSessionId(getCurrentSessionId())
  }, [])

  const handleNewChat = useCallback(async () => {
    const newId = crypto.randomUUID()
    setCurrentSessionId(newId)
    setSessionId(newId)
    setTab("chat")
    setPendingQuery(null)
    await clearMemory()
  }, [])

  const handleSwitchSession = useCallback((id: string) => {
    setCurrentSessionId(id)
    setSessionId(id)
    setTab("chat")
    setPendingQuery(null)
  }, [])

  const handleQuickQuery = useCallback((q: string) => {
    setTab("chat")
    setPendingQuery(q)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        mode={mode}
        setMode={setMode}
        onQuickQuery={handleQuickQuery}
        onNewChat={handleNewChat}
        onSwitchSession={handleSwitchSession}
        researchMode={researchMode}
        setResearchMode={setResearchMode}
        allowedTools={allowedTools}
        setAllowedTools={setAllowedTools}
        dateFrom={dateFrom}
        setDateFrom={setDateFrom}
        dateTo={dateTo}
        setDateTo={setDateTo}
        sessionId={sessionId}
      />

      {/* Main content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden bg-bg text-text">
        {/* Header */}
        <header className="border-b border-border px-6 py-3 flex items-center justify-end shrink-0 bg-surface">
          {/* Tab bar */}
          <nav className="flex items-center gap-1 p-1 rounded-xl" style={{ background: "#f3f4f6", border: "1px solid #d1d5db" }}>
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setTab(id)}
                className={`tab-btn flex items-center gap-1.5 ${tab === id ? "active" : ""}`}
              >
                <Icon size={13} />
                {label}
              </button>
            ))}
          </nav>
        </header>

        {/* Tab content — always mounted to preserve state across tab switches */}
        <div className="flex-1 overflow-hidden">
          <div className={tab === "chat" ? "h-full" : "hidden"}>
            <ChatTab
              mode={mode}
              key={sessionId}
              initialQuery={pendingQuery}
              onQueryConsumed={() => setPendingQuery(null)}
              allowedTools={allowedTools}
              dateFrom={dateFrom}
              dateTo={dateTo}
              sessionId={sessionId}
            />
          </div>
          <div className={tab === "ab" ? "h-full" : "hidden"}><ABTestTab /></div>
          <div className={tab === "analytics" ? "h-full" : "hidden"}><AnalyticsTab /></div>
          <div className={tab === "architecture" ? "h-full" : "hidden"}><ArchitectureTab /></div>
          <div className={tab === "help" ? "h-full" : "hidden"}><HelpTab /></div>
        </div>
      </main>
    </div>
  )
}
