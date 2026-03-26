"use client"

/* ─────────────────────────────────────────────────────────────────────────────
   ArchitectureTab — animated SVG pipeline diagrams
   Baseline RAG  : horizontal 6-node chain with flowing-dash arrows
   Agentic RAG   : vertical researcher + fan-out retrieval bus + refine loop
────────────────────────────────────────────────────────────────────────────── */

const BASELINE_STEPS = [
  { label: "User Query", color: "#1e3a5f", border: "#3b82f6" },
  { label: "Embedder", sub: "text-embedding-3-small", color: "#1e40af", border: "#3b82f6" },
  { label: "Vector DB", sub: "hybrid BM25 + vector", color: "#052e16", border: "#4ade80" },
  { label: "Top-K Select", sub: "k = 1–10", color: "#1e40af", border: "#3b82f6" },
  { label: "LLM Generate", sub: "gpt-4o-mini", color: "#2d1657", border: "#a855f7" },
  { label: "Answer", color: "#450a0a", border: "#ef4444" },
]

/* ── SVG geometry ── */
const B_W = 980      // baseline svg width
const B_H = 180
const B_NODE_W = 128
const B_NODE_H = 64
const B_GAP = 16     // gap between nodes
const B_ARROW = 16
const B_TOTAL = BASELINE_STEPS.length * B_NODE_W + (BASELINE_STEPS.length - 1) * (B_GAP + B_ARROW)
const B_LEFT = (B_W - B_TOTAL) / 2
const B_CY = B_H / 2 + 12   // shift down to leave room for title

function bNodeX(i: number) {
  return B_LEFT + i * (B_NODE_W + B_GAP + B_ARROW)
}

/* ── Agentic SVG uses internal constants defined in AgenticSVG ── */

export function ArchitectureTab() {
  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <style>{`
        /* flowing dash animation */
        @keyframes arch-dash {
          to { stroke-dashoffset: -20; }
        }
        @keyframes arch-dash-rev {
          to { stroke-dashoffset: 20; }
        }
        /* node pulse */
        @keyframes arch-pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.65; }
        }
        /* fade-in for detail panels */
        @keyframes arch-fadein {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .arch-fl {
          stroke-dasharray: 6 4;
          animation: arch-dash 0.7s linear infinite;
        }
        .arch-fl-slow {
          stroke-dasharray: 6 4;
          animation: arch-dash 1.1s linear infinite;
        }
        .arch-fl-rev {
          stroke-dasharray: 5 4;
          animation: arch-dash-rev 0.9s linear infinite;
        }
        .arch-pulse {
          animation: arch-pulse 2s ease-in-out infinite;
        }
        .arch-detail-open {
          animation: arch-fadein 0.2s ease-out forwards;
        }

        /* staggered delays for baseline arrows */
        .arch-d0  { animation-delay: 0s; }
        .arch-d1  { animation-delay: 0.12s; }
        .arch-d2  { animation-delay: 0.24s; }
        .arch-d3  { animation-delay: 0.36s; }
        .arch-d4  { animation-delay: 0.48s; }

        /* staggered for agentic fan-out lines */
        .arch-fan0 { animation-delay: 0s; }
        .arch-fan1 { animation-delay: 0.18s; }
        .arch-fan2 { animation-delay: 0.36s; }
      `}</style>

      {/* ═══════════════ BASELINE RAG ═══════════════ */}
      <div className="card p-5" style={{ borderLeft: "3px solid #3b82f6" }}>
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-sm font-bold" style={{ color: "#111827" }}>Baseline RAG Pipeline</h2>
        </div>
        <p className="text-xs mb-4" style={{ color: "#64748b" }}>
          Single-source retrieval from a local vector database using hybrid <strong style={{ color: "#94a3b8" }}>BM25 + dense vector</strong> search with RRF fusion, followed by a single LLM generation step.
        </p>

        {/* SVG diagram */}
        <div className="overflow-x-auto">
          <svg
            width="100%"
            viewBox={`0 0 ${B_W} ${B_H}`}
            preserveAspectRatio="xMidYMid meet"
            style={{ minWidth: 520 }}
          >
            <defs>
              {/* glow filters */}
              <filter id="gb" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                <feFlood floodColor="#3b82f6" floodOpacity="0.45" result="c" />
                <feComposite in="c" in2="blur" operator="in" result="glow" />
                <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="gg" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                <feFlood floodColor="#10b981" floodOpacity="0.45" result="c" />
                <feComposite in="c" in2="blur" operator="in" result="glow" />
                <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="gp" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                <feFlood floodColor="#8b5cf6" floodOpacity="0.45" result="c" />
                <feComposite in="c" in2="blur" operator="in" result="glow" />
                <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              <filter id="gr" x="-30%" y="-30%" width="160%" height="160%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="3" result="blur" />
                <feFlood floodColor="#ef4444" floodOpacity="0.45" result="c" />
                <feComposite in="c" in2="blur" operator="in" result="glow" />
                <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
              {/* gradient fills */}
              <linearGradient id="lgS" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1e3a5f" />
                <stop offset="100%" stopColor="#0f1f3d" />
              </linearGradient>
              <linearGradient id="lgB" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1e40af" />
                <stop offset="100%" stopColor="#0f2270" />
              </linearGradient>
              <linearGradient id="lgG" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#065f46" />
                <stop offset="100%" stopColor="#022c20" />
              </linearGradient>
              <linearGradient id="lgP" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b0764" />
                <stop offset="100%" stopColor="#1e0032" />
              </linearGradient>
              <linearGradient id="lgR" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#7f1d1d" />
                <stop offset="100%" stopColor="#3f0d0d" />
              </linearGradient>
              {/* arrow markers */}
              <marker id="ahB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#3b82f6" />
              </marker>
              <marker id="ahG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#4ade80" />
              </marker>
              <marker id="ahP" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#a855f7" />
              </marker>
              <marker id="ahR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
                <path d="M0,1 L9,5 L0,9 Z" fill="#ef4444" />
              </marker>
            </defs>

            {/* background */}
            <rect width={B_W} height={B_H} rx="12" fill="#0a1220" />

            {/* diagram title */}
            <text x={B_W / 2} y={16} textAnchor="middle" fontSize="16" fontWeight="700"
              fill="#e2e8f0" fontFamily="Inter, sans-serif" letterSpacing="0.5">
              Baseline RAG Pipeline
            </text>

            {BASELINE_STEPS.map((step, i) => {
              const x = bNodeX(i)
              const glowFilter =
                step.border === "#3b82f6" ? "url(#gb)"
                : step.border === "#4ade80" ? "url(#gg)"
                : step.border === "#a855f7" ? "url(#gp)"
                : "url(#gr)"
              const gradient =
                step.border === "#3b82f6" ? (i === 0 ? "url(#lgS)" : "url(#lgB)")
                : step.border === "#4ade80" ? "url(#lgG)"
                : step.border === "#a855f7" ? "url(#lgP)"
                : "url(#lgR)"
              const arrowColor =
                step.border === "#3b82f6" ? "#3b82f6"
                : step.border === "#4ade80" ? "#4ade80"
                : step.border === "#a855f7" ? "#a855f7"
                : "#ef4444"
              const arrowMarker =
                step.border === "#3b82f6" ? "url(#ahB)"
                : step.border === "#4ade80" ? "url(#ahG)"
                : step.border === "#a855f7" ? "url(#ahP)"
                : "url(#ahR)"

              return (
                <g key={i}>
                  {/* node box */}
                  <rect
                    x={x} y={B_CY - B_NODE_H / 2}
                    width={B_NODE_W} height={B_NODE_H}
                    rx="8"
                    fill={gradient}
                    stroke={step.border}
                    strokeWidth="1.5"
                    filter={glowFilter}
                  />
                  <text
                    x={x + B_NODE_W / 2} y={B_CY - (step.sub ? 10 : 0)}
                    textAnchor="middle"
                    fontSize="13"
                    fontWeight="700"
                    fill="#e2e8f0"
                    fontFamily="Inter, sans-serif"
                  >
                    {step.label}
                  </text>
                  {step.sub && (
                    <text
                      x={x + B_NODE_W / 2} y={B_CY + 12}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#94a3b8"
                      fontFamily="Inter, sans-serif"
                    >
                      {step.sub}
                    </text>
                  )}

                  {/* animated arrow to next node */}
                  {i < BASELINE_STEPS.length - 1 && (
                    <line
                      x1={x + B_NODE_W} y1={B_CY}
                      x2={x + B_NODE_W + B_GAP + B_ARROW} y2={B_CY}
                      stroke={arrowColor}
                      strokeWidth="2"
                      markerEnd={arrowMarker}
                      className={`arch-fl arch-d${i}`}
                    />
                  )}
                </g>
              )
            })}
          </svg>
        </div>

        <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid #e5e7eb" }}>
          {[["~3 sec","Speed"],["1 LLM","Call"],["~$0.0001","Cost"]].map(([val,label]) => (
            <span key={label} className="text-xs px-2.5 py-0.5 rounded-md font-mono font-semibold"
              style={{ background: "#e8f5e9", color: "#2e7d32" }}>
              {val} <span style={{ fontWeight: 400, color: "#4caf50" }}>{label}</span>
            </span>
          ))}
        </div>

      </div>

      {/* ═══════════════ AGENTIC RAG ═══════════════ */}
      <div className="card p-5" style={{ borderLeft: "3px solid #4ade80" }}>
        <div className="flex items-center gap-2 mb-1">
          <h2 className="text-sm font-bold" style={{ color: "#111827" }}>Agentic RAG Pipeline</h2>
        </div>
        <p className="text-xs mb-4" style={{ color: "#64748b" }}>
          Multi-agent LangGraph orchestration across <strong style={{ color: "#94a3b8" }}>three live sources</strong> - Tavily Specialist, MediaStack, and Tavily Web with LLM-based ranking, fact verification, answer synthesis, and an optional refinement loop.
        </p>

        {/* SVG diagram */}
        <div className="overflow-x-auto">
          <AgenticSVG />
        </div>

        <div className="flex items-center gap-2 mt-3 pt-3" style={{ borderTop: "1px solid #e5e7eb" }}>
          {[["20–50 sec","Speed"],["6–8 LLM","Calls"],["~$0.03","Cost"]].map(([val,label]) => (
            <span key={label} className="text-xs px-2.5 py-0.5 rounded-md font-mono font-semibold"
              style={{ background: "#e8f5e9", color: "#2e7d32" }}>
              {val} <span style={{ fontWeight: 400, color: "#4caf50" }}>{label}</span>
            </span>
          ))}
        </div>

      </div>

      {/* ═══════════════ CLOUD INFRASTRUCTURE ═══════════════ */}
      <div className="card p-5" style={{ borderLeft: "3px solid #38bdf8" }}>
        <div className="flex items-center gap-2 mb-4">
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "#4ade80",
            boxShadow: "0 0 6px #4ade80",
            animation: "arch-pulse 2s ease-in-out infinite"
          }} />
          <h2 className="text-sm font-bold" style={{ color: "#111827" }}>
            Cloud Infrastructure
          </h2>
          <span className="text-xs px-2 py-0.5 rounded-full font-mono"
            style={{ background: "#0f2d1a", color: "#4ade80", border: "1px solid #166534" }}>
            LIVE
          </span>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {/* Render */}
          <div className="rounded-xl p-4" style={{
            background: "linear-gradient(135deg, #0d1f2d 0%, #071521 100%)",
            border: "1px solid #1e40af"
          }}>
            <div className="flex items-center gap-2 mb-3">
              <div className="rounded-lg flex items-center justify-center text-base font-bold"
                style={{ width: 32, height: 32, background: "#1e3a8a", color: "#93c5fd", border: "1px solid #3b82f6", fontSize: 14 }}>
                R
              </div>
              <div>
                <div className="text-sm font-bold" style={{ color: "#93c5fd" }}>Render</div>
                <div className="text-xs" style={{ color: "#475569" }}>render.com</div>
              </div>
            </div>
            <div className="text-xs leading-relaxed mb-3" style={{ color: "#94a3b8" }}>
              Cloud application platform hosting both the <span style={{ color: "#e2e8f0", fontWeight: 600 }}>FastAPI backend</span> and <span style={{ color: "#e2e8f0", fontWeight: 600 }}>Next.js frontend</span> as separate web services.
            </div>
            <div className="flex flex-wrap gap-1.5">
              {["FastAPI", "Next.js", "Docker"].map(t => (
                <span key={t} className="text-xs px-2 py-0.5 rounded font-mono"
                  style={{ background: "#1e3a8a", color: "#93c5fd", border: "1px solid #1e40af" }}>{t}</span>
              ))}
            </div>
          </div>

          {/* Neon */}
          <div className="rounded-xl p-4" style={{
            background: "linear-gradient(135deg, #0c1f1a 0%, #071512 100%)",
            border: "1px solid #065f46"
          }}>
            <div className="flex items-center gap-2 mb-3">
              <div className="rounded-lg flex items-center justify-center text-base font-bold"
                style={{ width: 32, height: 32, background: "#064e3b", color: "#6ee7b7", border: "1px solid #10b981", fontSize: 14 }}>
                N
              </div>
              <div>
                <div className="text-sm font-bold" style={{ color: "#6ee7b7" }}>Neon</div>
                <div className="text-xs" style={{ color: "#475569" }}>neon.tech</div>
              </div>
            </div>
            <div className="text-xs leading-relaxed mb-3" style={{ color: "#94a3b8" }}>
              Serverless <span style={{ color: "#e2e8f0", fontWeight: 600 }}>PostgreSQL</span> database storing article metadata and the <span style={{ color: "#e2e8f0", fontWeight: 600 }}>BM25 keyword index</span> used by the hybrid retriever in Baseline RAG.
            </div>
            <div className="flex flex-wrap gap-1.5">
              {["PostgreSQL", "BM25 Index", "Serverless"].map(t => (
                <span key={t} className="text-xs px-2 py-0.5 rounded font-mono"
                  style={{ background: "#064e3b", color: "#6ee7b7", border: "1px solid #065f46" }}>{t}</span>
              ))}
            </div>
          </div>

          {/* Qdrant Cloud */}
          <div className="rounded-xl p-4" style={{
            background: "linear-gradient(135deg, #1a0d2e 0%, #110720 100%)",
            border: "1px solid #7c3aed"
          }}>
            <div className="flex items-center gap-2 mb-3">
              <div className="rounded-lg flex items-center justify-center text-base font-bold"
                style={{ width: 32, height: 32, background: "#4c1d95", color: "#c4b5fd", border: "1px solid #7c3aed", fontSize: 14 }}>
                Q
              </div>
              <div>
                <div className="text-sm font-bold" style={{ color: "#c4b5fd" }}>Qdrant Cloud</div>
                <div className="text-xs" style={{ color: "#475569" }}>cloud.qdrant.io</div>
              </div>
            </div>
            <div className="text-xs leading-relaxed mb-3" style={{ color: "#94a3b8" }}>
              Managed <span style={{ color: "#e2e8f0", fontWeight: 600 }}>vector database</span> (cluster: <span style={{ color: "#c4b5fd", fontFamily: "monospace" }}>Timber_intel</span>) storing dense embeddings of curated timber articles for semantic search.
            </div>
            <div className="flex flex-wrap gap-1.5">
              {["Vector DB", "Embeddings", "EU-central-1"].map(t => (
                <span key={t} className="text-xs px-2 py-0.5 rounded font-mono"
                  style={{ background: "#4c1d95", color: "#c4b5fd", border: "1px solid #7c3aed" }}>{t}</span>
              ))}
            </div>
          </div>
        </div>

        {/* connection legend */}
        <div className="mt-4 pt-3 flex flex-wrap gap-4 text-xs" style={{ borderTop: "1px solid #1e293b", color: "#64748b" }}>
          <span><span style={{ color: "#93c5fd" }}>●</span> Render → Neon: SQLAlchemy connection pool (hybrid retrieval)</span>
          <span><span style={{ color: "#c4b5fd" }}>●</span> Render → Qdrant Cloud: REST API (vector similarity search)</span>
          <span><span style={{ color: "#4ade80" }}>●</span> All services: EU-central-1 region</span>
        </div>
      </div>

    </div>
  )
}

/* ─────────────────────────────────────────────────────────────────────────────
   AgenticSVG — vertical pipeline with scope check, fan-out retrieval + refine loop
────────────────────────────────────────────────────────────────────────────── */
function AgenticSVG() {
  const W = 820
  const H = 850
  const CX = W / 2

  const Y_QUERY    = 78
  const Y_PLANNER  = 148
  const Y_SCOPE    = 230
  const Y_ORCH     = 335
  const Y_BUS_TOP  = 405
  const Y_SOURCE   = 455
  const Y_BUS_BOT  = 505
  const Y_RANKER   = 572
  const Y_VERIFIER = 644
  const Y_SYNTH    = 720
  const Y_ANSWER   = 790

  const SRC_XS = [116, 312, 508, 704]
  const NODE_W = 150
  const NODE_H = 44

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      style={{ minWidth: 480 }}
    >
      <defs>
        <filter id="ag-gB" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#3b82f6" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gG" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#4ade80" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gA" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#f59e0b" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gP" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#a855f7" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gI" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#818cf8" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gC" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#06b6d4" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="ag-gR" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="4" result="blur" />
          <feFlood floodColor="#ef4444" floodOpacity="0.5" result="c" />
          <feComposite in="c" in2="blur" operator="in" result="glow" />
          <feMerge><feMergeNode in="glow" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>

        {/* gradients */}
        <linearGradient id="ag-lgS" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" /><stop offset="100%" stopColor="#0f1f3d" />
        </linearGradient>
        <linearGradient id="ag-lgB" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e3a5f" /><stop offset="100%" stopColor="#0b1f38" />
        </linearGradient>
        <linearGradient id="ag-lgG" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#14532d" /><stop offset="100%" stopColor="#082817" />
        </linearGradient>
        <linearGradient id="ag-lgA" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#451a03" /><stop offset="100%" stopColor="#220d00" />
        </linearGradient>
        <linearGradient id="ag-lgP" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2d1657" /><stop offset="100%" stopColor="#160929" />
        </linearGradient>
        <linearGradient id="ag-lgI" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e1b4b" /><stop offset="100%" stopColor="#0d0b25" />
        </linearGradient>
        <linearGradient id="ag-lgGreen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#052e16" /><stop offset="100%" stopColor="#021509" />
        </linearGradient>
        <linearGradient id="ag-lgC" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#164e63" /><stop offset="100%" stopColor="#083344" />
        </linearGradient>
        <linearGradient id="ag-lgR" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#7f1d1d" /><stop offset="100%" stopColor="#3f0d0d" />
        </linearGradient>

        {/* arrows */}
        <marker id="ag-ahB" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#3b82f6" />
        </marker>
        <marker id="ag-ahG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#4ade80" />
        </marker>
        <marker id="ag-ahA" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#f59e0b" />
        </marker>
        <marker id="ag-ahP" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#a855f7" />
        </marker>
        <marker id="ag-ahI" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#818cf8" />
        </marker>
        <marker id="ag-ahR" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#f59e0b" />
        </marker>
        <marker id="ag-ahRed" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#ef4444" />
        </marker>
        <marker id="ag-ahC" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto">
          <path d="M0,1 L9,5 L0,9 Z" fill="#06b6d4" />
        </marker>
      </defs>

      {/* background */}
      <rect width={W} height={H} rx="12" fill="#0a1220" />

      {/* diagram title */}
      <text x={W / 2} y={16} textAnchor="middle" fontSize="14" fontWeight="700"
        fill="#e2e8f0" fontFamily="Inter, sans-serif" letterSpacing="0.5">
        Agentic RAG Pipeline
      </text>

      {/* ── User Query ── */}
      <NodeRect cx={CX} cy={Y_QUERY} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgS)" stroke="#3b82f6" filter="url(#ag-gB)"
        label="User Query" />

      {/* arrow: User Query → QueryPlanner */}
      <line x1={CX} y1={Y_QUERY + NODE_H / 2} x2={CX} y2={Y_PLANNER - NODE_H / 2}
        stroke="#3b82f6" strokeWidth="2" markerEnd="url(#ag-ahB)"
        className="arch-fl arch-d0" />

      {/* ── 1. QueryPlanner ── */}
      <NodeRect cx={CX} cy={Y_PLANNER} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgB)" stroke="#3b82f6" filter="url(#ag-gB)"
        label="① Planner" sub="gpt-4o-mini" />

      {/* arrow: QueryPlanner → ScopeCheck */}
      <line x1={CX} y1={Y_PLANNER + NODE_H / 2} x2={CX} y2={Y_SCOPE - NODE_H / 2}
        stroke="#06b6d4" strokeWidth="2" markerEnd="url(#ag-ahC)"
        className="arch-fl arch-d0" />

      {/* ── Scope Check ── */}
      <NodeRect cx={CX} cy={Y_SCOPE} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgC)" stroke="#06b6d4" filter="url(#ag-gC)"
        label="Scope Check" sub="in scope?" />

      {/* Out of Scope arrow → left */}
      <line
        x1={CX - (NODE_W + 30) / 2} y1={Y_SCOPE}
        x2={138} y2={Y_SCOPE}
        stroke="#ef4444" strokeWidth="2" markerEnd="url(#ag-ahRed)"
        strokeDasharray="5 3"
      />
      <text x={185} y={Y_SCOPE - 9}
        textAnchor="middle" fontSize="8.5" fill="#ef4444" fontFamily="Inter, sans-serif">
        No
      </text>

      {/* Out of Scope box */}
      <NodeRect cx={75} cy={Y_SCOPE} w={120} h={NODE_H}
        fill="url(#ag-lgR)" stroke="#ef4444" filter="url(#ag-gR)"
        label="Not Answered" sub="out of scope" />

      {/* In Scope arrow → down to Researcher */}
      <line x1={CX} y1={Y_SCOPE + NODE_H / 2} x2={CX} y2={Y_ORCH - NODE_H / 2}
        stroke="#3b82f6" strokeWidth="2" markerEnd="url(#ag-ahB)"
        className="arch-fl arch-d0" />
      <text x={CX + 10} y={(Y_SCOPE + Y_ORCH) / 2}
        textAnchor="start" fontSize="8.5" fill="#4ade80" fontFamily="Inter, sans-serif">
        Yes
      </text>

      {/* ── 2. Researcher ── */}
      <NodeRect cx={CX} cy={Y_ORCH} w={NODE_W + 40} h={NODE_H}
        fill="url(#ag-lgG)" stroke="#4ade80" filter="url(#ag-gG)"
        label="② Researcher" sub="gpt-4o · ReAct · max 6 steps" />

      {/* fan-out: researcher → bus */}
      <line x1={CX} y1={Y_ORCH + NODE_H / 2} x2={CX} y2={Y_BUS_TOP}
        stroke="#4ade80" strokeWidth="2"
        className="arch-fl arch-d0" />

      {/* horizontal bus line */}
      <line x1={SRC_XS[0]} y1={Y_BUS_TOP} x2={SRC_XS[SRC_XS.length-1]} y2={Y_BUS_TOP}
        stroke="#4ade80" strokeWidth="1.5"
        strokeDasharray="4 3"
        className="arch-fl-slow" />

      {/* bus → each source */}
      {SRC_XS.map((sx, i) => (
        <line key={i}
          x1={sx} y1={Y_BUS_TOP} x2={sx} y2={Y_SOURCE - NODE_H / 2}
          stroke="#4ade80" strokeWidth="2" markerEnd="url(#ag-ahG)"
          className={`arch-fl arch-fan${i}`}
        />
      ))}

      {/* ── 3. Tool nodes ── */}
      <ToolNode cx={SRC_XS[0]} cy={Y_SOURCE} label="Tavily Specialist"
        sub="timber-online · holzkurier…" fill="url(#ag-lgB)" stroke="#3b82f6" filter="url(#ag-gB)" />
      <ToolNode cx={SRC_XS[1]} cy={Y_SOURCE} label="MediaStack"
        sub="12 German keywords" fill="url(#ag-lgA)" stroke="#f59e0b" filter="url(#ag-gA)" />
      <ToolNode cx={SRC_XS[2]} cy={Y_SOURCE} label="Tavily Web"
        sub="Open web search" fill="url(#ag-lgB)" stroke="#60a5fa" filter="url(#ag-gB)" />
      <ToolNode cx={SRC_XS[3]} cy={Y_SOURCE} label="Baseline DB"
        sub="hybrid BM25 + vector" fill="url(#ag-lgI)" stroke="#818cf8" filter="url(#ag-gI)" />

      {/* fan-in: 3 sources → ranker bus */}
      {SRC_XS.map((sx, i) => (
        <line key={i}
          x1={sx} y1={Y_SOURCE + NODE_H / 2} x2={sx} y2={Y_BUS_BOT}
          stroke="#64748b" strokeWidth="1.5" markerEnd="url(#ag-ahG)"
          className={`arch-fl arch-fan${i}`}
        />
      ))}

      {/* horizontal fan-in bus */}
      <line x1={SRC_XS[0]} y1={Y_BUS_BOT} x2={SRC_XS[SRC_XS.length-1]} y2={Y_BUS_BOT}
        stroke="#64748b" strokeWidth="1.5"
        strokeDasharray="4 3"
        className="arch-fl-slow" />

      {/* source count label */}
      <text x={CX} y={Y_BUS_BOT - 6} textAnchor="middle" fontSize="9"
        fill="#64748b" fontFamily="Inter, sans-serif">
        ~40 raw sources
      </text>

      {/* bus → ranker */}
      <line x1={CX} y1={Y_BUS_BOT} x2={CX} y2={Y_RANKER - NODE_H / 2}
        stroke="#a855f7" strokeWidth="2" markerEnd="url(#ag-ahP)"
        className="arch-fl arch-d1" />

      {/* ── 4. SourceRanker ── */}
      <NodeRect cx={CX} cy={Y_RANKER} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgP)" stroke="#a855f7" filter="url(#ag-gP)"
        label="④ Ranker" sub="gpt-4o-mini · 40 → 20" />

      {/* ranker → verifier */}
      <line x1={CX} y1={Y_RANKER + NODE_H / 2} x2={CX} y2={Y_VERIFIER - NODE_H / 2}
        stroke="#a855f7" strokeWidth="2" markerEnd="url(#ag-ahP)"
        className="arch-fl arch-d1" />

      {/* ── 5. FactVerifier ── */}
      <NodeRect cx={CX} cy={Y_VERIFIER} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgGreen)" stroke="#4ade80" filter="url(#ag-gG)"
        label="⑤ Verifier" sub="gpt-4o · reads 20 sources" />

      {/* verifier → synthesizer */}
      <line x1={CX} y1={Y_VERIFIER + NODE_H / 2} x2={CX} y2={Y_SYNTH - NODE_H / 2}
        stroke="#818cf8" strokeWidth="2" markerEnd="url(#ag-ahI)"
        className="arch-fl arch-d2" />

      {/* ── 6. AnswerSynthesizer ── */}
      <NodeRect cx={CX} cy={Y_SYNTH} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgI)" stroke="#818cf8" filter="url(#ag-gI)"
        label="⑥ Synthesizer" sub="gpt-4o-mini · final answer" />

      {/* synthesizer → answer */}
      <line x1={CX} y1={Y_SYNTH + NODE_H / 2} x2={CX} y2={Y_ANSWER - NODE_H / 2}
        stroke="#ef4444" strokeWidth="2" markerEnd="url(#ag-ahRed)"
        className="arch-fl arch-d2" />

      {/* ── Answer ── */}
      <NodeRect cx={CX} cy={Y_ANSWER} w={NODE_W + 30} h={NODE_H}
        fill="url(#ag-lgR)" stroke="#ef4444" filter="url(#ag-gR)"
        label="Answer" />

      {/* ── Amber refine loop (right side) ── */}
      <path
        d={`M ${CX + (NODE_W + 30) / 2} ${Y_SYNTH}
            L ${W - 12} ${Y_SYNTH}
            L ${W - 12} ${Y_ORCH}
            L ${CX + (NODE_W + 40) / 2} ${Y_ORCH}`}
        fill="none"
        stroke="#f59e0b"
        strokeWidth="1.8"
        markerEnd="url(#ag-ahR)"
        className="arch-fl-rev"
        strokeDasharray="5 4"
      />
      {/* refine label */}
      <text x={W - 6} y={(Y_SYNTH + Y_ORCH) / 2} textAnchor="middle"
        fontSize="8.5" fill="#f59e0b" fontFamily="Inter, sans-serif"
        transform={`rotate(-90, ${W - 6}, ${(Y_SYNTH + Y_ORCH) / 2})`}>
        refine loop (max 2×)
      </text>
      {/* refine condition label */}
      <text x={(CX + (NODE_W + 30) / 2 + W - 12) / 2} y={Y_SYNTH + 14}
        textAnchor="middle" fontSize="8" fill="#64748b" fontFamily="Inter, sans-serif">
        if confidence &lt; 0.45
      </text>
    </svg>
  )
}

/* ── Small helper components ── */
function NodeRect({
  cx, cy, w, h, fill, stroke, filter, label, sub,
}: {
  cx: number; cy: number; w: number; h: number
  fill: string; stroke: string; filter: string
  label: string; sub?: string
}) {
  return (
    <g>
      <rect
        x={cx - w / 2} y={cy - h / 2}
        width={w} height={h} rx="8"
        fill={fill} stroke={stroke} strokeWidth="1.5"
        filter={filter}
      />
      <text
        x={cx} y={cy - (sub ? 7 : 1)}
        textAnchor="middle" fontSize="11" fontWeight="700"
        fill="#e2e8f0" fontFamily="Inter, sans-serif"
      >
        {label}
      </text>
      {sub && (
        <text
          x={cx} y={cy + 9}
          textAnchor="middle" fontSize="8.5"
          fill="#94a3b8" fontFamily="Inter, sans-serif"
        >
          {sub}
        </text>
      )}
    </g>
  )
}

function ToolNode({
  cx, cy, label, sub, fill, stroke, filter,
}: {
  cx: number; cy: number; label: string; sub: string
  fill: string; stroke: string; filter: string
}) {
  const w = 152, h = 44
  return (
    <g>
      <rect
        x={cx - w / 2} y={cy - h / 2}
        width={w} height={h} rx="7"
        fill={fill} stroke={stroke} strokeWidth="1.5"
        filter={filter}
        className="arch-pulse"
      />
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="10" fontWeight="700"
        fill="#e2e8f0" fontFamily="Inter, sans-serif">{label}</text>
      <text x={cx} y={cy + 8} textAnchor="middle" fontSize="8"
        fill="#94a3b8" fontFamily="Inter, sans-serif">{sub}</text>
    </g>
  )
}
