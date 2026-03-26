"use client"
import { useState, useEffect, useMemo } from "react"
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ScatterChart, Scatter, Cell,
  ComposedChart, ReferenceLine, BarChart, Bar,
} from "recharts"
import { loadCosts, loadResearchLog, clearResearchLog } from "../lib/storage"
import type { QueryCostEntry, ResearchLogEntry } from "../lib/types"
import {
  TrendingUp, DollarSign, Zap, Clock, Download, Trash2,
  Activity, Database, Filter, Target, Layers,
} from "lucide-react"

// ── Shared color tokens ────────────────────────────────────────────────────────
const A       = "#0f766e"   // Agentic teal
const B       = "#2563eb"   // Baseline blue
const A_CONF  = "#4ade80"   // Agentic confidence green
const B_CONF  = "#60a5fa"   // Baseline confidence blue
const AMBER   = "#f59e0b"
const PURPLE  = "#7c3aed"
const GRID    = "#e2e8f0"
const AXIS_TICK = { fill: "#64748b", fontSize: 11 }
const TIP_STYLE = { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 8, color: "#0f172a", fontSize: 12 }

// ── Heatmap / scatter color tokens ────────────────────────────────────────────
const QUERY_TYPE_COLORS: Record<string, string> = {
  temporal:   A,
  simple:     B,
  multi_hop:  PURPLE,
  comparison: AMBER,
}
const TYPE_LABELS: Record<string, string> = {
  temporal: "Temporal", simple: "Simple", multi_hop: "Multi-Hop", comparison: "Comparison",
}
const TOOL_LABELS: Record<string, string> = {
  search_tavily_specialist: "Tavily Specialist",
  search_mediastack:        "MediaStack",
  search_tavily_web:        "Tavily Web",
  search_baseline:          "Baseline DB",
}
const ALL_TOOLS = ["search_tavily_specialist", "search_mediastack", "search_tavily_web", "search_baseline"]
const ALL_TYPES = ["temporal", "simple", "multi_hop", "comparison"]

function heatColor(value: number, max: number): string {
  if (value === 0 || max === 0) return "#f1f5f9"
  const t = Math.min(value / max, 1)
  return `rgb(${Math.round(241 - 226 * t)},${Math.round(245 - 127 * t)},${Math.round(249 - 139 * t)})`
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function modeOf(c: QueryCostEntry): "Agentic" | "Baseline" {
  return (c.mode === "agentic" || c.query_type === "agentic") ? "Agentic" : "Baseline"
}
function avg(total: number, count: number, dec = 2): number {
  return count ? Number((total / count).toFixed(dec)) : 0
}
function Chip({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-3 h-3 rounded-sm shrink-0" style={{ background: color }} />
      <span className="text-xs text-text-3">{label}</span>
    </div>
  )
}

// ── Custom scatter tooltip ────────────────────────────────────────────────────
function ScatterTip({ active, payload }: { active?: boolean; payload?: { payload: { query: string; x: number; y: number; query_type: string } }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div style={{ ...TIP_STYLE, padding: "8px 12px", maxWidth: 230 }}>
      <p className="text-xs font-semibold mb-1" style={{ color: QUERY_TYPE_COLORS[d.query_type] ?? "#64748b" }}>
        {TYPE_LABELS[d.query_type] ?? d.query_type}
      </p>
      <p className="text-xs text-slate-400 mb-1 truncate" style={{ maxWidth: 200 }}>{d.query}</p>
      <p className="text-xs">Verified sources: <strong>{d.x}</strong></p>
      <p className="text-xs">Confidence: <strong>{d.y}%</strong></p>
    </div>
  )
}

// ── Custom dual-line tooltip ──────────────────────────────────────────────────
function DualTip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null
  const cost    = payload.find(p => p.name === "Cost ($)")
  const latency = payload.find(p => p.name === "Time (s)")
  const query   = (payload[0] as unknown as { payload: { query: string } })?.payload?.query
  return (
    <div style={{ ...TIP_STYLE, padding: "8px 12px", maxWidth: 220 }}>
      <p className="text-xs font-semibold text-slate-600 mb-1">{label}</p>
      {query && <p className="text-xs text-slate-400 mb-1 truncate" style={{ maxWidth: 190 }}>{query}</p>}
      {cost    && <p className="text-xs">Cost: <strong style={{ color: AMBER }}>${cost.value.toFixed(5)}</strong></p>}
      {latency && <p className="text-xs">Time: <strong style={{ color: A }}>{latency.value}s</strong></p>}
    </div>
  )
}

// ── Colored scatter dot ───────────────────────────────────────────────────────
function ColoredDot({ cx = 0, cy = 0, payload }: { cx?: number; cy?: number; payload?: { query_type: string } }) {
  return <circle cx={cx} cy={cy} r={5} fill={QUERY_TYPE_COLORS[payload?.query_type ?? ""] ?? "#94a3b8"} stroke="#fff" strokeWidth={1.5} opacity={0.85} />
}

// ══════════════════════════════════════════════════════════════════════════════
export function AnalyticsTab({ researchMode }: { researchMode: boolean }) {
  const [costs, setCosts] = useState<QueryCostEntry[]>([])
  const [researchLog, setResearchLog] = useState<ResearchLogEntry[]>([])

  useEffect(() => {
    setCosts(loadCosts())
    setResearchLog(loadResearchLog())
    const interval = setInterval(() => {
      setCosts(loadCosts())
      setResearchLog(loadResearchLog())
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const agenticCosts = useMemo(() => costs.filter(c => modeOf(c) === "Agentic"), [costs])

  // ── All useMemo hooks before any early return (React rules of hooks) ──────
  const pipelineStats = useMemo(() => {
    const withData = agenticCosts.filter(c => c.sources_collected !== undefined)
    if (withData.length === 0) return null
    const n            = withData.length
    const avgCollected = withData.reduce((s, c) => s + (c.sources_collected ?? 0), 0) / n
    const avgVerified  = withData.reduce((s, c) => s + (c.sources_verified  ?? 0), 0) / n
    return { avgCollected, avgVerified, n }
  }, [agenticCosts])

  const funnelStages = useMemo(() => {
    if (!pipelineStats) return []
    const { avgCollected, avgVerified } = pipelineStats
    return [
      { stage: "Retrieved", value: Number(avgCollected.toFixed(1)), pct: 100, fill: "#0ea5e9", note: "Total articles fetched across all tool calls" },
      { stage: "Verified",  value: Number(avgVerified.toFixed(1)),  pct: avgCollected > 0 ? Math.round(avgVerified / avgCollected * 100) : 0, fill: A, note: "Approved by the Fact Verifier LLM" },
    ]
  }, [pipelineStats])

  const heatmap = useMemo(() => {
    const matrix: Record<string, Record<string, number>> = {}
    ALL_TYPES.forEach(t => { matrix[t] = {}; ALL_TOOLS.forEach(tool => { matrix[t][tool] = 0 }) })
    agenticCosts.forEach(c => {
      const qt   = (c.query_type ?? "simple").toLowerCase()
      const type = ALL_TYPES.includes(qt) ? qt : "simple"
      ;(c.tools_used ?? []).forEach(tool => {
        if (ALL_TOOLS.includes(tool)) matrix[type][tool]++
      })
    })
    const maxVal = Math.max(1, ...ALL_TYPES.flatMap(t => ALL_TOOLS.map(tool => matrix[t][tool])))
    return { matrix, maxVal }
  }, [agenticCosts])

  const scatterData = useMemo(() =>
    agenticCosts
      .filter(c => c.sources_verified !== undefined)
      .map(c => ({
        x:          c.sources_verified ?? 0,
        y:          Number((c.confidence * 100).toFixed(1)),
        query_type: c.query_type ?? "simple",
        query:      c.query,
      })),
    [agenticCosts]
  )

  const costLatencyData = useMemo(() =>
    agenticCosts.map((c, i) => ({
      name:    `Q${i + 1}`,
      cost:    Number(c.cost_usd.toFixed(5)),
      latency: Number(c.response_time.toFixed(1)),
      query:   c.query,
    })),
    [agenticCosts]
  )

  if (costs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8 space-y-3">
        <TrendingUp size={32} className="text-text-3" />
        <p className="text-text-2 text-sm">No data yet</p>
        <p className="text-text-3 text-xs">Run some queries to see analytics here</p>
      </div>
    )
  }

  // ── Existing aggregations ─────────────────────────────────────────────────
  const total_cost   = costs.reduce((s, c) => s + c.cost_usd, 0)
  const total_tokens = costs.reduce((s, c) => s + c.total_tokens, 0)

  const grouped = costs.reduce((acc, c) => {
    const m = modeOf(c)
    if (!acc[m]) acc[m] = { count: 0, total_time: 0, total_conf: 0, total_cost: 0, total_tokens: 0, total_calls: 0 }
    acc[m].count        += 1
    acc[m].total_time   += c.response_time
    acc[m].total_conf   += c.confidence * 100
    acc[m].total_cost   += c.cost_usd
    acc[m].total_tokens += c.total_tokens
    acc[m].total_calls  += c.llm_calls
    return acc
  }, {} as Record<string, { count: number; total_time: number; total_conf: number; total_cost: number; total_tokens: number; total_calls: number }>)

  const bS = grouped.Baseline || { count: 0, total_time: 0, total_conf: 0, total_cost: 0, total_tokens: 0, total_calls: 0 }
  const aS = grouped.Agentic  || { count: 0, total_time: 0, total_conf: 0, total_cost: 0, total_tokens: 0, total_calls: 0 }

  const timeline = costs.map((c, i) => ({
    name:          `Q${i + 1}`,
    cost:          Number(c.cost_usd.toFixed(5)),
    cumulative:    Number(costs.slice(0, i + 1).reduce((s, x) => s + x.cost_usd, 0).toFixed(5)),
    tokens:        c.total_tokens,
    confidence:    Number((c.confidence * 100).toFixed(1)),
    llm_calls:     c.llm_calls,
    response_time: Number(c.response_time.toFixed(2)),
    mode:          modeOf(c),
  }))

  const exportCSV = () => {
    const header = "timestamp,query,mode,cost_usd,total_tokens,llm_calls,confidence,response_time"
    const rows = costs.map(c =>
      `${c.timestamp},"${c.query}",${modeOf(c)},${c.cost_usd},${c.total_tokens},${c.llm_calls},${c.confidence},${c.response_time}`
    )
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" })
    const a = document.createElement("a")
    a.href = URL.createObjectURL(blob)
    a.download = `timber_analytics_${Date.now()}.csv`
    a.click()
  }

  const xInterval = Math.max(0, Math.floor(costLatencyData.length / 12) - 1)
  const TM = { top: 8, right: 24, left: 36, bottom: 36 }

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">

      {/* ── Metric cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: "Baseline Queries",  value: bS.count,                              icon: Database,   color: "text-blue" },
          { label: "Agentic Queries",   value: aS.count,                              icon: Activity,   color: "text-accent" },
          { label: "Avg Baseline Time", value: `${avg(bS.total_time, bS.count, 1)}s`, icon: Clock,      color: "text-blue" },
          { label: "Avg Agentic Time",  value: `${avg(aS.total_time, aS.count, 1)}s`, icon: Clock,      color: "text-accent" },
          { label: "Total Cost",        value: `$${total_cost.toFixed(5)}`,           icon: DollarSign, color: "text-amber" },
          { label: "Total Tokens",      value: total_tokens.toLocaleString(),         icon: Zap,        color: "text-blue" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="metric-card">
            <Icon size={14} className={color} />
            <div className={`metric-value ${color}`}>{value}</div>
            <div className="metric-label">{label}</div>
          </div>
        ))}
      </div>

      {/* ── Query-type legend (for new plots) ─────────────────────────────── */}
      <div className="flex items-center gap-5 px-1 flex-wrap">
        {Object.entries(QUERY_TYPE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
            <span className="text-xs text-text-3">{TYPE_LABELS[type]}</span>
          </div>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          NEW SECTION 1 + 2 · Pipeline Funnel & Tool Heatmap
      ══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-2 gap-4">

        {/* Plot 1 · Pipeline Evidence Funnel */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-0.5">
            <Filter size={13} className="text-accent" />
            <h3 className="text-sm font-semibold text-text">Pipeline Evidence Funnel</h3>
          </div>
          <p className="text-xs text-text-3 mb-4">
            Avg sources at each stage · {pipelineStats?.n ?? agenticCosts.length} agentic queries
          </p>
          {funnelStages.length === 0 ? (
            <p className="text-xs text-text-3 text-center py-10">Run agentic queries to populate</p>
          ) : (
            <div className="space-y-5">
              {funnelStages.map((stage, i) => {
                const dropPct = i > 0 && funnelStages[0].value > 0
                  ? Math.round((funnelStages[0].value - stage.value) / funnelStages[0].value * 100)
                  : null
                return (
                  <div key={stage.stage}>
                    <div className="flex justify-between items-end mb-1.5">
                      <div>
                        <span className="text-xs font-semibold text-text">{stage.stage}</span>
                        <p className="text-xs text-text-3 mt-0.5">{stage.note}</p>
                      </div>
                      <div className="flex items-center gap-3 shrink-0 ml-4">
                        {dropPct !== null && <span className="text-xs font-medium text-red-400">↓ {dropPct}% filtered</span>}
                        <span className="text-sm font-bold font-mono" style={{ color: stage.fill }}>avg {stage.value}</span>
                      </div>
                    </div>
                    <div className="relative w-full h-8 bg-surface-2 rounded-lg overflow-hidden border border-border">
                      <div
                        className="absolute left-0 top-0 h-full rounded-lg flex items-center justify-end pr-3 transition-all duration-700"
                        style={{ width: `${Math.max(stage.pct, 2)}%`, background: stage.fill }}
                      >
                        <span className="text-xs font-bold text-white drop-shadow">{stage.pct}%</span>
                      </div>
                    </div>
                  </div>
                )
              })}
              {pipelineStats && pipelineStats.avgCollected > 0 && (
                <div className="pt-3 border-t border-border flex justify-between items-center">
                  <span className="text-xs text-text-3">Verification pass rate</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-1.5 bg-surface-2 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${Math.round(pipelineStats.avgVerified / pipelineStats.avgCollected * 100)}%`, background: A }} />
                    </div>
                    <span className="text-xs font-semibold text-accent">
                      {Math.round(pipelineStats.avgVerified / pipelineStats.avgCollected * 100)}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Plot 2 · Tool Usage Heatmap */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-0.5">
            <Layers size={13} className="text-accent" />
            <h3 className="text-sm font-semibold text-text">Tool Usage by Query Type</h3>
          </div>
          <p className="text-xs text-text-3 mb-4">Call frequency — darker = more calls · hover for details</p>
          <table className="w-full border-separate" style={{ borderSpacing: "4px" }}>
            <thead>
              <tr>
                <th className="text-left pb-1" style={{ width: "90px" }} />
                {ALL_TOOLS.map(tool => (
                  <th key={tool} className="text-center pb-1">
                    {TOOL_LABELS[tool].split(" ").map((word, i) => (
                      <div key={i} className="text-xs text-text-3 font-medium leading-tight">{word}</div>
                    ))}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ALL_TYPES.map(qt => (
                <tr key={qt}>
                  <td className="pr-2 py-0.5">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ background: QUERY_TYPE_COLORS[qt] }} />
                      <span className="text-xs font-medium text-text-2 whitespace-nowrap">{TYPE_LABELS[qt]}</span>
                    </div>
                  </td>
                  {ALL_TOOLS.map(tool => {
                    const val = heatmap.matrix[qt]?.[tool] ?? 0
                    const bg  = heatColor(val, heatmap.maxVal)
                    const textCol = val / heatmap.maxVal > 0.5 ? "#ffffff" : "#0f172a"
                    return (
                      <td key={tool} className="text-center">
                        <div
                          className="rounded-lg h-10 flex items-center justify-center text-xs font-bold transition-transform duration-150 hover:scale-110 cursor-default select-none"
                          style={{ background: bg, color: textCol }}
                          title={`${TYPE_LABELS[qt]} × ${TOOL_LABELS[tool]}: ${val} call${val !== 1 ? "s" : ""}`}
                        >
                          {val}
                        </div>
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center gap-2 mt-4">
            <span className="text-xs text-text-3">0 calls</span>
            <div className="flex-1 h-2 rounded-full" style={{ background: "linear-gradient(to right, #f1f5f9, #0f766e)" }} />
            <span className="text-xs text-text-3">max ({heatmap.maxVal})</span>
          </div>
        </div>
      </div>

      {/* Plot 3 · Confidence vs Verified Sources  +  Plot 4 · Cost & Latency */}
      <div className="grid grid-cols-2 gap-4">

        {/* Plot 3 */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-0.5">
            <Target size={13} className="text-accent" />
            <h3 className="text-sm font-semibold text-text">Confidence vs Verified Sources</h3>
          </div>
          <p className="text-xs text-text-3 mb-1">Each dot = one agentic query · coloured by query type</p>
          <ResponsiveContainer width="100%" height={240}>
            <ScatterChart margin={{ top: 16, right: 24, left: 36, bottom: 44 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis type="number" dataKey="x" name="Verified Sources" tick={AXIS_TICK} allowDecimals={false}
                label={{ value: "Verified Sources (#)", position: "insideBottom", offset: -30, fill: "#64748b", fontSize: 11 }} />
              <YAxis type="number" dataKey="y" name="Confidence" domain={[0, 100]} tick={AXIS_TICK}
                label={{ value: "Confidence (%)", angle: -90, position: "insideLeft", offset: -16, fill: "#64748b", fontSize: 11 }} />
              <ReferenceLine y={70} yAxisId={0} stroke={AMBER} strokeDasharray="5 4" strokeWidth={1.5}
                label={{ value: "70% target", position: "insideTopRight", fill: AMBER, fontSize: 10 }} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }}
                content={(props) => <ScatterTip active={props.active} payload={props.payload as Parameters<typeof ScatterTip>[0]["payload"]} />} />
              <Scatter data={scatterData} shape={(props: { cx?: number; cy?: number; payload?: { query_type: string } }) => <ColoredDot {...props} />} name="queries" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Plot 4 */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-0.5">
            <Activity size={13} className="text-accent" />
            <h3 className="text-sm font-semibold text-text">Cost &amp; Latency Over Agentic Queries</h3>
          </div>
          <div className="flex items-center gap-4 mb-1">
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 rounded" style={{ background: AMBER }} />
              <span className="text-xs text-text-3">Cost $ (left)</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-8 h-0.5 rounded" style={{ background: A }} />
              <span className="text-xs text-text-3">Response time s (right)</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <ComposedChart data={costLatencyData} margin={{ top: 16, right: 52, left: 44, bottom: 44 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis dataKey="name" tick={AXIS_TICK} interval={xInterval}
                label={{ value: "Query #", position: "insideBottom", offset: -30, fill: "#64748b", fontSize: 11 }} />
              <YAxis yAxisId="cost" tick={AXIS_TICK}
                label={{ value: "Cost ($)", angle: -90, position: "insideLeft", offset: -24, fill: "#64748b", fontSize: 11 }} />
              <YAxis yAxisId="latency" orientation="right" tick={AXIS_TICK}
                label={{ value: "Time (s)", angle: 90, position: "insideRight", offset: -28, fill: "#64748b", fontSize: 11 }} />
              <Tooltip content={(props) => <DualTip active={props.active} payload={props.payload as Parameters<typeof DualTip>[0]["payload"]} label={props.label as string} />} />
              <Line yAxisId="cost"    type="monotone" dataKey="cost"    name="Cost ($)" stroke={AMBER} strokeWidth={2} dot={{ r: 3.5, fill: AMBER, stroke: "#fff", strokeWidth: 1.5 }} activeDot={{ r: 5.5 }} />
              <Line yAxisId="latency" type="monotone" dataKey="latency" name="Time (s)" stroke={A}     strokeWidth={2} dot={{ r: 3.5, fill: A,     stroke: "#fff", strokeWidth: 1.5 }} activeDot={{ r: 5.5 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          EXISTING SECTIONS — unchanged below this line
      ══════════════════════════════════════════════════════════════════ */}

      {/* Section 3 · Timeline: Cost per query + Cumulative */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-text mb-1">Cost Per Query &amp; Cumulative</h3>
        <p className="text-xs text-text-3 mb-3">Blue bars = Baseline · Amber bars = Agentic · Green line = cumulative total</p>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={timeline} margin={TM}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
            <XAxis dataKey="name" tick={AXIS_TICK}
              label={{ value: "Query #", position: "insideBottom", offset: -24, fill: "#64748b", fontSize: 11 }} />
            <YAxis tick={AXIS_TICK}
              label={{ value: "Cost ($)", angle: -90, position: "insideLeft", offset: -18, fill: "#64748b", fontSize: 11 }} />
            <Tooltip contentStyle={TIP_STYLE}
              formatter={(v, name) => [
                name === "cost" ? `$${Number(v).toFixed(5)}` : `$${Number(v).toFixed(5)}`,
                name === "cost" ? "Query Cost" : "Cumulative"
              ]} />
            <Bar dataKey="cost" name="cost" radius={[3, 3, 0, 0]}>
              {timeline.map((d, i) => <Cell key={i} fill={d.mode === "Agentic" ? AMBER : B_CONF} />)}
            </Bar>
            <Line type="monotone" dataKey="cumulative" stroke={A_CONF} dot={false} strokeWidth={2} name="cumulative" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Section 4 · Confidence & Response Time per query */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card p-4">
          <h3 className="text-sm font-semibold text-text mb-3">Confidence per Query</h3>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={timeline} margin={TM}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis dataKey="name" tick={AXIS_TICK}
                label={{ value: "Query #", position: "insideBottom", offset: -24, fill: "#64748b", fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={AXIS_TICK}
                label={{ value: "Confidence %", angle: -90, position: "insideLeft", offset: -18, fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={TIP_STYLE} formatter={(v) => [`${v}%`, "Confidence"]} />
              <Line type="monotone" dataKey="confidence" stroke={A_CONF}
                dot={{ fill: A_CONF, r: 4, strokeWidth: 0 }} strokeWidth={2} name="Confidence" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <h3 className="text-sm font-semibold text-text mb-3">Response Time per Query</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={timeline} margin={TM}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="name" tick={AXIS_TICK}
                label={{ value: "Query #", position: "insideBottom", offset: -24, fill: "#64748b", fontSize: 11 }} />
              <YAxis tick={AXIS_TICK}
                label={{ value: "Seconds", angle: -90, position: "insideLeft", offset: -18, fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={TIP_STYLE} formatter={(v) => [`${v}s`, "Response Time"]} />
              <Bar dataKey="response_time" radius={[3, 3, 0, 0]} name="Response Time">
                {timeline.map((d, i) => <Cell key={i} fill={d.mode === "Agentic" ? A : B} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Section 5 · Cost vs Confidence scatter (Agentic only) */}
      <div className="card p-4">
        <h3 className="text-sm font-semibold text-text mb-1">Cost vs Confidence — Agentic RAG</h3>
        <p className="text-xs text-text-3 mb-3">Each dot is one agentic query · Baseline excluded (no confidence score)</p>
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart margin={{ top: 8, right: 24, left: 36, bottom: 36 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
            <XAxis dataKey="cost" name="Cost ($)" tick={AXIS_TICK}
              label={{ value: "Cost ($)", position: "insideBottom", offset: -24, fill: "#64748b", fontSize: 11 }} />
            <YAxis dataKey="confidence" name="Confidence %" domain={[0, 100]} tick={AXIS_TICK}
              label={{ value: "Confidence %", angle: -90, position: "insideLeft", offset: -18, fill: "#64748b", fontSize: 11 }} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={TIP_STYLE}
              formatter={(v, name) => [
                name === "Cost ($)" ? `$${Number(v).toFixed(5)}` : `${v}%`,
                name
              ]} />
            <Scatter data={timeline.filter(d => d.mode === "Agentic")} fill={A} name="Agentic" />
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-5 mt-2 justify-center">
          <Chip color={A} label="Agentic" />
        </div>
      </div>


      {/* ── Research Log — visible only when Research Mode is ON ── */}
      {researchMode && (
        <div className="card overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div>
              <h3 className="text-sm font-semibold text-text">Query Research Log</h3>
              <p className="text-xs text-text-3 mt-0.5">Detailed log captured while Research Mode is ON</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => {
                  const header = "Date,Time,Query,Response,Mode,Cost ($),Tokens,LLM Calls,Confidence / Avg Similarity,Resp. Time (s)"
                  const rows = researchLog.map(r =>
                    [
                      r.date,
                      r.time,
                      `"${r.query.replace(/"/g, '""')}"`,
                      `"${r.response.replace(/"/g, '""')}"`,
                      r.mode,
                      r.cost_usd.toFixed(6),
                      r.total_tokens,
                      r.llm_calls,
                      r.confidence !== null ? (r.confidence * 100).toFixed(1) + "%" : r.avg_similarity?.toFixed(3) ?? "N/A",
                      r.response_time.toFixed(2),
                    ].join(",")
                  )
                  const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv" })
                  const a = document.createElement("a")
                  a.href = URL.createObjectURL(blob)
                  a.download = `timber_research_log_${Date.now()}.csv`
                  a.click()
                }}
                className="btn-ghost text-xs flex items-center gap-1"
              >
                <Download size={11} /> Export CSV
              </button>
              <button
                onClick={() => { clearResearchLog(); setResearchLog([]) }}
                className="btn-ghost text-xs flex items-center gap-1 text-red-400"
              >
                <Trash2 size={11} /> Clear
              </button>
            </div>
          </div>

          {researchLog.length === 0 ? (
            <div className="px-4 py-8 text-center text-xs text-text-3">
              No entries yet — run queries with Research Mode ON to populate this log.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-surface-2 border-b border-border">
                    {["Date", "Time", "Query", "Response", "Mode", "Cost ($)", "Tokens", "LLM Calls", "Confidence / Avg Sim.", "Resp. Time"].map(h => (
                      <th key={h} className="px-3 py-2.5 text-left text-text-3 font-semibold whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...researchLog].reverse().map((r, i) => (
                    <tr key={i} className="border-t border-border hover:bg-surface-2 transition-colors align-top">
                      <td className="px-3 py-2 font-mono text-text-3 whitespace-nowrap">{r.date}</td>
                      <td className="px-3 py-2 font-mono text-text-3 whitespace-nowrap">{r.time}</td>
                      <td className="px-3 py-2 text-text-2 max-w-[180px]">
                        <span title={r.query}>{r.query}</span>
                      </td>
                      <td className="px-3 py-2 text-text-2 max-w-[140px]">
                        <span title={r.response} className="cursor-help">
                          {r.response.split(" ").slice(0, 5).join(" ")}…
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className={`badge ${r.mode === "Agentic" ? "badge-green" : "badge-blue"}`}>{r.mode}</span>
                      </td>
                      <td className="px-3 py-2 font-mono text-amber">${r.cost_usd.toFixed(6)}</td>
                      <td className="px-3 py-2 font-mono text-blue">{r.total_tokens.toLocaleString()}</td>
                      <td className="px-3 py-2 font-mono text-text-2 text-center">{r.llm_calls}</td>
                      <td className="px-3 py-2 font-mono">
                        {r.confidence !== null
                          ? <span className={r.confidence >= 0.65 ? "text-accent" : r.confidence >= 0.35 ? "text-amber" : "text-red"}>
                              {(r.confidence * 100).toFixed(0)}%
                            </span>
                          : <span className="text-text-3">{r.avg_similarity?.toFixed(3) ?? "—"}</span>
                        }
                      </td>
                      <td className="px-3 py-2 font-mono text-text-3">{r.response_time.toFixed(2)}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

    </div>
  )
}
