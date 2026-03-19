import type { DashboardSnapshot } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { StatusDot } from '@/components/ui/StatusDot'
import { MetricCard } from '@/components/ui/MetricCard'

interface Props {
  data: DashboardSnapshot
}

export function OperationsView({ data }: Props) {
  const tick = data.latestTick
  const m = tick?.metrics
  const officeHours = data.officeHoursPackets ?? []
  const decisions = data.decisionPackets ?? []
  const alerts = tick?.health_alerts ?? []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Operations</h2>
        <p className="text-sm text-gray-500 mt-0.5">System health and operational queues</p>
      </div>

      {/* System checks */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Portfolio Focus"
          value={m ? `${(m.ops_portfolio_focus_score * 100).toFixed(0)}%` : '--'}
          accent={m && m.ops_portfolio_focus_score < 0.5 ? 'warning' : null}
        />
        <MetricCard
          label="Automation"
          value={m ? `${(m.ops_automation_coverage_score * 100).toFixed(0)}%` : '--'}
          accent={m && m.ops_automation_coverage_score < 0.5 ? 'warning' : null}
        />
        <MetricCard
          label="Review Hygiene"
          value={m ? `${(m.ops_review_hygiene_score * 100).toFixed(0)}%` : '--'}
          accent={m && m.ops_review_hygiene_score < 0.5 ? 'warning' : null}
        />
        <MetricCard
          label="Validation Velocity"
          value={m ? `${(m.ops_validation_velocity_score * 100).toFixed(0)}%` : '--'}
          accent={m && m.ops_validation_velocity_score < 0.5 ? 'warning' : null}
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Trust Hygiene"
          value={m ? `${(m.ops_trust_hygiene_score * 100).toFixed(0)}%` : '--'}
        />
        <MetricCard
          label="Knowledge Capture"
          value={m ? `${(m.ops_knowledge_capture_score * 100).toFixed(0)}%` : '--'}
        />
        <MetricCard label="Stale KPIs" value={tick?.stale_kpi_count ?? 0} accent={tick && tick.stale_kpi_count > 0 ? 'warning' : null} />
        <MetricCard label="Blocking Trust" value={tick?.blocking_trust_count ?? 0} accent={tick && tick.blocking_trust_count > 0 ? 'danger' : null} />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Health alerts */}
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Health Alerts
            {alerts.length > 0 && (
              <Badge variant="danger" size="sm" className="ml-2">{alerts.length}</Badge>
            )}
          </h3>
          <div className="space-y-2">
            {alerts.map((a, i) => (
              <div key={i} className="flex items-start gap-2 px-3 py-2 rounded-md bg-gray-50">
                <StatusDot status={a.severity === 'critical' ? 'red' : 'yellow'} size="sm" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-900">{a.alert}</span>
                    <Badge variant={a.severity === 'critical' ? 'danger' : 'warning'} size="sm">{a.severity}</Badge>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{a.venture_id} — {a.detail}</p>
                </div>
              </div>
            ))}
            {alerts.length === 0 && (
              <p className="text-sm text-gray-400">No alerts — all systems healthy</p>
            )}
          </div>
        </Card>

        {/* Decisions */}
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Pending Decisions
            {decisions.length > 0 && (
              <Badge variant="info" size="sm" className="ml-2">{decisions.length}</Badge>
            )}
          </h3>
          <div className="space-y-2">
            {decisions.map((d, i) => (
              <div key={i} className="px-3 py-2 rounded-md bg-gray-50">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-900">{d.venture_id}</span>
                  <Badge variant="outline" size="sm">{d.decision}</Badge>
                </div>
                <p className="text-xs text-gray-500">{d.required_next_step}</p>
              </div>
            ))}
            {decisions.length === 0 && (
              <p className="text-sm text-gray-400">No pending decisions</p>
            )}
          </div>
        </Card>
      </div>

      {/* Office hours */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">
          Office Hours Queue
          {officeHours.length > 0 && (
            <Badge variant="info" size="sm" className="ml-2">{officeHours.length}</Badge>
          )}
        </h3>
        {officeHours.length > 0 ? (
          <div className="divide-y divide-gray-50">
            {officeHours.map((oh, i) => (
              <div key={i} className="py-2.5 first:pt-0 last:pb-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-gray-900">{oh.venture_id}</span>
                  <Badge variant="outline" size="sm">{oh.commitment}</Badge>
                </div>
                {oh.agenda.length > 0 && (
                  <ul className="space-y-0.5">
                    {oh.agenda.map((item, j) => (
                      <li key={j} className="text-xs text-gray-600 flex items-center gap-1.5">
                        <span className="w-1 h-1 bg-gray-300 rounded-full shrink-0" />
                        {item}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400">No upcoming office hours</p>
        )}
      </Card>

      {/* Queue counters */}
      <Card>
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Queue Summary</h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
          <div>
            <p className="text-2xl font-semibold text-gray-900">{tick?.venture_task_count ?? 0}</p>
            <p className="text-xs text-gray-500 mt-0.5">Venture Tasks</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{tick?.conversation_count ?? 0}</p>
            <p className="text-xs text-gray-500 mt-0.5">Conversations</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{tick?.open_pipeline_count ?? 0}</p>
            <p className="text-xs text-gray-500 mt-0.5">Open Pipeline</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{tick?.promoted_playbook_count ?? 0}</p>
            <p className="text-xs text-gray-500 mt-0.5">Promoted Playbooks</p>
          </div>
        </div>
      </Card>
    </div>
  )
}
