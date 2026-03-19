import clsx from 'clsx'

interface ProgressBarProps {
  value: number // 0-100
  label?: string
  showValue?: boolean
  className?: string
}

function barColor(value: number): string {
  if (value >= 70) return 'bg-success-500'
  if (value >= 40) return 'bg-warning-500'
  return 'bg-danger-500'
}

export function ProgressBar({ value, label, showValue = true, className }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value))
  return (
    <div className={clsx('space-y-1', className)}>
      {(label || showValue) && (
        <div className="flex justify-between text-xs">
          {label && <span className="font-medium text-gray-600">{label}</span>}
          {showValue && <span className="text-gray-400">{Math.round(clamped)}%</span>}
        </div>
      )}
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={clsx('h-full rounded-full transition-all duration-500', barColor(clamped))}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  )
}
