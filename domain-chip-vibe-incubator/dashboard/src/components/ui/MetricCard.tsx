import clsx from 'clsx'

interface MetricCardProps {
  label: string
  value: string | number
  trend?: 'up' | 'down' | 'flat' | null
  trendValue?: string
  accent?: 'success' | 'warning' | 'danger' | null
  className?: string
}

const trendColors = {
  up: 'text-success-500',
  down: 'text-danger-500',
  flat: 'text-gray-400',
}

const trendArrows = { up: '\u2191', down: '\u2193', flat: '\u2192' }

export function MetricCard({
  label,
  value,
  trend = null,
  trendValue,
  accent = null,
  className,
}: MetricCardProps) {
  return (
    <div
      className={clsx(
        'bg-white border border-gray-200 rounded-lg p-4 shadow-xs',
        accent === 'success' && 'border-l-4 border-l-success-500',
        accent === 'warning' && 'border-l-4 border-l-warning-500',
        accent === 'danger' && 'border-l-4 border-l-danger-500',
        className,
      )}
    >
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">{label}</p>
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      {trend && trendValue && (
        <p className={clsx('text-sm mt-1 font-medium', trendColors[trend])}>
          {trendArrows[trend]} {trendValue}
        </p>
      )}
    </div>
  )
}
