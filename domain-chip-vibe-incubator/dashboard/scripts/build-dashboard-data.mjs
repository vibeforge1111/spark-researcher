import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const dashboardRoot = path.resolve(__dirname, '..')
const chipRoot = path.resolve(dashboardRoot, '..')
const artifactsRoot = path.join(chipRoot, 'artifacts', 'incubator_os')
const outputPath = path.join(dashboardRoot, 'src', 'generated', 'incubator-dashboard.json')

async function readJson(name) {
  const raw = await readFile(path.join(artifactsRoot, name), 'utf8')
  return JSON.parse(raw)
}

async function readJsonl(name) {
  try {
    const raw = await readFile(path.join(artifactsRoot, name), 'utf8')
    return raw
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => JSON.parse(line))
  } catch {
    return []
  }
}

function scoreTrust(status, blocking) {
  if (blocking) return 20
  if (status === 'green') return 88
  if (status === 'yellow') return 60
  if (status === 'red') return 25
  return 50
}

function clampScore(value) {
  return Math.max(0, Math.min(100, Math.round(value)))
}

function buildTokenReadiness(venture, trustInfo, learningInfo, executionInfo) {
  const utility = clampScore(
    (venture.active_users ?? 0) * 14 +
      (venture.automation_coverage ?? 0) * 24 +
      (venture.stage === 'validation' ? 22 : 10),
  )
  const traction = clampScore(
    (venture.customer_conversations_this_week ?? 0) * 8 +
      (venture.paid_signals_this_week ?? 0) * 14 +
      (venture.weekly_revenue ?? 0) / 18 +
      (venture.open_pipeline_count ?? 0) * 12,
  )
  const governance = clampScore(
    (venture.doctrine_ready ? 44 : 20) +
      (venture.promoted_playbook_count ?? 0) * 18 +
      (learningInfo?.reusable_asset_count ?? 0) * 12,
  )
  const contribution = clampScore(
    (venture.shared_asset_count ?? 0) * 24 +
      (venture.customer_signal_count ?? 0) * 12 +
      (learningInfo?.retrospective_count ?? 0) * 10 +
      (executionInfo?.open_build_request_count ?? 0) * 8,
  )
  const trust = scoreTrust(trustInfo?.trust_status ?? venture.trust_review_status, Boolean(trustInfo?.blocking))
  const treasury = clampScore(
    (venture.capital_readiness ? 50 : 24) +
      ((venture.ready_data_room_count ?? 0) / Math.max(1, venture.total_data_room_count ?? 1)) * 24 +
      (venture.investor_target_count ?? 0) * 8,
  )
  const overall = clampScore((utility + traction + governance + contribution + trust + treasury) / 6)

  return {
    utility,
    traction,
    governance,
    contribution,
    trust,
    treasury,
    overall,
  }
}

function eventSummary(event) {
  const time = event.created_at ?? event.createdAt ?? null
  return { ...event, createdAt: time }
}

function buildTimeline(ventureId, eventGroups) {
  const entries = []
  for (const [type, sourceEvents] of eventGroups) {
    for (const event of sourceEvents.filter((item) => item.venture_id === ventureId)) {
      let title = type
      let lane = 'ops'
      let detail = ''
      let tone = 'info'
      if (type === 'weekly_update') {
        title = 'Weekly update captured'
        lane = 'proof'
        detail = event.note ?? 'Founder update logged'
      } else if (type === 'review') {
        title = `Decision: ${event.decision}`
        lane = 'operator'
        detail = event.note ?? event.next_step ?? ''
        tone = event.decision === 'continue' ? 'good' : 'warn'
      } else if (type === 'experiment') {
        title = `Experiment ${event.status}`
        lane = 'build'
        detail = event.hypothesis ?? event.target_metric ?? ''
      } else if (type === 'build_request') {
        title = `Build request: ${event.title}`
        lane = 'build'
        detail = `${event.status} · ${event.kind}`
      } else if (type === 'customer_conversation') {
        title = `Customer conversation with ${event.customer_label}`
        lane = 'validation'
        detail = event.objection ?? event.next_step ?? ''
        tone = event.outcome === 'positive_follow_up' ? 'good' : 'info'
      } else if (type === 'pipeline_opportunity') {
        title = `Pipeline ${event.stage}`
        lane = 'validation'
        detail = `${event.customer_label} · ${event.value ?? 0}`
      } else if (type === 'trust_review') {
        title = `Trust review: ${event.status}`
        lane = 'trust'
        detail = event.risk_area ?? event.scope ?? ''
        tone = event.status === 'green' ? 'good' : 'warn'
      } else if (type === 'data_room_item') {
        title = `Data room: ${event.label}`
        lane = 'capital'
        detail = `${event.category} · ${event.status}`
      } else if (type === 'investor_target') {
        title = `Investor target: ${event.investor_label}`
        lane = 'capital'
        detail = `${event.stage} · ${event.status}`
      } else if (type === 'retrospective') {
        title = `Retrospective: ${event.outcome}`
        lane = 'learning'
        detail = event.lesson ?? event.next_step ?? ''
        tone = event.outcome === 'win' ? 'good' : event.outcome === 'mixed' ? 'warn' : 'info'
      } else if (type === 'kpi_snapshot') {
        title = 'KPI snapshot'
        lane = 'proof'
        detail = `rev ${event.weekly_revenue ?? 0} · users ${event.active_users ?? 0}`
      }
      entries.push({
        id: `${type}:${event.created_at ?? event.createdAt ?? Math.random().toString(36).slice(2)}`,
        title,
        lane,
        detail,
        tone,
        createdAt: event.created_at ?? event.createdAt ?? null,
      })
    }
  }
  return entries.sort((a, b) => (b.createdAt ?? '').localeCompare(a.createdAt ?? ''))
}

function buildFeed(ventures) {
  return ventures
    .flatMap((venture) =>
      venture.timeline.slice(0, 6).map((entry) => ({
        ...entry,
        ventureId: venture.venture_id,
        ventureLabel: venture.label,
      })),
    )
    .sort((a, b) => (b.createdAt ?? '').localeCompare(a.createdAt ?? ''))
    .slice(0, 20)
}

function buildNetwork(state, learningSnapshot, scoutSnapshot) {
  const nodes = [
    { id: 'batch:current', label: 'Current Batch', type: 'batch', score: state.ventures.length },
  ]
  const edges = []

  for (const founder of state.founders) {
    nodes.push({
      id: `founder:${founder.founder_id}`,
      label: founder.label,
      type: 'founder',
      score: founder.venture_ids.length || 1,
    })
    edges.push({
      id: `edge:batch-founder:${founder.founder_id}`,
      source: 'batch:current',
      target: `founder:${founder.founder_id}`,
      type: 'member',
    })
  }

  for (const venture of state.ventures) {
    nodes.push({
      id: `venture:${venture.venture_id}`,
      label: venture.venture_id,
      type: 'venture',
      score: (venture.weekly_revenue ?? 0) / 50 + (venture.customer_conversations_this_week ?? 0) + 1,
    })
    edges.push({
      id: `edge:batch-venture:${venture.venture_id}`,
      source: 'batch:current',
      target: `venture:${venture.venture_id}`,
      type: 'batch_link',
    })
  }

  for (const founder of state.founders) {
    for (const ventureId of founder.venture_ids) {
      edges.push({
        id: `edge:founder-venture:${founder.founder_id}:${ventureId}`,
        source: `founder:${founder.founder_id}`,
        target: `venture:${ventureId}`,
        type: 'owns',
      })
    }
  }

  for (const asset of learningSnapshot.reusable_assets ?? []) {
    nodes.push({
      id: `asset:${asset.asset_id}`,
      label: asset.label,
      type: 'asset',
      score: asset.reused_by_count ?? 1,
    })
    edges.push({
      id: `edge:venture-asset:${asset.venture_id}:${asset.asset_id}`,
      source: `venture:${asset.venture_id}`,
      target: `asset:${asset.asset_id}`,
      type: 'reusable_asset',
    })
  }

  for (const failure of learningSnapshot.repeated_failures ?? []) {
    nodes.push({
      id: `failure:${failure.failure_mode}`,
      label: failure.failure_mode,
      type: 'failure',
      score: failure.count ?? 1,
    })
    for (const ventureId of failure.ventures ?? []) {
      edges.push({
        id: `edge:venture-failure:${ventureId}:${failure.failure_mode}`,
        source: `venture:${ventureId}`,
        target: `failure:${failure.failure_mode}`,
        type: 'failure_mode',
      })
    }
  }

  for (const app of scoutSnapshot.pending_packets ?? []) {
    nodes.push({
      id: `application:${app.application_id}`,
      label: app.label,
      type: 'application',
      score: app.incubator_compound_score ?? 1,
    })
    edges.push({
      id: `edge:batch-application:${app.application_id}`,
      source: 'batch:current',
      target: `application:${app.application_id}`,
      type: 'pipeline',
    })
  }

  return { nodes, edges }
}

function buildCurriculum() {
  return [
    {
      id: 'proof',
      title: 'Proof Sprint',
      description: 'Ship a public artifact, frame the pain clearly, and capture the first user signal.',
      outputs: ['Demo page', 'First proof post', 'User target definition'],
    },
    {
      id: 'validation',
      title: 'Validation Loop',
      description: 'Run calls, test willingness to pay, and convert objections into product tasks.',
      outputs: ['Conversation log', 'Pipeline board', 'Paid signal test'],
    },
    {
      id: 'genesis',
      title: 'Genesis Readiness',
      description: 'Only move toward public token rails when utility, governance, and trust signals are real.',
      outputs: ['Utility map', 'Token readiness radar', 'Launch eligibility memo'],
    },
  ]
}

async function main() {
  const [
    state,
    latestTick,
    queueSnapshot,
    executionSnapshot,
    customerSnapshot,
    trustSnapshot,
    learningSnapshot,
    scoutSnapshot,
    ventureTaskPackets,
    officeHoursPackets,
    decisionPackets,
  ] = await Promise.all([
    readJson('state.json'),
    readJson('latest_tick.json'),
    readJson('queue_snapshot.json'),
    readJson('execution_snapshot.json'),
    readJson('customer_gtm_snapshot.json'),
    readJson('trust_capital_snapshot.json'),
    readJson('portfolio_learning_snapshot.json'),
    readJson('scout_snapshot.json'),
    readJson('venture_task_packets.json'),
    readJson('office_hours_packets.json'),
    readJson('decision_packets.json'),
  ])

  const [
    weeklyUpdates,
    reviews,
    experiments,
    buildRequests,
    customerConversations,
    pipelineOpportunities,
    trustReviews,
    dataRoomItems,
    investorTargets,
    retrospectives,
    kpiSnapshots,
  ] = await Promise.all([
    readJsonl('weekly_updates.jsonl'),
    readJsonl('reviews.jsonl'),
    readJsonl('experiments.jsonl'),
    readJsonl('build_requests.jsonl'),
    readJsonl('customer_conversations.jsonl'),
    readJsonl('pipeline_opportunities.jsonl'),
    readJsonl('trust_reviews.jsonl'),
    readJsonl('data_room_items.jsonl'),
    readJsonl('investor_targets.jsonl'),
    readJsonl('portfolio_retrospectives.jsonl'),
    readJsonl('kpi_snapshots.jsonl'),
  ])

  const executionMap = new Map((executionSnapshot.ventures ?? []).map((item) => [item.venture_id, item]))
  const customerMap = new Map((customerSnapshot.ventures ?? []).map((item) => [item.venture_id, item]))
  const trustMap = new Map((trustSnapshot.ventures ?? []).map((item) => [item.venture_id, item]))
  const learningMap = new Map((learningSnapshot.ventures ?? []).map((item) => [item.venture_id, item]))
  const taskMap = new Map((ventureTaskPackets ?? []).map((item) => [item.venture_id, item]))

  const eventGroups = [
    ['weekly_update', weeklyUpdates],
    ['review', reviews],
    ['experiment', experiments],
    ['build_request', buildRequests],
    ['customer_conversation', customerConversations],
    ['pipeline_opportunity', pipelineOpportunities],
    ['trust_review', trustReviews],
    ['data_room_item', dataRoomItems],
    ['investor_target', investorTargets],
    ['retrospective', retrospectives],
    ['kpi_snapshot', kpiSnapshots],
  ]

  const ventures = (state.ventures ?? []).map((venture) => {
    const executionInfo = executionMap.get(venture.venture_id)
    const customerInfo = customerMap.get(venture.venture_id)
    const trustInfo = trustMap.get(venture.venture_id)
    const learningInfo = learningMap.get(venture.venture_id)
    const taskInfo = taskMap.get(venture.venture_id)
    const timeline = buildTimeline(venture.venture_id, eventGroups)

    return {
      ...venture,
      execution: executionInfo ?? null,
      customer: customerInfo ?? null,
      trust: trustInfo ?? null,
      learning: learningInfo ?? null,
      taskPacket: taskInfo ?? null,
      tokenReadiness: buildTokenReadiness(venture, trustInfo, learningInfo, executionInfo),
      timeline,
    }
  })

  const snapshot = {
    generatedAt: latestTick.generated_at ?? state.updated_at ?? new Date().toISOString(),
    product: {
      name: 'Vibe Vibe',
      runtimeName: state.program?.name ?? 'Vibe Incubator',
      operatorMode: state.program?.operator_mode ?? 'solo_plus_agents',
      microBatchStyle: state.program?.micro_batch_style ?? 'cohort',
      portfolioCap: state.program?.active_portfolio_cap ?? latestTick.metrics?.portfolio_cap ?? 0,
      treasuryAssets: ['ETH', 'USDT'],
      externalLaunchRail: 'uniswap_v4_hook',
    },
    latestTick,
    queueSnapshot,
    state: {
      founders: state.founders ?? [],
      queues: state.queues ?? {},
    },
    scout: scoutSnapshot,
    officeHoursPackets,
    decisionPackets,
    executionSnapshot,
    customerSnapshot,
    trustSnapshot,
    learningSnapshot,
    ventures,
    feed: buildFeed(ventures),
    network: buildNetwork(state, learningSnapshot, scoutSnapshot),
    curriculum: buildCurriculum(),
    genesisSystem: {
      spark: {
        baseToken: 'SPARK',
        governanceToken: 'veSPARK',
        treasuryFlow: 'quote_assets_only',
        projectExposure: 'support_reserve_and_claim_rights',
      },
      phases: [
        'Proof',
        'Contribution',
        'Genesis Credits',
        'Claim Rights',
        'External Launch',
      ],
      rules: [
        'Proof before price',
        'Quote-asset treasury, not project-token fee farming',
        'Contribution earns rights only when value is verified',
      ],
    },
  }

  await mkdir(path.dirname(outputPath), { recursive: true })
  await writeFile(outputPath, `${JSON.stringify(snapshot, null, 2)}\n`, 'utf8')
  process.stdout.write(`wrote ${path.relative(dashboardRoot, outputPath)}\n`)
}

main().catch((error) => {
  process.stderr.write(`${error instanceof Error ? error.stack ?? error.message : String(error)}\n`)
  process.exitCode = 1
})
