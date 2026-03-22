"use client"
import { useState, useRef } from "react"
import { Play, Database, Cpu, Clock, Target, DollarSign, BookOpen } from "lucide-react"
import { streamAgentic, queryBaseline } from "../lib/api"
import { loadCosts, saveCosts } from "../lib/storage"
import { SourceCard } from "./SourceCard"
import { StreamingPanel, resolveStep } from "./StreamingPanel"
import type { QueryResult, QueryCostEntry, SSEEvent } from "../lib/types"
import type { LiveStep, LiveReActEvent } from "./StreamingPanel"

function renderAnswer(text: string) {
  return text.split("\n").map((line, li) => {
    if (!line.trim()) return <br key={li} />
    const parts = line.split(/\*\*(.*?)\*\*/g)
    return (
      <p key={li} className="text-sm text-text leading-relaxed">
        {parts.map((p, i) => i % 2 === 1 ? <strong key={i}>{p}</strong> : p)}
      </p>
    )
  })
}

const STEP_CONFIDENCE: Record<string, number> = {
  planned: 0.15, researched: 0.40, ranked: 0.45,
  verified: 0.70, answer_synthesized: 0.85,
}

interface PanelState {
  running: boolean
  result: QueryResult | null
  error: string | null
  steps: LiveStep[]
  react: LiveReActEvent[]
  conf: number
  cost: number
  tokens: number
  elapsed: number
}

const empty = (): PanelState => ({
  running: false, result: null, error: null,
  steps: [], react: [], conf: 0, cost: 0, tokens: 0, elapsed: 0,
})

export function ABTestTab() {
  const [query, setQuery] = useState("")
  const [baseline, setBaseline] = useState<PanelState>(empty())
  const [agentic, setAgentic] = useState<PanelState>(empty())
  const abortRef = useRef<AbortController | null>(null)
  const startRef = useRef<number>(0)

  const run = async () => {
    if (!query.trim()) return
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    const q = query.trim()
    startRef.current = Date.now()

    setBaseline({ ...empty(), running: true })
    setAgentic({ ...empty(), running: true })

    // Run BOTH in parallel simultaneously
    const baselinePromise = (async () => {
      try {
        const r = await queryBaseline(q)
        r.response_time = (Date.now() - startRef.current) / 1000
        r.mode = "baseline"
        setBaseline(prev => ({ ...prev, running: false, result: r, elapsed: r.response_time }))
        const bEntry: QueryCostEntry = {
          query: q.slice(0, 60), cost_usd: r.cost_usd || 0, total_tokens: r.total_tokens || 0,
          llm_calls: r.llm_calls || 1, confidence: r.confidence || 0, query_type: "baseline",
          timestamp: new Date().toLocaleTimeString(), mode: "baseline", response_time: r.response_time,
        }
        saveCosts([...loadCosts(), bEntry])
      } catch (e) {
        setBaseline(prev => ({ ...prev, running: false, error: String(e) }))
      }
    })()

    const agenticPromise = (async () => {
      const shownSteps = new Set<string>()
      try {
        await streamAgentic(q, (ev: SSEEvent) => {
          if (ev.type === "step" && ev.step && !shownSteps.has(ev.step)) {
            shownSteps.add(ev.step)
            const { title, desc } = resolveStep(ev.step)
            setAgentic(prev => ({
              ...prev,
              steps: [...prev.steps.map(s => ({ ...s, done: true })), { id: ev.step!, title, desc, done: false }]
            }))
            for (const [k, v] of Object.entries(STEP_CONFIDENCE)) {
              if (ev.step!.startsWith(k)) setAgentic(prev => ({ ...prev, conf: v }))
            }
          }
          if (ev.type === "action") {
            setAgentic(prev => ({
              ...prev,
              react: [...prev.react, { id: `${Date.now()}-${Math.random()}`, type: "action", tool: ev.tool, text: (ev.args as Record<string, string>)?.query }]
            }))
          }
          if (ev.type === "observation") {
            setAgentic(prev => ({
              ...prev,
              react: [...prev.react, { id: `${Date.now()}-${Math.random()}`, type: "observation", count: ev.count, summary: ev.summary }]
            }))
          }
          if (ev.type === "result" && ev.data) {
            const r = ev.data
            r.mode = "agentic"
            r.response_time = (Date.now() - startRef.current) / 1000
            setAgentic(prev => ({ ...prev, result: r, conf: r.confidence, cost: r.cost_usd, tokens: r.total_tokens, elapsed: r.response_time }))
            const aEntry: QueryCostEntry = {
              query: q.slice(0, 60), cost_usd: r.cost_usd || 0, total_tokens: r.total_tokens || 0,
              llm_calls: r.llm_calls || 0, confidence: r.confidence || 0, query_type: r.query_type || "unknown",
              timestamp: new Date().toLocaleTimeString(), mode: "agentic", response_time: r.response_time,
              sources_collected: r.researcher_scratchpad?.filter((s: { type: string }) => s.type === "observation").reduce((sum: number, s: { count?: number }) => sum + (s.count || 0), 0) || 0,
              sources_verified: r.sources?.length || 0,
              tools_used: r.researcher_scratchpad?.filter((s: { type: string; tool?: string }) => s.type === "action" && s.tool).map((s: { tool?: string }) => s.tool!) || [],
            }
            saveCosts([...loadCosts(), aEntry])
          }
          if (ev.type === "complete") {
            setAgentic(prev => ({ ...prev, running: false, steps: prev.steps.map(s => ({ ...s, done: true })) }))
          }
        }, abortRef.current!.signal)
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setAgentic(prev => ({ ...prev, running: false, error: String(e) }))
        }
      }
    })()

    await Promise.allSettled([baselinePromise, agenticPromise])
  }

  const bothDone = !baseline.running && !agentic.running && (baseline.result || agentic.result)

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="card p-4" style={{ borderLeft: "3px solid #166534" }}>
          <h2 className="text-sm font-semibold text-text mb-1">A/B Comparison — True Parallel Streaming</h2>
          <p className="text-xs text-text-3">Both systems run simultaneously. Watch Baseline return in ~3s while Agentic streams its reasoning trace live.</p>
        </div>

        {/* Query input */}
        <div className="flex gap-2">
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === "Enter" && run()}
            placeholder="Enter a query to compare both systems…"
            className="input-field flex-1"
          />
          <button
            onClick={run}
            disabled={!query.trim() || baseline.running || agentic.running}
            className="btn-primary flex items-center gap-2 px-5 shrink-0"
          >
            <Play size={14} />
            {baseline.running || agentic.running ? "Running…" : "Run A/B Test"}
          </button>
        </div>

        {/* Side-by-side panels */}
        <div className="grid grid-cols-2 gap-4">
          {/* Baseline panel */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Database size={14} className="text-blue" />
              <span className="text-sm font-semibold text-blue">Baseline RAG</span>
              {baseline.elapsed > 0 && (
                <span className="ml-auto text-xs font-mono text-text-3 flex items-center gap-1">
                  <Clock size={10} />{baseline.elapsed.toFixed(2)}s
                </span>
              )}
            </div>
            <div className="card p-3 min-h-32">
              {baseline.running && (
                <div className="flex items-center gap-2 text-xs text-text-3">
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-1.5 h-1.5 rounded-full bg-blue animate-pulse-dot"
                        style={{ animationDelay: `${i * 0.2}s` }} />
                    ))}
                  </div>
                  Searching vector database…
                </div>
              )}
              {baseline.error && <p className="text-xs text-red">{baseline.error}</p>}
              {baseline.result && (
                <div className="space-y-2">
                  <div className="space-y-1">{renderAnswer(baseline.result.answer)}</div>
                  <div className="flex gap-3 text-xs font-mono text-text-3 flex-wrap">
                    <span className="flex items-center gap-1"><Clock size={10} />{baseline.elapsed.toFixed(2)}s</span>
                    <span>{baseline.result.sources.length} sources</span>
                    <span className="flex items-center gap-1"><Target size={10} />{(baseline.result.sources.reduce((a, s) => a + s.score, 0) / Math.max(baseline.result.sources.length, 1)).toFixed(2)} avg</span>
                    <span className="text-accent flex items-center gap-1"><DollarSign size={10} />0.00001</span>
                  </div>
                </div>
              )}
            </div>
            {baseline.result?.sources.length ? (
              <div className="space-y-1.5">
                {baseline.result.sources.slice(0, 3).map((s, i) => <SourceCard key={i} source={s} index={i} />)}
              </div>
            ) : null}
          </div>

          {/* Agentic panel */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Cpu size={14} className="text-accent" />
              <span className="text-sm font-semibold text-accent">Agentic RAG</span>
              {agentic.elapsed > 0 && (
                <span className="ml-auto text-xs font-mono text-text-3 flex items-center gap-1">
                  <Clock size={10} />{agentic.elapsed.toFixed(2)}s
                </span>
              )}
            </div>
            <div className="card p-3 min-h-32">
              {(agentic.running || agentic.steps.length > 0) && (
                <StreamingPanel
                  steps={agentic.steps}
                  react={agentic.react}
                  confidence={agentic.conf}
                  cost={agentic.cost}
                  tokens={agentic.tokens}
                  isRunning={agentic.running}
                />
              )}
              {agentic.error && <p className="text-xs text-red">{agentic.error}</p>}
              {agentic.result && !agentic.running && (
                <div className="space-y-2 mt-2 pt-2 border-t border-border">
                  <div className="space-y-1">{renderAnswer(agentic.result.answer)}</div>
                  <div className="flex gap-3 text-xs font-mono flex-wrap">
                    <span className="text-text-3 flex items-center gap-1"><Clock size={10} />{agentic.elapsed.toFixed(2)}s</span>
                    <span className="text-text-3">{agentic.result.sources.length} sources</span>
                    <span className={agentic.result.confidence >= 0.65 ? "text-accent" : "text-amber"}>
                      {(agentic.result.confidence * 100).toFixed(0)}% conf
                    </span>
                    <span className="text-amber flex items-center gap-1"><DollarSign size={10} />{agentic.result.cost_usd.toFixed(5)}</span>
                    <span className="text-text-3">{agentic.result.llm_calls} LLM calls</span>
                  </div>
                </div>
              )}
            </div>
            {agentic.result?.sources.length ? (
              <div className="space-y-1.5">
                {agentic.result.sources.slice(0, 3).map((s, i) => <SourceCard key={i} source={s} index={i} />)}
              </div>
            ) : null}
          </div>
        </div>

        {/* Comparison table */}
        {bothDone && baseline.result && agentic.result && (
          <div className="card overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-surface-2 border-b border-border">
                  <th className="px-4 py-2.5 text-left text-text-3 font-medium">Metric</th>
                  <th className="px-4 py-2.5 text-left text-blue font-medium">Baseline RAG</th>
                  <th className="px-4 py-2.5 text-left text-accent font-medium">Agentic RAG</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Response Time", `${baseline.elapsed.toFixed(2)}s`, `${agentic.elapsed.toFixed(2)}s`],
                  ["Sources", baseline.result.sources.length.toString(), agentic.result.sources.length.toString()],
                  ["Quality", `${(baseline.result.sources.reduce((a, s) => a + s.score, 0) / Math.max(baseline.result.sources.length, 1)).toFixed(2)} avg score`, `${(agentic.result.confidence * 100).toFixed(0)}% confidence`],
                  ["Answer Length", `${baseline.result.answer.length} chars`, `${agentic.result.answer.length} chars`],
                  ["LLM Calls", "1", agentic.result.llm_calls.toString()],
                  ["Cost", "~$0.00001", `$${agentic.result.cost_usd.toFixed(5)}`],
                  ["Domain Scoped", "No", agentic.result.is_domain_relevant ? "Yes" : "No"],
                ].map(([label, b, a]) => (
                  <tr key={label} className="border-b border-surface-3 hover:bg-surface-2 transition-colors">
                    <td className="px-4 py-2.5 text-text-3">{label}</td>
                    <td className="px-4 py-2.5 font-mono text-text-2">{b}</td>
                    <td className="px-4 py-2.5 font-mono text-text-2">{a}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
