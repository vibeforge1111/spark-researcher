export interface TokenReadiness {
  utility: number
  traction: number
  governance: number
  contribution: number
  trust: number
  treasury: number
  overall: number
}

export interface TimelineEntry {
  id: string
  title: string
  lane: string
  detail: string
  tone: 'good' | 'warn' | 'bad' | 'info'
  createdAt: string | null
}

export interface VentureExecution {
  venture_id: string
  next_action: string
  open_build_request_count: number
}

export interface VentureCustomer {
  venture_id: string
  conversation_count: number
  top_objections: string[]
}

export interface VentureTrust {
  venture_id: string
  capital_readiness: boolean
  capital_tasks: string[]
}

export interface VentureLearning {
  venture_id: string
  lesson: string
  doctrine_claim: string
}

export interface VentureTaskPacket {
  venture_id: string
  next_action: string
  required_tasks: string[]
}

export interface Venture {
  venture_id: string
  label: string
  stage: string
  status: string
  venture_model?: string
  customer_surface?: string
  distribution_engine?: string
  build_stack?: string
  venture_theme?: string
  bottleneck?: string
  weekly_revenue: number
  active_users: number
  automation_coverage: number
  customer_conversations_this_week: number
  paid_signals_this_week: number
  open_pipeline_count: number
  open_pipeline_value?: number
  trust_review_status?: string
  capital_readiness?: boolean
  doctrine_ready?: boolean
  shared_asset_count?: number
  customer_signal_count?: number
  promoted_playbook_count?: number
  ready_data_room_count?: number
  total_data_room_count?: number
  investor_target_count?: number
  revenue_trend?: number
  retention_signal?: number
  returning_customers?: number
  churned_customers?: number
  conversations_with_commitment?: number
  conversations_with_payment?: number
  evidence_backed_reviews?: number
  total_reviews?: number
  exit_reason?: string
  exit_lesson?: string
  execution: VentureExecution | null
  customer: VentureCustomer | null
  trust: VentureTrust | null
  learning: VentureLearning | null
  taskPacket: VentureTaskPacket | null
  tokenReadiness: TokenReadiness
  timeline: TimelineEntry[]
}

export interface Application {
  application_id: string
  label: string
  founder_id?: string
  founder_label?: string
  status: string
  venture_model?: string
  customer_surface?: string
  distribution_engine?: string
  venture_theme?: string
  thesis_summary?: string
  first_week_plan?: string[]
  incubator_compound_score?: number
  recommended_decision?: string
}

export interface HealthAlert {
  venture_id: string
  alert: string
  severity: 'warning' | 'critical'
  detail: string
}

export interface GovernanceProposal {
  proposal_id: string
  proposal_type: string
  venture_id: string
  description: string
  status: string
  votes_for: number
  votes_against: number
  note?: string
  created_at?: string
}

export interface GovernanceVote {
  proposal_id: string
  decision: string
  weight: number
  note?: string
  created_at?: string
}

export interface GovernanceResolution {
  proposal_id: string
  outcome: string
  votes_for: number
  votes_against: number
  quorum_met: number
  created_at?: string
}

export interface OfficeHoursPacket {
  venture_id: string
  commitment: string
  agenda: string[]
}

export interface DecisionPacket {
  venture_id: string
  decision: string
  required_next_step: string
}

export interface Metrics {
  incubator_compound_score: number
  ops_portfolio_focus_score: number
  ops_automation_coverage_score: number
  ops_review_hygiene_score: number
  ops_validation_velocity_score: number
  ops_trust_hygiene_score: number
  ops_knowledge_capture_score: number
  outcome_revenue_score?: number
  outcome_retention_score?: number
  outcome_impact_score?: number
  outcome_review_quality_score?: number
  verdict_confidence: number
  bottleneck: string
  active_portfolio_count: number
  portfolio_cap: number
}

export interface LatestTick {
  generated_at: string
  policy: Record<string, string>
  metrics: Metrics
  priority_ventures: Array<{ venture_id: string; label: string; next_action?: string }>
  health_alerts: HealthAlert[]
  critical_alert_count: number
  warning_alert_count: number
  office_hours_count: number
  decision_count: number
  venture_task_count: number
  stale_kpi_count: number
  pending_application_count: number
  conversation_count: number
  open_pipeline_count: number
  capital_ready_count: number
  blocking_trust_count: number
  promoted_playbook_count: number
  repeated_failure_count: number
}

export interface QueueSnapshot {
  generated_at: string
  portfolio_cap: number
  active_portfolio_count: number
  pending_applications: number
  venture_task_count: number
  conversation_count: number
  open_pipeline_count: number
  capital_ready_count: number
  promoted_playbook_count: number
  repeated_failure_count: number
}

export interface ProductConfig {
  name: string
  runtimeName: string
  operatorMode: string
  batchStyle?: string
  microBatchStyle?: string
  portfolioCap: number
  treasuryAssets?: string[]
  externalLaunchRail?: string
}

export interface GenesisSystem {
  spark: {
    baseToken: string
    governanceToken: string
    treasuryFlow: string
    projectExposure: string
  }
  phases: string[]
  rules: string[]
}

export interface CurriculumModule {
  id: string
  title: string
  description: string
  outputs: string[]
}

export interface NetworkNode {
  id: string
  label: string
  type: string
  score?: number
}

export interface NetworkEdge {
  id: string
  source: string
  target: string
  type: string
}

export interface FeedEntry {
  id: string
  title: string
  ventureId: string
  ventureLabel: string
  detail: string
  tone: 'good' | 'warn' | 'bad' | 'info'
  createdAt: string | null
}

export interface DashboardSnapshot {
  generatedAt: string
  product: ProductConfig
  latestTick: LatestTick
  queueSnapshot: QueueSnapshot
  state: {
    founders: Array<{ founder_id: string; label: string; venture_ids: string[] }>
    queues: Record<string, unknown[]>
    batches: Array<Record<string, unknown>>
  }
  scout: {
    pending_count: number
    applications: Application[]
  }
  officeHoursPackets: OfficeHoursPacket[]
  decisionPackets: DecisionPacket[]
  executionSnapshot: Record<string, unknown>
  customerSnapshot: Record<string, unknown>
  trustSnapshot: Record<string, unknown>
  learningSnapshot: Record<string, unknown>
  ventures: Venture[]
  feed?: FeedEntry[]
  network?: { nodes: NetworkNode[]; edges: NetworkEdge[] }
  curriculum?: CurriculumModule[]
  genesisSystem?: GenesisSystem
  governance?: {
    proposals: GovernanceProposal[]
    votes: GovernanceVote[]
    resolutions: GovernanceResolution[]
    stats: { total_resolved?: number; total_passed?: number }
  }
}

export interface AlertsResponse {
  alerts: HealthAlert[]
  critical_count: number
  warning_count: number
}

export interface StatusResponse {
  active_ventures: number
  batches: number
  pending_applications: number
  tick: LatestTick
}

export type ViewId =
  | 'overview'
  | 'ventures'
  | 'apply'
  | 'operations'
  | 'governance'
  | 'network'
  | 'genesis'
  | 'feed'
