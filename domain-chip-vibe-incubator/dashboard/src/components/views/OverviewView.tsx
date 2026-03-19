import type { DashboardSnapshot, ViewId } from '@/types'
import { MetricCard } from '@/components/ui/MetricCard'
import { AlertBanner } from '@/components/ui/AlertBanner'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { StatusDot } from '@/components/ui/StatusDot'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { formatDecimal, formatScore, formatCurrency } from '@/lib/format'

interface Props {
  data: DashboardSnapshot
  onNavigate: (view: ViewId) => void
}

const trustColor = (s?: string): 'green' | 'red' | 'yellow' => s === 'green' ? 'green' : s === 'red' ? 'red' : 'yellow'

export function OverviewView({ data, onNavigate }: Props) {
  const m = data.latestTick?.metrics
  const alerts = data.latestTick?.health_alerts ?? []
  const ventures = data.ventures?.filter((v) => v.status === 'active') ?? []
  const priorities = data.latestTick?.priority_ventures ?? []

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Overview</h2>
        <p className="text-sm text-gray-500 mt-0.5">Portfolio health at a glance</p>
      </div>

      {/* Alerts */}
      <AlertBanner alerts={alerts} />

      {/* Metric row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Ventures"
          value={m?.active_portfolio_count ?? 0}
          accent={m && m.active_portfolio_count > m.portfolio_cap ? 'danger' : null}
        />
        <MetricCard
          label="Compound Score"
          value={formatDecimal(m?.incubator_compound_score)}
          accent={m && m.incubator_compound_score < 0.5 ? 'warning' : m && m.incubator_compound_score >= 0.75 ? 'success' : null}
        />
        <MetricCard
          label="Pending Apps"
          value={data.queueSnapshot?.pending_applications ?? 0}
          accent={data.queueSnapshot && data.queueSnapshot.pending_applications > 3 ? 'warning' : null}
        />
        <MetricCard
          label="Confidence"
          value={formatDecimal(m?.verdict_confidence)}
        />
      </div>

      {/* Two-column: Heatmap + Priority */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Heatmap */}
        <Card className="xl:col-span-2" padding="none">
          <div className="px-5 py-3 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900">Cohort Readiness</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Venture</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Utility</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Traction</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Gov</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Trust</th>
                  <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase">Overall</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {ventures.map((v) => (
                  <tr
                    key={v.venture_id}
                    className="hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => onNavigate('ventures')}
                  >
                    <td className="px-4 py-2.5 flex items-center gap-2">
                      <StatusDot status={trustColor(v.trust_review_status)} size="sm" />
                      <span className="font-medium text-gray-900 truncate max-w-[180px]">{v.label}</span>
                    </td>
                    <HeatCell value={v.tokenReadiness?.utility ?? 0} />
                    <HeatCell value={v.tokenReadiness?.traction ?? 0} />
                    <HeatCell value={v.tokenReadiness?.governance ?? 0} />
                    <HeatCell value={v.tokenReadiness?.trust ?? 0} />
                    <HeatCell value={v.tokenReadiness?.overall ?? 0} bold />
                  </tr>
                ))}
                {ventures.length === 0 && (
                  <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No active ventures</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Priority + Scores */}
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Priority Ventures</h3>
            <div className="space-y-2">
              {priorities.slice(0, 5).map((p) => (
                <div key={p.venture_id} className="flex items-center justify-between">
                  <span className="text-sm text-gray-700 truncate">{p.label || p.venture_id}</span>
                  {p.next_action && (
                    <Badge variant="outline" size="sm">{p.next_action}</Badge>
                  )}
                </div>
              ))}
              {priorities.length === 0 && (
                <p className="text-sm text-gray-400">No priorities</p>
              )}
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Outcome Scores</h3>
            <div className="space-y-3">
              <ProgressBar label="Revenue" value={(m?.outcome_revenue_score ?? 0) * 100} />
              <ProgressBar label="Retention" value={(m?.outcome_retention_score ?? 0) * 100} />
              <ProgressBar label="Impact" value={(m?.outcome_impact_score ?? 0) * 100} />
              <ProgressBar label="Review Quality" value={(m?.outcome_review_quality_score ?? 0) * 100} />
            </div>
          </Card>

          <Card>
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Bottleneck</h3>
            <Badge variant="warning">{m?.bottleneck ?? 'none'}</Badge>
          </Card>
        </div>
      </div>

      {/* Recent feed preview */}
      {data.feed && data.feed.length > 0 && (
        <Card padding="none">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Recent Activity</h3>
            <button
              onClick={() => onNavigate('feed')}
              className="text-xs text-primary-600 hover:text-primary-700 font-medium"
            >
              View all
            </button>
          </div>
          <div className="divide-y divide-gray-50">
            {data.feed.slice(0, 5).map((f) => (
              <div key={f.id} className="px-5 py-2.5 flex items-center gap-3">
                <StatusDot
                  status={f.tone === 'good' ? 'green' : f.tone === 'bad' ? 'red' : f.tone === 'warn' ? 'yellow' : 'gray'}
                  size="sm"
                />
                <div className="min-w-0 flex-1">
                  <span className="text-sm text-gray-700">{f.title}</span>
                  <span className="text-xs text-gray-400 ml-2">{f.ventureLabel}</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function HeatCell({ value, bold = false }: { value: number; bold?: boolean }) {
  const bg = value >= 70 ? 'bg-success-50' : value >= 40 ? 'bg-warning-50' : value > 0 ? 'bg-danger-50' : ''
  const text = value >= 70 ? 'text-success-700' : value >= 40 ? 'text-warning-700' : value > 0 ? 'text-danger-700' : 'text-gray-400'
  return (
    <td className={`px-3 py-2.5 text-center text-xs ${bg} ${text} ${bold ? 'font-semibold' : 'font-medium'}`}>
      {value > 0 ? value : '--'}
    </td>
  )
}
