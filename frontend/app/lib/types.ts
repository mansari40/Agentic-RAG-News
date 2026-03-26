export interface Source {
  title: string | null
  url: string | null
  content: string
  score: number
  source_type: string
  source_name: string | null
  published_at: string | null
  relevance_reason?: string
  keywords?: string[]
}

export interface ResearchStep {
  step: number
  type: "thought" | "action" | "observation" | "error"
  tool?: string
  args?: Record<string, unknown>
  summary: string
  count?: number
}

export interface QueryResult {
  answer: string
  sources: Source[]
  confidence: number
  reasoning_steps: string[]
  llm_calls: number
  retrieval_iterations: number
  response_time: number
  cached: boolean
  query_type: string
  mode: string
  is_domain_relevant: boolean
  cost_usd: number
  total_tokens: number
  evidence_summary: string
  key_facts: string[]
  researcher_scratchpad: ResearchStep[]
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: number
  result?: QueryResult
}

export interface SSEEvent {
  type: "start" | "step" | "thought" | "action" | "observation" | "result" | "complete" | "error"
  step?: string
  base_step?: string
  title?: string
  desc?: string
  text?: string
  tool?: string
  args?: Record<string, unknown>
  count?: number
  summary?: string
  data?: QueryResult
  message?: string
}

export interface ResearchLogEntry {
  date: string
  time: string
  query: string
  response: string
  mode: string
  cost_usd: number
  total_tokens: number
  llm_calls: number
  confidence: number | null        // agentic only
  avg_similarity: number | null    // baseline only
  response_time: number
}

export interface QueryCostEntry {
  query: string
  cost_usd: number
  total_tokens: number
  llm_calls: number
  confidence: number
  query_type: string
  timestamp: string
  mode: string
  response_time: number
  // Agentic pipeline metrics
  sources_collected?: number   // total raw articles fetched across all tool calls
  sources_verified?: number    // sources selected by the verifier
  tools_used?: string[]        // tool names called during research
}
