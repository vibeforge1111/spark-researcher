import clsx from 'clsx'
import type { HealthAlert } from '@/types'

interface AlertBannerProps {
  alerts: HealthAlert[]
  className?: string
}

export function AlertBanner({ alerts, className }: AlertBannerProps) {
  if (alerts.length === 0) return null

  const criticals = alerts.filter((a) => a.severity === 'critical')
  const warnings = alerts.filter((a) => a.severity === 'warning')

  return (
    <div className={clsx('space-y-2', className)}>
      {criticals.length > 0 && (
        <div className="bg-danger-50 border border-danger-200 rounded-lg px-4 py-3">
          <p className="text-sm font-semibold text-danger-700 mb-1">
            {criticals.length} critical alert{criticals.length > 1 ? 's' : ''}
          </p>
          <ul className="space-y-0.5">
            {criticals.map((a, i) => (
              <li key={i} className="text-sm text-danger-700">
                <span className="font-medium">{a.venture_id}</span> &mdash; {a.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="bg-warning-50 border border-warning-200 rounded-lg px-4 py-3">
          <p className="text-sm font-semibold text-warning-700 mb-1">
            {warnings.length} warning{warnings.length > 1 ? 's' : ''}
          </p>
          <ul className="space-y-0.5">
            {warnings.map((a, i) => (
              <li key={i} className="text-sm text-warning-700">
                <span className="font-medium">{a.venture_id}</span> &mdash; {a.detail}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
