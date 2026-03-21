const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface QueryOptions {
  allowedTools?: string[]
  dateFrom?: string
  dateTo?: string
}

export async function queryBaseline(question: string, useHybrid = true, topK = 5, opts: QueryOptions = {}) {
  const body: Record<string, unknown> = { question, mode: "baseline", use_hybrid: useHybrid, top_k: topK }
  if (opts.dateFrom) body.date_from = opts.dateFrom
  if (opts.dateTo)   body.date_to   = opts.dateTo
  const r = await fetch(`${API}/query/baseline`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`Baseline error: ${r.status}`)
  const data = await r.json()
  data.mode = "baseline"
  return data
}

export async function queryAgenticNonStream(question: string) {
  const r = await fetch(`${API}/query/agentic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, mode: "agentic" }),
  })
  if (!r.ok) throw new Error(`Agentic error: ${r.status}`)
  const data = await r.json()
  data.mode = "agentic"
  return data
}

export function createAgenticStream(question: string): EventSource {
  const url = `${API}/query/agentic/stream`
  // Use fetch-based streaming for POST requests
  return new EventSource(`${API}/query/agentic/stream?q=${encodeURIComponent(question)}`)
}

export async function streamAgentic(
  question: string,
  onEvent: (event: import("./types").SSEEvent) => void,
  signal?: AbortSignal,
  opts: QueryOptions = {}
): Promise<void> {
  const body: Record<string, unknown> = { question, mode: "agentic" }
  if (opts.allowedTools?.length) body.allowed_tools = opts.allowedTools
  if (opts.dateFrom) body.date_from = opts.dateFrom
  if (opts.dateTo)   body.date_to   = opts.dateTo
  const response = await fetch(`${API}/query/agentic/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  })

  if (!response.body) throw new Error("No response body")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split("\n")
    buffer = lines.pop() || ""
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event = JSON.parse(line.slice(6))
          onEvent(event)
          if (event.type === "complete" || event.type === "error") return
        } catch { /* skip malformed */ }
      }
    }
  }
}

export async function clearMemory() {
  await fetch(`${API}/agentic/memory/clear`, { method: "POST" })
}

export async function getHealth() {
  try {
    const r = await fetch(`${API}/health`, { signal: AbortSignal.timeout(3000) })
    return r.ok ? await r.json() : null
  } catch { return null }
}

export async function getSessionCost() {
  try {
    const r = await fetch(`${API}/agentic/cost`)
    return r.ok ? await r.json() : null
  } catch { return null }
}
