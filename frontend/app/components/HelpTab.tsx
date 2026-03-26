"use client"
import { BookOpen, Zap, Search, ShieldCheck, GitBranch, DollarSign } from "lucide-react"

const FEATURES = [
  {
    icon: Search,
    title: "Multi-Source Retrieval",
    color: "#3b82f6",
    desc: "Searches three independent sources - a curated Vector DB of ~900 timber articles, MediaStack news API with 12 German keywords, and Tavily specialist web search - then deduplicates and merges all results.",
  },
  {
    icon: GitBranch,
    title: "ReAct Research Loop",
    color: "#4ade80",
    desc: "The Researcher agent uses a Reasoning + Acting loop to decide which tools to call and in what order, adapting its strategy based on what each source returns. Up to 6 steps per query.",
  },
  {
    icon: ShieldCheck,
    title: "LLM-Based Verification",
    color: "#a855f7",
    desc: "A dedicated FactVerifier (gpt-4o) reads every retrieved article in full and selects only those genuinely relevant to the question - with a written reason for each selection.",
  },
  {
    icon: Zap,
    title: "Baseline vs. Agentic",
    color: "#f59e0b",
    desc: "Baseline RAG is a fast single-source mode (~3 s, ~$0.0001) using only the local Vector DB. Agentic mode runs the full multi-source pipeline (~30 s, ~$0.03). Compare them side-by-side in the A/B Test tab.",
  },
  {
    icon: DollarSign,
    title: "Cost & Token Tracking",
    color: "#e11d48",
    desc: "Every query logs token counts, per-agent costs, and cumulative session spend visible in the sidebar and Analytics tab - so you always know what a question costs before scaling up.",
  },
  {
    icon: BookOpen,
    title: "Live Reasoning Trace",
    color: "#60a5fa",
    desc: "The Streaming Panel shows each pipeline step in real time - Planner strategy, Researcher tool calls, Ranker decisions, Verifier judgements - giving full transparency into how an answer was built.",
  },
]

export function HelpTab() {
  return (
    <div className="h-full overflow-y-auto p-4 space-y-5">

      {/* ── Hero ── */}
      <div className="card p-5" style={{ borderLeft: "3px solid #4ade80" }}>
        <h1 className="text-lg font-bold mb-2" style={{ color: "#111827" }}>Timber Intel</h1>
        <p className="text-sm leading-relaxed mb-3" style={{ color: "#1f2937" }}>
          A market intelligence platform purpose-built for the <strong>German timber market</strong>, offering
          two query modes: a fast <strong>Baseline RAG</strong> for quick local lookups, and a full
          <strong> Agentic RAG</strong> pipeline for comprehensive, multi-source, verified answers.
          Ask plain-language questions and get answers grounded in real news and industry sources -
          with full transparency into how every answer was produced.
        </p>
        <p className="text-sm leading-relaxed mb-4" style={{ color: "#1f2937" }}>
          The <strong>Baseline RAG</strong> mode queries a local <strong>Vector DB</strong> of ~900 curated timber articles
          using hybrid BM25 + vector search for fast offline retrieval (~3 s). The <strong>Agentic</strong> mode
          goes further - its primary live source is <strong>MediaStack</strong>, a news API queried with 12 targeted
          German timber keywords (Holzpreis, Baukosten, Zölle, etc.), complemented by <strong>Tavily</strong>
          specialist and open-web search for broader coverage. The backend is built with <strong>FastAPI</strong>,
          the frontend with <strong>Next.js</strong>, and the entire stack is containerised with <strong>Docker</strong>.
        </p>
        <div className="flex gap-3 flex-wrap">
          {[
            ["Domain",      "German Timber Market"],
            ["Primary Source", "MediaStack · Tavily"],
            ["Backend",     "FastAPI · Python"],
            ["Frontend",    "Next.js · TypeScript"],
            ["Infra",       "Docker"],
          ].map(([l, v]) => (
            <div key={l} className="text-xs px-2.5 py-1 rounded-md"
              style={{ background: "#1e293b", color: "#e2e8f0" }}>
              <span style={{ color: "#64748b" }}>{l}: </span>
              <span className="font-semibold">{v}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Key Features ── */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-wider mb-3 px-1"
          style={{ color: "#111827" }}>Key Features</h2>
        <div className="grid grid-cols-2 gap-3">
          {FEATURES.map(f => (
            <div key={f.title} className="card p-4">
              <div className="flex items-center gap-2 mb-2">
                <f.icon size={14} style={{ color: f.color }} />
                <span className="text-sm font-semibold" style={{ color: "#111827" }}>{f.title}</span>
              </div>
              <p className="text-sm leading-relaxed" style={{ color: "#374151" }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Quick Tips ── */}
      <div className="card p-4">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-3"
          style={{ color: "#111827" }}>Quick Tips</h2>
        <ul className="space-y-2.5">
          {[
            ["Baseline mode",       "Use for fast, simple lookups from the local Vector DB knowledge base (~3 s, ~$0.0001)."],
            ["Agentic mode",        "Use when you need comprehensive, current, multi-source evidence across MediaStack, Tavily, and the Vector DB (~30 s, ~$0.03)."],
            ["Research mode",       "Turn on to activate the Query Research Log in the Analytics tab to access logs of full queries, responses, and metrics for export and analysis."],
            ["A/B Test tab",        "Run both modes on the same query to see the difference in depth, sources, and cost."],
            ["Export button",       "Download the full answer, sources, cost breakdown, and key facts after any query."],
            ["Follow-up questions", "The pipeline remembers the last conversation turn - ask follow-ups naturally without repeating context."],
          ].map(([label, tip]) => (
            <li key={label as string} className="flex gap-2 text-sm leading-relaxed">
              <span className="font-bold shrink-0" style={{ color: "#111827" }}>{label}:</span>
              <span style={{ color: "#374151" }}>{tip}</span>
            </li>
          ))}
        </ul>
      </div>

    </div>
  )
}
