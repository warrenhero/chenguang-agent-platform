export interface Conversation {
  id: string
  agentId: string
  agentName: string
  userId: string
  userName: string
  status: 'active' | 'completed' | 'failed'
  turnCount: number
  tokenUsage: number
  cost: number
  duration: number
  satisfaction?: number
  errorMessage?: string
  startedAt: string
  endedAt?: string
  tags?: string[]
}

export interface ConversationDetail extends Conversation {
  turns: ConversationTurn[]
  annotation?: ConversationAnnotation
}

export interface ConversationTurn {
  id: string
  conversationId: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  tokenCount?: number
  toolCalls?: unknown[]
  trace?: TurnTrace
}

export interface TurnTrace {
  steps: TraceStep[]
  inputTokens: number
  outputTokens: number
  totalDuration: number
  model: string
}

export interface TokenUsage {
  prompt: number
  completion: number
  total: number
}

export interface TraceStep {
  id: string
  turnId: string
  type: 'receive' | 'retrieval' | 'tool_call' | 'prompt_build' | 'llm_call' | 'response' | 'llm' | 'tool'
  name: string
  input?: unknown
  output?: unknown
  startTime: string
  endTime: string
  duration: number
  tokenUsage?: TokenUsage
  status: 'success' | 'failed'
  metadata?: {
    toolId?: string
    toolName?: string
    knowledgeBaseId?: string
    topK?: number
    [key: string]: unknown
  }
}

export interface ConversationAnnotation {
  rating: number
  tags: string[]
  notes: string
  annotatedBy: string
  annotatedAt: string
}
