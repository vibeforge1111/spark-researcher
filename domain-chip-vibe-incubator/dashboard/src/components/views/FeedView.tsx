import { useState } from 'react'
import type { DashboardSnapshot, FeedEntry } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { StatusDot } from '@/components/ui/StatusDot'
import { formatAge } from '@/lib/format'

interface Props {
  data: DashboardSnapshot
}

const LANES = ['all', 'validation', 'customer', 'operator', 'governance', 'trust'] as const
type Lane = (typeof LANES)[number]

const toneDot = (tone: FeedEntry['tone']) =>
  tone === 'good' ? 'green' : tone === 'bad' ? 'red' : tone === 'warn' ? 'yellow' : 'gray'

export function FeedView({ data }: Props) {
  const feed = data.feed ?? []
  const [lane, setLane] = useState<Lane>('all')

  const filtered = lane === 'all' ? feed : feed.filter((f) => f.detail?.toLowerCase().includes(lane))

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Feed</h2>
        <p className="text-sm text-gray-500 mt-0.5">{feed.length} entries</p>
      </div>

      {/* Lane filters */}
      <div className="flex gap-1.5 flex-wrap">
        {LANES.map((l) => (
          <button
            key={l}
            onClick={() => setLane(l)}
            className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-colors ${
              lane === l
                ? 'bg-primary-50 border-primary-200 text-primary-700'
                : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {l.charAt(0).toUpperCase() + l.slice(1)}
          </button>
        ))}
      </div>

      {/* Feed timeline */}
      <Card padding="none">
        <div className="divide-y divide-gray-50">
          {filtered.map((entry) => (
            <div key={entry.id} className="px-5 py-3 flex items-start gap-3">
              <div className="pt-1">
                <StatusDot status={toneDot(entry.tone)} size="sm" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-gray-900">{entry.title}</span>
                  {entry.ventureLabel && (
                    <Badge variant="outline" size="sm">{entry.ventureLabel}</Badge>
                  )}
                </div>
                {entry.detail && (
                  <p className="text-xs text-gray-500 line-clamp-2">{entry.detail}</p>
                )}
                {entry.createdAt && (
                  <p className="text-[11px] text-gray-400 mt-1">{formatAge(entry.createdAt)}</p>
                )}
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="px-5 py-12 text-center text-gray-400 text-sm">
              {feed.length === 0 ? 'No feed entries yet' : 'No entries match this filter'}
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
