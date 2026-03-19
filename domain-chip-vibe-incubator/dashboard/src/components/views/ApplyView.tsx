import { useState } from 'react'
import type { DashboardSnapshot, Application } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { useAdmissionsReview } from '@/api/mutations'
import { formatDecimal } from '@/lib/format'

interface Props {
  data: DashboardSnapshot
  showToast: (t: { message: string; tone: 'success' | 'error' | 'info' }) => void
}

export function ApplyView({ data, showToast }: Props) {
  const applications = data.scout?.applications ?? []
  const pending = applications.filter((a) => a.status === 'pending')
  const reviewed = applications.filter((a) => a.status !== 'pending')

  const review = useAdmissionsReview()
  const [activeNote, setActiveNote] = useState<Record<string, string>>({})

  const handleDecision = (app: Application, decision: string) => {
    review.mutate(
      { application_id: app.application_id, decision, note: activeNote[app.application_id] || undefined },
      {
        onSuccess: () => showToast({ message: `${app.label} — ${decision}`, tone: 'success' }),
        onError: (err) => showToast({ message: String(err), tone: 'error' }),
      },
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Applications</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          {pending.length} pending, {reviewed.length} reviewed
        </p>
      </div>

      {/* Queue stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <p className="text-xs text-gray-500 uppercase font-medium">Pending</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{pending.length}</p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 uppercase font-medium">Portfolio Cap</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">
            {data.queueSnapshot?.active_portfolio_count ?? 0}/{data.queueSnapshot?.portfolio_cap ?? 3}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-gray-500 uppercase font-medium">Total Reviewed</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{reviewed.length}</p>
        </Card>
      </div>

      {/* Pending applications */}
      {pending.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-gray-900">Pending Review</h3>
          {pending.map((app) => (
            <Card key={app.application_id}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900">{app.label}</h4>
                  <p className="text-xs text-gray-500">{app.application_id}</p>
                </div>
                {app.incubator_compound_score != null && (
                  <Badge variant={app.incubator_compound_score >= 0.7 ? 'success' : app.incubator_compound_score >= 0.5 ? 'warning' : 'danger'}>
                    Score: {formatDecimal(app.incubator_compound_score)}
                  </Badge>
                )}
              </div>

              {app.thesis_summary && (
                <p className="text-sm text-gray-700 mb-3">{app.thesis_summary}</p>
              )}

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-3 text-xs">
                {app.venture_model && (
                  <div>
                    <span className="text-gray-500">Model</span>
                    <p className="text-gray-900 font-medium">{app.venture_model}</p>
                  </div>
                )}
                {app.customer_surface && (
                  <div>
                    <span className="text-gray-500">Surface</span>
                    <p className="text-gray-900 font-medium">{app.customer_surface}</p>
                  </div>
                )}
                {app.distribution_engine && (
                  <div>
                    <span className="text-gray-500">Distribution</span>
                    <p className="text-gray-900 font-medium">{app.distribution_engine}</p>
                  </div>
                )}
                {app.venture_theme && (
                  <div>
                    <span className="text-gray-500">Theme</span>
                    <p className="text-gray-900 font-medium">{app.venture_theme}</p>
                  </div>
                )}
              </div>

              {app.first_week_plan && app.first_week_plan.length > 0 && (
                <div className="mb-3">
                  <p className="text-xs text-gray-500 uppercase font-medium mb-1">First Week Plan</p>
                  <ul className="space-y-0.5">
                    {app.first_week_plan.map((step, i) => (
                      <li key={i} className="text-xs text-gray-700 flex items-center gap-1.5">
                        <span className="w-1 h-1 bg-gray-300 rounded-full shrink-0" />
                        {step}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {app.recommended_decision && (
                <div className="mb-3 px-3 py-2 bg-gray-50 rounded-md text-xs">
                  <span className="text-gray-500">Recommendation: </span>
                  <span className="font-medium text-gray-900">{app.recommended_decision}</span>
                </div>
              )}

              {/* Note + actions */}
              <div className="flex items-end gap-3 pt-3 border-t border-gray-100">
                <input
                  type="text"
                  placeholder="Optional note..."
                  value={activeNote[app.application_id] ?? ''}
                  onChange={(e) => setActiveNote((prev) => ({ ...prev, [app.application_id]: e.target.value }))}
                  className="flex-1 text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400"
                />
                <button
                  onClick={() => handleDecision(app, 'invite')}
                  disabled={review.isPending}
                  className="px-3 py-1.5 text-xs font-medium bg-success-50 text-success-700 border border-success-200 rounded-md hover:bg-success-100 disabled:opacity-50 transition-colors"
                >
                  Invite
                </button>
                <button
                  onClick={() => handleDecision(app, 'waitlist')}
                  disabled={review.isPending}
                  className="px-3 py-1.5 text-xs font-medium bg-warning-50 text-warning-700 border border-warning-200 rounded-md hover:bg-warning-100 disabled:opacity-50 transition-colors"
                >
                  Waitlist
                </button>
                <button
                  onClick={() => handleDecision(app, 'reject')}
                  disabled={review.isPending}
                  className="px-3 py-1.5 text-xs font-medium bg-danger-50 text-danger-700 border border-danger-200 rounded-md hover:bg-danger-100 disabled:opacity-50 transition-colors"
                >
                  Reject
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Reviewed */}
      {reviewed.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-900">Previously Reviewed</h3>
          <Card padding="none">
            <div className="divide-y divide-gray-50">
              {reviewed.map((app) => (
                <div key={app.application_id} className="px-4 py-2.5 flex items-center justify-between">
                  <div>
                    <span className="text-sm text-gray-700">{app.label}</span>
                    <span className="text-xs text-gray-400 ml-2">{app.application_id}</span>
                  </div>
                  <Badge
                    variant={app.status === 'invited' ? 'success' : app.status === 'waitlisted' ? 'warning' : 'danger'}
                    size="sm"
                  >
                    {app.status}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {applications.length === 0 && (
        <Card>
          <div className="py-8 text-center text-gray-400 text-sm">No applications yet</div>
        </Card>
      )}
    </div>
  )
}
