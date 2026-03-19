import { useCallback, useEffect, useState } from 'react'

import { api } from './api'
import rawData from './generated/incubator-dashboard.json'

type DashboardData = typeof rawData
type Venture = DashboardData['ventures'][number]
type FeedEntry = DashboardData['feed'][number]
type NavCommand =
  | 'batches'
  | 'ventures'
  | 'proof'
  | 'apply'
  | 'operator'
  | 'network'
  | 'genesis'
  | 'feed'
  | 'autoloop'
  | 'curriculum'
  | 'ops'
type AppTheme = 'light' | 'dark'

const data = rawData as DashboardData

const NAV_ITEMS: Array<{ label: string; command: NavCommand }> = [
  { label: 'Batches', command: 'batches' },
  { label: 'Ventures', command: 'ventures' },
  { label: 'Proof', command: 'proof' },
  { label: 'Apply', command: 'apply' },
  { label: 'Operator', command: 'operator' },
  { label: 'Network', command: 'network' },
  { label: 'Genesis', command: 'genesis' },
  { label: 'Feed', command: 'feed' },
  { label: 'Autoloop', command: 'autoloop' },
  { label: 'Curriculum', command: 'curriculum' },
  { label: 'Ops', command: 'ops' },
]

function formatCurrency(value: number | null | undefined) {
  if (value === null || value === undefined) return 'n/a'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: value >= 1000 ? 0 : 2,
  }).format(value)
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return 'n/a'
  return `${Math.round(value * 100)}%`
}

function shortAge(value: string | null | undefined) {
  if (!value) return 'n/a'
  const parsed = Date.parse(value)
  if (!Number.isFinite(parsed)) return value
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - parsed) / 1000))
  if (deltaSeconds < 60) return 'just now'
  if (deltaSeconds < 3600) return `${Math.floor(deltaSeconds / 60)}m ago`
  if (deltaSeconds < 86400) return `${Math.floor(deltaSeconds / 3600)}h ago`
  return `${Math.floor(deltaSeconds / 86400)}d ago`
}

function initialTheme(): AppTheme {
  try {
    const cached = window.localStorage.getItem('vibe-vibe-theme')
    if (cached === 'light' || cached === 'dark') return cached
  } catch {
    // ignore
  }
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function SidebarSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string
  defaultOpen?: boolean
  children: React.ReactNode
}) {
  return (
    <details className="sidebar-section" open={defaultOpen || undefined}>
      <summary className="sidebar-section-toggle">{title}</summary>
      <div className="sidebar-section-body">{children}</div>
    </details>
  )
}

function ViewIntro({ id, children }: { id: string; children: React.ReactNode }) {
  const [visible, setVisible] = useState(() => {
    try {
      return window.localStorage.getItem(`vibe-vibe-intro-${id}`) !== '1'
    } catch {
      return true
    }
  })

  if (!visible) return null

  return (
    <div className="view-intro">
      <div className="view-intro-body">{children}</div>
      <button
        type="button"
        className="view-intro-dismiss"
        onClick={() => {
          try {
            window.localStorage.setItem(`vibe-vibe-intro-${id}`, '1')
          } catch {
            // ignore
          }
          setVisible(false)
        }}
        aria-label="dismiss intro"
      >
        &times;
      </button>
    </div>
  )
}

function Radar({ venture }: { venture: Venture }) {
  const axes = [
    ['utility', venture.tokenReadiness.utility],
    ['traction', venture.tokenReadiness.traction],
    ['governance', venture.tokenReadiness.governance],
    ['contribution', venture.tokenReadiness.contribution],
    ['trust', venture.tokenReadiness.trust],
    ['treasury', venture.tokenReadiness.treasury],
  ] as const
  const center = 150
  const radius = 104
  const points = axes.map(([, value], index) => {
    const angle = -Math.PI / 2 + (index / axes.length) * Math.PI * 2
    const scaled = (value / 100) * radius
    return `${center + Math.cos(angle) * scaled},${center + Math.sin(angle) * scaled}`
  })

  return (
    <svg viewBox="0 0 300 300" className="radar-chart" aria-label="token readiness radar">
      {[0.2, 0.4, 0.6, 0.8, 1].map((ring) => (
        <circle key={ring} cx={center} cy={center} r={radius * ring} className="radar-ring" />
      ))}
      {axes.map(([label], index) => {
        const angle = -Math.PI / 2 + (index / axes.length) * Math.PI * 2
        const x = center + Math.cos(angle) * radius
        const y = center + Math.sin(angle) * radius
        const labelX = center + Math.cos(angle) * (radius + 24)
        const labelY = center + Math.sin(angle) * (radius + 24)
        return (
          <g key={label}>
            <line x1={center} y1={center} x2={x} y2={y} className="radar-axis" />
            <text x={labelX} y={labelY} className="radar-label" textAnchor="middle">
              {label}
            </text>
          </g>
        )
      })}
      <polygon points={points.join(' ')} className="radar-area" />
      {points.map((point, index) => {
        const [cx, cy] = point.split(',')
        return <circle key={axes[index][0]} cx={cx} cy={cy} r="4" className="radar-point" />
      })}
    </svg>
  )
}

function Network({
  selectedVentureId,
  onSelectVenture,
}: {
  selectedVentureId: string
  onSelectVenture: (ventureId: string) => void
}) {
  const xByType: Record<string, number> = { batch: 110, founder: 280, venture: 520, asset: 790, failure: 1020, application: 1020 }
  const groups = new Map<string, DashboardData['network']['nodes']>()
  for (const node of data.network.nodes) {
    const bucket = groups.get(node.type) ?? []
    bucket.push(node)
    groups.set(node.type, bucket)
  }
  const positions = new Map<string, { x: number; y: number }>()
  for (const [type, nodes] of groups) {
    nodes.forEach((node, index) => positions.set(node.id, { x: xByType[type] ?? 110, y: 90 + index * 110 }))
  }

  return (
    <div className="graph-view">
      <svg viewBox="0 0 1160 620" className="graph-canvas">
        {data.network.edges.map((edge) => {
          const source = positions.get(edge.source)
          const target = positions.get(edge.target)
          if (!source || !target) return null
          return <line key={edge.id} x1={source.x} y1={source.y} x2={target.x} y2={target.y} className="graph-edge" />
        })}
        {data.network.nodes.map((node) => {
          const position = positions.get(node.id)
          if (!position) return null
          const selected = node.id === `venture:${selectedVentureId}`
          const radius = node.type === 'batch' ? 28 : node.type === 'venture' ? 20 : node.type === 'founder' ? 16 : 12
          return (
            <g
              key={node.id}
              className={`graph-node graph-node-${node.type}${selected ? ' selected' : ''}`}
              transform={`translate(${position.x}, ${position.y})`}
              onClick={() => {
                if (node.type === 'venture') onSelectVenture(node.id.replace('venture:', ''))
              }}
            >
              <circle r={radius} />
              <text y={radius + 18} textAnchor="middle">{node.label}</text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function App() {
  const [activeCommand, setActiveCommand] = useState<NavCommand>('batches')
  const [selectedVentureId, setSelectedVentureId] = useState(data.ventures[0]?.venture_id ?? '')
  const [theme, setTheme] = useState<AppTheme>(initialTheme)
  const [toast, setToast] = useState<{ message: string; tone: 'good' | 'warn' | 'info' } | null>(null)
  const [busyAction, setBusyAction] = useState<string | null>(null)

  const showToast = useCallback((message: string, tone: 'good' | 'warn' | 'info' = 'info') => {
    setToast({ message, tone })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const handleAdmissionsReview = useCallback(async (applicationId: string, decision: string) => {
    const key = `${applicationId}:${decision}`
    setBusyAction(key)
    try {
      await api.admissionsReview({ application_id: applicationId, decision })
      showToast(`${applicationId} → ${decision}`, 'good')
    } catch (err) {
      showToast(`Failed: ${err instanceof Error ? err.message : String(err)}`, 'warn')
    } finally {
      setBusyAction(null)
    }
  }, [showToast])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      window.localStorage.setItem('vibe-vibe-theme', theme)
    } catch {
      // ignore
    }
  }, [theme])

  const selectedVenture = data.ventures.find((venture) => venture.venture_id === selectedVentureId) ?? data.ventures[0]
  const queueEntries = Object.entries(data.state.queues)
  const metrics = data.latestTick.metrics

  const contentByView: Record<NavCommand, React.ReactNode> = {
    batches: (
      <div className="view-stack">
        <ViewIntro id="batches">Batch command surface. Keep attention on venture proof, queue pressure, and who deserves the next unit of operator energy.</ViewIntro>
        <section className="hero-panel">
          <div>
            <span className="eyebrow">current batch</span>
            <h1>Vibe-coded startups run as a data-visible collective.</h1>
            <p>Mirror the Autoresearch shell, but make cohort health, proof capture, contribution, and launch readiness the main objects.</p>
            <div className="chip-row">
              {queueEntries.map(([name, items]) => (
                <span key={name} className="data-chip">{name} {Array.isArray(items) ? items.length : 0}</span>
              ))}
            </div>
          </div>
          <div className="hero-metrics">
            <div className="metric-card"><span className="metric-value">{data.queueSnapshot.active_portfolio_count}</span><span className="metric-label">active ventures</span></div>
            <div className="metric-card metric-good"><span className="metric-value">{data.queueSnapshot.capital_ready_count}</span><span className="metric-label">capital ready</span></div>
            <div className="metric-card metric-warn"><span className="metric-value">{data.queueSnapshot.pending_applications}</span><span className="metric-label">pending apps</span></div>
            <div className="metric-card"><span className="metric-value">{data.feed.length}</span><span className="metric-label">proof events</span></div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>cohort heatmap</h2><span className="panel-kicker">proof before price</span></div>
          <div className="heatmap">
            <div className="heatmap-header">
              <span className="heatmap-venture-label">venture</span>
              <span className="heatmap-col-label">utility</span>
              <span className="heatmap-col-label">traction</span>
              <span className="heatmap-col-label">governance</span>
              <span className="heatmap-col-label">contribution</span>
              <span className="heatmap-col-label">trust</span>
              <span className="heatmap-col-label">treasury</span>
            </div>
            {data.ventures.map((venture) => (
              <button key={venture.venture_id} type="button" className={`heatmap-row${venture.venture_id === selectedVenture.venture_id ? ' selected' : ''}`} onClick={() => setSelectedVentureId(venture.venture_id)}>
                <span className="heatmap-venture-label">{venture.venture_id}</span>
                {(['utility', 'traction', 'governance', 'contribution', 'trust', 'treasury'] as const).map((key) => (
                  <span key={key} className="heatmap-cell" style={{ ['--heat' as string]: `${venture.tokenReadiness[key] / 100}` }}>{venture.tokenReadiness[key]}</span>
                ))}
              </button>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>priority ventures</h2></div>
          <div className="venture-grid">
            {data.ventures.map((venture) => (
              <button key={venture.venture_id} type="button" className={`venture-card${venture.venture_id === selectedVenture.venture_id ? ' selected' : ''}`} onClick={() => setSelectedVentureId(venture.venture_id)}>
                <div className="venture-card-top"><span className={`tone-dot tone-${venture.trust_review_status === 'green' ? 'good' : 'warn'}`} /><span className="venture-card-id">{venture.venture_id}</span><span className="venture-card-stage">{venture.stage}</span></div>
                <h3>{venture.label}</h3>
                <div className="venture-card-metrics"><span>rev {formatCurrency(venture.weekly_revenue)}</span><span>conv {venture.customer_conversations_this_week}</span><span>pipe {formatCurrency(venture.open_pipeline_value)}</span></div>
                <div className="chip-row"><span className="data-chip">{venture.bottleneck}</span><span className="data-chip">readiness {venture.tokenReadiness.overall}</span><span className="data-chip">automation {formatPercent(venture.automation_coverage)}</span></div>
              </button>
            ))}
          </div>
        </section>
      </div>
    ),
    ventures: (
      <div className="view-stack">
        <ViewIntro id="ventures">Venture view is the direct operating board: shipping, pipeline, readiness, and what must happen next.</ViewIntro>
        <section className="panel">
          <div className="panel-header"><h2>venture board</h2></div>
          <div className="venture-grid">
            {data.ventures.map((venture) => (
              <button key={venture.venture_id} type="button" className={`venture-card${venture.venture_id === selectedVenture.venture_id ? ' selected' : ''}`} onClick={() => setSelectedVentureId(venture.venture_id)}>
                <div className="venture-card-top"><span className={`tone-dot tone-${venture.trust_review_status === 'green' ? 'good' : 'warn'}`} /><span className="venture-card-id">{venture.venture_id}</span><span className="venture-card-stage">{venture.stage}</span></div>
                <h3>{venture.label}</h3>
                <div className="chip-row"><span className="data-chip">{venture.execution?.next_action ?? venture.bottleneck}</span><span className="data-chip">revenue {formatCurrency(venture.weekly_revenue)}</span><span className="data-chip">pipeline {formatCurrency(venture.open_pipeline_value)}</span></div>
              </button>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>{selectedVenture.venture_id} timeline</h2></div>
          <div className="timeline">
            {selectedVenture.timeline.map((item) => (
              <div key={item.id} className="timeline-item">
                <div className={`timeline-lane tone-${item.tone}`} />
                <div className="timeline-body">
                  <div className="timeline-top"><span className="timeline-title">{item.title}</span><span className="timeline-time">{shortAge(item.createdAt)}</span></div>
                  <div className="timeline-meta"><span className="data-chip">{item.lane}</span><span>{item.detail || 'no detail'}</span></div>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    ),
    proof: (
      <div className="view-stack">
        <ViewIntro id="proof">Proof view collects the evidence that matters: conversations, doctrine, validation, and investor-facing readiness.</ViewIntro>
        <section className="panel">
          <div className="panel-header"><h2>proof timeline</h2><span className="panel-kicker">{selectedVenture.venture_id}</span></div>
          <div className="timeline">
            {selectedVenture.timeline.map((item) => (
              <div key={item.id} className="timeline-item">
                <div className={`timeline-lane tone-${item.tone}`} />
                <div className="timeline-body">
                  <div className="timeline-top"><span className="timeline-title">{item.title}</span><span className="timeline-time">{shortAge(item.createdAt)}</span></div>
                  <div className="timeline-meta"><span className="data-chip">{item.lane}</span><span>{item.detail || 'no detail'}</span></div>
                </div>
              </div>
            ))}
          </div>
        </section>
        <div className="three-up-grid">
          <section className="panel"><div className="panel-header"><h3>customer signals</h3></div><div className="stack-list">{data.customerSnapshot.customer_signal_packets.map((packet) => <div key={packet.venture_id} className="stack-card"><strong>{packet.venture_id}</strong><span>{packet.conversation_count} conversations</span><span>{packet.top_objections.join(', ') || 'no objections logged'}</span></div>)}</div></section>
          <section className="panel"><div className="panel-header"><h3>doctrine</h3></div><div className="stack-list">{data.learningSnapshot.doctrine_packets.map((packet) => <div key={packet.venture_id} className="stack-card"><strong>{packet.venture_id}</strong><span>{packet.lesson}</span><span>{packet.doctrine_claim}</span></div>)}</div></section>
          <section className="panel"><div className="panel-header"><h3>capital proof</h3></div><div className="stack-list">{data.trustSnapshot.capital_packets.map((packet) => <div key={packet.venture_id} className="stack-card"><strong>{packet.venture_id}</strong><span>{packet.capital_readiness ? 'capital ready' : 'not ready'}</span><span>{packet.capital_tasks.join(' · ')}</span></div>)}</div></section>
        </div>
      </div>
    ),
    apply: (
      <div className="view-stack">
        <ViewIntro id="apply">Applications are handled like operating packets, not essay submissions. The first-week plan matters more than pitch theatrics.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>applications</h2><span className="panel-kicker">{data.scout.pending_count} pending</span></div><div className="stack-list">{data.scout.applications.map((application) => <div key={application.application_id} className="stack-card"><div className="stack-card-top"><strong>{application.label}</strong><span className="data-chip">{application.status}</span></div><span>{application.thesis_summary}</span><span>founder {application.founder_label} · score {application.incubator_compound_score}</span><div className="chip-row">{application.first_week_plan.map((step) => <span key={step} className="data-chip">{step}</span>)}</div>{application.status === 'pending' && (<div className="action-row">{(['invite', 'waitlist', 'reject'] as const).map((decision) => { const key = `${application.application_id}:${decision}`; return (<button key={decision} type="button" className={`action-btn action-btn-${decision}`} disabled={busyAction === key} onClick={() => handleAdmissionsReview(application.application_id, decision)}>{busyAction === key ? '...' : decision}</button>)})}</div>)}</div>)}</div></section>
      </div>
    ),
    operator: (
      <div className="view-stack">
        <ViewIntro id="operator">Operator mode keeps the batch honest: system checks, queue shape, and the task packets the loop is producing right now.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>system checks</h2></div><div className="status-checks">{[
          { label: 'trust', value: data.trustSnapshot.blocking_trust_count === 0 ? 'clear' : 'blocking', ok: data.trustSnapshot.blocking_trust_count === 0 },
          { label: 'admissions', value: `${data.scout.pending_count} pending`, ok: data.scout.pending_count <= 3 },
          { label: 'autoloop confidence', value: metrics.verdict_confidence.toFixed(4), ok: metrics.verdict_confidence >= 0.6 },
          { label: 'knowledge capture', value: metrics.ops_knowledge_capture_score.toFixed(4), ok: metrics.ops_knowledge_capture_score >= 0.7 },
        ].map((check) => <div key={check.label} className="status-check"><span className={`status-check-dot ${check.ok ? 'status-check-ok' : 'status-check-warn'}`} /><span className="status-check-label">{check.label}</span><span className="status-check-value">{check.value}</span></div>)}</div></section>
        <section className="panel"><div className="panel-header"><h2>operator packets</h2></div><div className="stack-list">{data.ventures.map((venture) => <div key={venture.venture_id} className="stack-card"><div className="stack-card-top"><strong>{venture.venture_id}</strong><span className="data-chip">{venture.taskPacket?.next_action ?? venture.execution?.next_action ?? venture.bottleneck}</span></div><span>{venture.label}</span><div className="chip-row">{(venture.taskPacket?.required_tasks ?? []).map((task) => <span key={task} className="data-chip">{task}</span>)}</div></div>)}</div></section>
      </div>
    ),
    network: (
      <div className="view-stack">
        <ViewIntro id="network">Network view mirrors the Collective graph pattern, but maps it onto founders, ventures, reusable assets, failures, and the admissions pipeline.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>collective network</h2></div><Network selectedVentureId={selectedVenture.venture_id} onSelectVenture={setSelectedVentureId} /></section>
      </div>
    ),
    genesis: (
      <div className="view-stack">
        <ViewIntro id="genesis">Genesis is a readiness surface, not a speculation surface. Utility, trust, contribution, and treasury posture must be visible before launch routing exists.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>genesis readiness</h2><span className="panel-kicker">{selectedVenture.venture_id}</span></div><div className="genesis-grid"><Radar venture={selectedVenture} /><div className="stack-list"><div className="stack-card"><strong>SPARK stack</strong><span>{data.genesisSystem.spark.baseToken}{' -> '}{data.genesisSystem.spark.governanceToken}</span><span>treasury {data.genesisSystem.spark.treasuryFlow}</span><span>launch rail {data.product.externalLaunchRail}</span></div><div className="stack-card"><strong>genesis phases</strong><div className="chip-row">{data.genesisSystem.phases.map((phase) => <span key={phase} className="data-chip">{phase}</span>)}</div></div><div className="stack-card"><strong>guardrails</strong>{data.genesisSystem.rules.map((rule) => <span key={rule}>{rule}</span>)}</div></div></div></section>
      </div>
    ),
    feed: (
      <div className="view-stack">
        <ViewIntro id="feed">The feed is public-proof native: the batch should feel alive through actions, decisions, customer contact, and learning packets.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>proof feed</h2><span className="panel-kicker">latest 20 events</span></div><div className="feed-list">{data.feed.map((entry: FeedEntry) => <div key={`${entry.ventureId}:${entry.id}`} className="feed-item"><span className={`feed-dot tone-${entry.tone}`} /><div className="feed-body"><div className="feed-top"><strong>{entry.title}</strong><span>{shortAge(entry.createdAt)}</span></div><span>{entry.ventureLabel}</span><span>{entry.detail}</span></div></div>)}</div></section>
      </div>
    ),
    autoloop: (
      <div className="view-stack">
        <ViewIntro id="autoloop">The batch loop should be visible as a real operating system, not a hidden daemon. Show the pulse, the queue, and the current recommendation pressure.</ViewIntro>
        <section className="hero-panel"><div><span className="eyebrow">batch autoloop</span><h1>One loop. visible pressure. proof-first routing.</h1><p>The loop is prioritizing {data.latestTick.priority_ventures[0]?.venture_id ?? 'n/a'} and currently flags {metrics.bottleneck} as the main batch bottleneck.</p></div><div className="hero-metrics"><div className="metric-card metric-good"><span className="metric-value">{metrics.incubator_compound_score.toFixed(4)}</span><span className="metric-label">compound</span></div><div className="metric-card metric-warn"><span className="metric-value">{metrics.ops_review_hygiene_score.toFixed(4)}</span><span className="metric-label">review hygiene</span></div><div className="metric-card metric-good"><span className="metric-value">{metrics.ops_validation_velocity_score.toFixed(4)}</span><span className="metric-label">validation</span></div><div className="metric-card metric-good"><span className="metric-value">{metrics.ops_trust_hygiene_score.toFixed(4)}</span><span className="metric-label">trust</span></div></div></section>
        <div className="two-up-grid"><section className="panel"><div className="panel-header"><h3>priority ventures</h3></div><div className="stack-list">{data.latestTick.priority_ventures.map((venture) => <div key={venture.venture_id} className="stack-card"><strong>{venture.venture_id}</strong><span>{venture.label}</span><span>{venture.next_action}</span></div>)}</div></section><section className="panel"><div className="panel-header"><h3>office hours packets</h3></div><div className="stack-list">{data.officeHoursPackets.map((packet) => <div key={packet.venture_id} className="stack-card"><strong>{packet.venture_id}</strong><span>{packet.commitment}</span><div className="chip-row">{packet.agenda.map((item) => <span key={item} className="data-chip">{item}</span>)}</div></div>)}</div></section></div>
      </div>
    ),
    curriculum: (
      <div className="view-stack">
        <ViewIntro id="curriculum">Education in Vibe Vibe is stage-based. Every module should terminate in a concrete founder output, not passive content consumption.</ViewIntro>
        <div className="three-up-grid">{data.curriculum.map((module) => <section key={module.id} className="panel"><div className="panel-header"><h3>{module.title}</h3></div><p>{module.description}</p><div className="chip-row">{module.outputs.map((output) => <span key={output} className="data-chip">{output}</span>)}</div></section>)}</div>
      </div>
    ),
    ops: (
      <div className="view-stack">
        <ViewIntro id="ops">Ops is the raw packet surface for the operator: current tasks, current decisions, and what the machine is emitting right now.</ViewIntro>
        <section className="panel"><div className="panel-header"><h2>decision packets</h2></div><div className="stack-list">{data.decisionPackets.map((packet) => <div key={packet.venture_id} className="stack-card"><strong>{packet.venture_id}</strong><span>{packet.decision}</span><span>{packet.required_next_step}</span></div>)}</div></section>
      </div>
    ),
  }

  return (
    <div className="terminal-app">
      <nav className="activity-bar" aria-label="Vibe Vibe navigation">
        <div className="activity-brand" aria-label="Vibe Vibe"><span className="activity-brand-mark" aria-hidden="true"><span /><span /><span /><span /></span><span className="activity-brand-label">vibe vibe</span></div>
        <div className="activity-nav-items" role="tablist" aria-label="main navigation">
          {NAV_ITEMS.map((item) => (
            <button key={item.command} type="button" role="tab" className={`activity-bar-item${activeCommand === item.command ? ' active' : ''}`} onClick={() => setActiveCommand(item.command)} aria-selected={activeCommand === item.command}>{item.label}</button>
          ))}
        </div>
        <button type="button" className="theme-toggle" onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? 'light mode' : 'dark mode'}</button>
      </nav>
      <main className="main-surface">{contentByView[activeCommand]}</main>
      <aside className="detail-sidebar">
        <SidebarSection title="Batch" defaultOpen>
          <div className="sidebar-stack">
            <span><strong>mode</strong> {data.product.operatorMode}</span>
            <span><strong>style</strong> {data.product.microBatchStyle}</span>
            <span><strong>updated</strong> {shortAge(data.generatedAt)}</span>
            <div className="chip-row">{queueEntries.map(([name, items]) => <span key={name} className="data-chip">{name} {Array.isArray(items) ? items.length : 0}</span>)}</div>
          </div>
        </SidebarSection>
        <SidebarSection title="Selected Venture" defaultOpen>
          <div className="sidebar-stack">
            <strong>{selectedVenture.venture_id}</strong>
            <span>{selectedVenture.label}</span>
            <span>stage {selectedVenture.stage}</span>
            <span>bottleneck {selectedVenture.bottleneck}</span>
            <div className="chip-row"><span className="data-chip">readiness {selectedVenture.tokenReadiness.overall}</span><span className="data-chip">trust {selectedVenture.tokenReadiness.trust}</span><span className="data-chip">treasury {selectedVenture.tokenReadiness.treasury}</span></div>
          </div>
        </SidebarSection>
        <SidebarSection title="Queue Focus" defaultOpen>
          <div className="sidebar-stack">{data.latestTick.priority_ventures.map((venture) => <div key={venture.venture_id} className="sidebar-mini-card"><strong>{venture.venture_id}</strong><span>{venture.next_action}</span></div>)}</div>
        </SidebarSection>
        <SidebarSection title="Autoloop">
          <div className="sidebar-stack">
            <span><strong>compound</strong> {metrics.incubator_compound_score.toFixed(4)}</span>
            <span><strong>confidence</strong> {metrics.verdict_confidence.toFixed(4)}</span>
            <span><strong>bottleneck</strong> {metrics.bottleneck}</span>
            <span><strong>task packets</strong> {data.queueSnapshot.venture_task_count}</span>
          </div>
        </SidebarSection>
        <SidebarSection title="Genesis">
          <div className="sidebar-stack">
            <span><strong>treasury</strong> {data.product.treasuryAssets.join(' / ')}</span>
            <span><strong>rail</strong> {data.product.externalLaunchRail}</span>
            <div className="chip-row">{data.genesisSystem.phases.map((phase) => <span key={phase} className="data-chip">{phase}</span>)}</div>
          </div>
        </SidebarSection>
      </aside>
      <div className="status-bar" role="status">
        <span className="status-bar-item">batch 00 | {data.ventures.length}/{data.product.portfolioCap} ventures</span>
        <span className="status-bar-item">autoloop {metrics.bottleneck}</span>
        <span className="status-bar-item">compound {metrics.incubator_compound_score.toFixed(4)}</span>
        <span className="status-bar-item">queue {data.queueSnapshot.venture_task_count} tasks</span>
        <span className="status-bar-item status-bar-right">selected {selectedVenture.venture_id} | readiness {selectedVenture.tokenReadiness.overall}</span>
      </div>
      {toast && <div className={`toast toast-${toast.tone}`} role="alert">{toast.message}</div>}
    </div>
  )
}

export default App
