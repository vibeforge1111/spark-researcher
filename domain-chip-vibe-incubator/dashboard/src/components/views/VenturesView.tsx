import { useState } from 'react'
import type { DashboardSnapshot, Venture } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { StatusDot } from '@/components/ui/StatusDot'
import { Timeline } from '@/components/ui/Timeline'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { MetricCard } from '@/components/ui/MetricCard'
import { formatCurrency, formatTrend, formatPercent, stageLabel } from '@/lib/format'

interface Props {
  data: DashboardSnapshot
}

const trustColor = (s?: string): 'green' | 'red' | 'yellow' => s === 'green' ? 'green' : s === 'red' ? 'red' : 'yellow'
const stageBadge = (stage: string) => {
  if (stage === 'archived') return 'danger'
  if (stage === 'growth' || stage === 'scale') return 'success'
  if (stage === 'validation') return 'warning'
  return 'default'
}

type DetailTab = 'timeline' | 'execution' | 'customer' | 'learning' | 'readiness'

export function VenturesView({ data }: Props) {
  const ventures = data.ventures ?? []
  const [selectedId, setSelectedId] = useState<string>(ventures[0]?.venture_id ?? '')
  const [tab, setTab] = useState<DetailTab>('timeline')
  const selected = ventures.find((v) => v.venture_id === selectedId) ?? ventures[0]

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Ventures</h2>
        <p className="text-sm text-gray-500 mt-0.5">{ventures.length} total, {ventures.filter(v => v.status === 'active').length} active</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[360px_1fr] gap-6">
        {/* Venture list */}
        <Card padding="none" className="overflow-hidden">
          <div className="divide-y divide-gray-50 max-h-[calc(100vh-180px)] overflow-y-auto">
            {ventures.map((v) => (
              <button
                key={v.venture_id}
                onClick={() => { setSelectedId(v.venture_id); setTab('timeline') }}
                className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${
                  selectedId === v.venture_id ? 'bg-primary-50 border-l-2 border-l-primary-500' : ''
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <StatusDot status={trustColor(v.trust_review_status)} size="sm" />
                  <span className="text-sm font-medium text-gray-900 truncate">{v.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={stageBadge(v.stage)} size="sm">{stageLabel(v.stage)}</Badge>
                  {v.weekly_revenue > 0 && (
                    <span className="text-xs text-gray-500">{formatCurrency(v.weekly_revenue)}/wk</span>
                  )}
                </div>
              </button>
            ))}
            {ventures.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-400 text-sm">No ventures</div>
            )}
          </div>
        </Card>

        {/* Detail panel */}
        {selected && (
          <div className="space-y-4">
            {/* Header */}
            <Card>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-base font-semibold text-gray-900">{selected.label}</h3>
                  <p className="text-sm text-gray-500">{selected.venture_id}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusDot status={trustColor(selected.trust_review_status)} />
                  <Badge variant={stageBadge(selected.stage)}>{stageLabel(selected.stage)}</Badge>
                </div>
              </div>

              {/* Key metrics */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <MetricCard
                  label="Revenue"
                  value={formatCurrency(selected.weekly_revenue)}
                  trend={selected.revenue_trend != null ? (selected.revenue_trend > 0 ? 'up' : selected.revenue_trend < 0 ? 'down' : 'flat') : null}
                  trendValue={selected.revenue_trend != null ? formatTrend(selected.revenue_trend) : undefined}
                />
                <MetricCard label="Active Users" value={selected.active_users ?? 0} />
                <MetricCard label="Pipeline" value={formatCurrency(selected.open_pipeline_value)} />
                <MetricCard label="Automation" value={formatPercent(selected.automation_coverage)} />
              </div>
            </Card>

            {/* Tabs */}
            <div className="flex gap-1 border-b border-gray-200">
              {(['timeline', 'execution', 'customer', 'learning', 'readiness'] as DetailTab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
                    tab === t
                      ? 'border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <Card>
              {tab === 'timeline' && (
                <Timeline entries={selected.timeline ?? []} maxItems={20} />
              )}
              {tab === 'execution' && (
                <div className="space-y-3">
                  {selected.execution ? (
                    <>
                      <div>
                        <p className="text-xs text-gray-500 uppercase font-medium">Next Action</p>
                        <p className="text-sm text-gray-900 mt-1">{selected.execution.next_action || 'None'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase font-medium">Open Build Requests</p>
                        <p className="text-sm text-gray-900 mt-1">{selected.execution.open_build_request_count}</p>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-gray-400">No execution data</p>
                  )}
                  {selected.taskPacket && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <p className="text-xs text-gray-500 uppercase font-medium mb-2">Required Tasks</p>
                      <ul className="space-y-1">
                        {selected.taskPacket.required_tasks.map((t, i) => (
                          <li key={i} className="text-sm text-gray-700 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 bg-gray-300 rounded-full shrink-0" />
                            {t}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              {tab === 'customer' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <p className="text-xs text-gray-500">Conversations/wk</p>
                      <p className="text-lg font-semibold text-gray-900">{selected.customer_conversations_this_week}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Paid Signals</p>
                      <p className="text-lg font-semibold text-gray-900">{selected.paid_signals_this_week}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Commitments</p>
                      <p className="text-lg font-semibold text-gray-900">{selected.conversations_with_commitment ?? 0}</p>
                    </div>
                  </div>
                  {selected.retention_signal != null && (
                    <ProgressBar label="Retention Signal" value={selected.retention_signal * 100} />
                  )}
                  {selected.customer?.top_objections?.length ? (
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-medium mb-1">Top Objections</p>
                      {selected.customer.top_objections.map((o, i) => (
                        <Badge key={i} variant="outline" size="sm" className="mr-1 mb-1">{o}</Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              )}
              {tab === 'learning' && (
                <div className="space-y-3">
                  {selected.learning ? (
                    <>
                      <div>
                        <p className="text-xs text-gray-500 uppercase font-medium">Lesson</p>
                        <p className="text-sm text-gray-900 mt-1">{selected.learning.lesson}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 uppercase font-medium">Doctrine Claim</p>
                        <p className="text-sm text-gray-900 mt-1">{selected.learning.doctrine_claim}</p>
                      </div>
                    </>
                  ) : (
                    <p className="text-sm text-gray-400">No learning data</p>
                  )}
                  {selected.total_reviews != null && selected.total_reviews > 0 && (
                    <ProgressBar
                      label="Evidence-Backed Reviews"
                      value={((selected.evidence_backed_reviews ?? 0) / selected.total_reviews) * 100}
                    />
                  )}
                </div>
              )}
              {tab === 'readiness' && selected.tokenReadiness && (
                <div className="space-y-3">
                  {(['utility', 'traction', 'governance', 'contribution', 'trust', 'treasury'] as const).map((k) => (
                    <ProgressBar key={k} label={k.charAt(0).toUpperCase() + k.slice(1)} value={selected.tokenReadiness[k]} />
                  ))}
                  <div className="pt-3 border-t border-gray-100">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium text-gray-700">Overall Readiness</span>
                      <span className="font-semibold text-gray-900">{Math.round(selected.tokenReadiness.overall)}%</span>
                    </div>
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
