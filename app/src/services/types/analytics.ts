export interface AnalyticsOverview {
  totalCalls: number
  totalTokens: number
  totalCost: number
  avgLatency: number
  callsTrend: number
  tokensTrend: number
  costTrend: number
  latencyTrend: number
}

export interface DailyStats {
  date: string
  calls: number
  inputTokens: number
  outputTokens: number
  cost: number
  avgLatency: number
  successRate: number
}

export interface AgentAnalytics {
  agentId: string
  agentName: string
  calls: number
  tokens: number
  cost: number
  successRate: number
  avgLatency: number
}

export interface ModelAnalytics {
  modelId: string
  modelName: string
  calls: number
  inputTokens: number
  outputTokens: number
  cost: number
}

export interface CostAnalysis {
  monthCost: number
  dailyAvgCost: number
  projectedCost: number
  budgetRemaining: number
  costByModel: { model: string; cost: number }[]
  costByAgent: { agent: string; cost: number }[]
}

export interface Evaluation {
  avgSatisfaction: number
  annotationCoverage: number
  needsOptimization: number
  avgRating: number
  agentEvaluations: AgentEvaluation[]
  commonIssues: CommonIssue[]
}

export interface AgentEvaluation {
  agentId: string
  agentName: string
  satisfaction: number
  avgRating: number
  annotationCount: number
  needsOptimization: number
  trend: 'up' | 'down' | 'stable'
}

export interface CommonIssue {
  type: string
  count: number
  percentage: number
  trend: 'up' | 'down' | 'stable'
}

// ---- 用量统计 ----
export interface UsageOverview {
  totalCalls: number
  totalTokens: number
  totalCost: number
  avgResponseTime: number
  successRate: number
  period: string
}

export interface UsageDaily {
  date: string
  calls: number
  tokens: number
  cost: number
  avgResponseTime: number
  successRate: number
}

export interface UsageByAgent {
  agentId: string
  agentName: string
  calls: number
  tokens: number
  cost: number
  successRate: number
}

export interface UsageByModel {
  modelId: string
  modelName: string
  calls: number
  tokens: number
  cost: number
  avgResponseTime: number
}

export interface UsageByUser {
  userId: string
  userName: string
  calls: number
  tokens: number
  cost: number
  avgSatisfaction: number
}

export interface UsageStats {
  overview: UsageOverview
  daily: UsageDaily[]
  byAgent: UsageByAgent[]
  byModel: UsageByModel[]
  byUser: UsageByUser[]
}

// ---- 成本统计 ----
export interface CostOverview {
  totalCost: number
  modelCost: number
  toolCost: number
  storageCost: number
  otherCost: number
  period: string
}

export interface CostDaily {
  date: string
  total: number
  model: number
  tool: number
  storage: number
  other: number
}

export interface CostByModel {
  modelId: string
  modelName: string
  cost: number
  percentage: number
  calls: number
}

export interface CostByAgent {
  agentId: string
  agentName: string
  cost: number
  percentage: number
}

export interface CostByTool {
  toolId: string
  toolName: string
  cost: number
  calls: number
}

export interface CostTrend {
  current: number
  previous: number
  change: number
  forecast: number
}

export interface CostStats {
  overview: CostOverview
  daily: CostDaily[]
  byModel: CostByModel[]
  byAgent: CostByAgent[]
  byTool: CostByTool[]
  trend: CostTrend
}

// ---- 评估统计 ----
export interface EvaluationOverview {
  avgSatisfaction: number
  totalEvaluations: number
  positiveRate: number
  negativeRate: number
  neutralRate: number
  period: string
  annotationCoverage?: number
  avgRating?: number
  needsOptimization?: number
}

export interface EvaluationDistribution {
  score1: number
  score2: number
  score3: number
  score4: number
  score5: number
}

export interface EvaluationDaily {
  date: string
  avgScore: number
  evaluations: number
  positiveRate: number
}

export interface EvaluationByAgent {
  agentId: string
  agentName: string
  avgScore: number
  evaluations: number
  positiveRate: number
  needsOptimization?: number
  trend?: 'up' | 'down' | 'stable'
}

export interface EvaluationIssue {
  issue: string
  count: number
  percentage: number
}

export interface EvaluationImprovement {
  suggestion: string
  priority: 'high' | 'medium' | 'low'
  mentions: number
}

export interface EvaluationStats {
  overview: EvaluationOverview
  distribution: EvaluationDistribution
  daily: EvaluationDaily[]
  byAgent: EvaluationByAgent[]
  issues: EvaluationIssue[]
  improvements: EvaluationImprovement[]
}
