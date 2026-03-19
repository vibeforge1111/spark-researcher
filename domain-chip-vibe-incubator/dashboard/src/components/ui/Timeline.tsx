import clsx from 'clsx'
import type { TimelineEntry } from '@/types'
import { formatAge } from '@/lib/format'

interface TimelineProps {
  entries: TimelineEntry[]
  maxItems?: number
  className?: string
}

const toneDot: Record<string, string> = {
  good: 'bg-success-500',
  warn: 'bg-warning-500',
  bad: 'bg-danger-500',
  info: 'bg-gray-400',
}

const toneLine: Record<string, string> = {
  good: 'bg-success-200',
  warn: 'bg-warning-200',
  bad: 'bg-danger-200',
  info: 'bg-gray-200',
}

export function Timeline({ entries, maxItems, className }: TimelineProps) {
  const items = maxItems ? entries.slice(0, maxItems) : entries
  return (
    <div className={clsx('space-y-0', className)}>
      {items.map((entry, i) => (
        <div key={entry.id} className="flex gap-3 group">
          {/* Left connector */}
          <div className="flex flex-col items-center pt-1.5">
            <div className={clsx('w-2 h-2 rounded-full shrink-0', toneDot[entry.tone] || toneDot.info)} />
            {i < items.length - 1 && (
              <div className={clsx('w-0.5 grow mt-1', toneLine[entry.tone] || toneLine.info)} />
            )}
          </div>
          {/* Content */}
          <div className="pb-4 min-w-0">
            <div className="flex items-baseline gap-2">
              <p className="text-sm font-medium text-gray-900 truncate">{entry.title}</p>
              {entry.createdAt && (
                <span className="text-xs text-gray-400 shrink-0">{formatAge(entry.createdAt)}</span>
              )}
            </div>
            {entry.detail && (
              <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{entry.detail}</p>
            )}
            <span className="inline-block mt-1 text-[10px] font-medium text-gray-400 uppercase tracking-wider">
              {entry.lane}
            </span>
          </div>
        </div>
      ))}
      {items.length === 0 && (
        <p className="text-sm text-gray-400 py-4 text-center">No events yet</p>
      )}
    </div>
  )
}
