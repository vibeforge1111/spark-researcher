import type { ViewId, DashboardSnapshot } from '@/types'
import { NavItem } from './NavItem'
import { formatDecimal, formatAge } from '@/lib/format'

interface SidebarProps {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
  data?: DashboardSnapshot | null
}

interface NavGroup {
  label: string
  items: Array<{ id: ViewId; label: string; icon: string; badge?: number }>
}

export function Sidebar({ activeView, onNavigate, data }: SidebarProps) {
  const pendingApps = data?.queueSnapshot?.pending_applications ?? 0
  const criticalAlerts = data?.latestTick?.critical_alert_count ?? 0

  const groups: NavGroup[] = [
    {
      label: 'Portfolio',
      items: [
        { id: 'overview', label: 'Overview', icon: '\u25A6', badge: criticalAlerts || undefined },
        { id: 'ventures', label: 'Ventures', icon: '\u25C8' },
        { id: 'genesis', label: 'Genesis', icon: '\u2B22' },
      ],
    },
    {
      label: 'Operations',
      items: [
        { id: 'apply', label: 'Apply', icon: '\u2709', badge: pendingApps || undefined },
        { id: 'operations', label: 'Operations', icon: '\u2699' },
        { id: 'governance', label: 'Governance', icon: '\u2696' },
      ],
    },
    {
      label: 'Community',
      items: [
        { id: 'network', label: 'Network', icon: '\u2B2F' },
        { id: 'feed', label: 'Feed', icon: '\u25CE' },
      ],
    },
  ]

  const score = data?.latestTick?.metrics?.incubator_compound_score
  const activeCount = data?.latestTick?.metrics?.active_portfolio_count ?? 0
  const cap = data?.latestTick?.metrics?.portfolio_cap ?? 3

  return (
    <aside className="bg-white border-r border-gray-200 flex flex-col h-screen sticky top-0">
      {/* Brand */}
      <div className="px-4 py-5 border-b border-gray-100">
        <h1 className="text-sm font-bold text-gray-900 tracking-tight">Vibe Incubator</h1>
        <p className="text-xs text-gray-400 mt-0.5">Operating System</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="px-3 mb-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-widest">
              {group.label}
            </p>
            <div className="space-y-0.5">
              {group.items.map((item) => (
                <NavItem
                  key={item.id}
                  label={item.label}
                  icon={item.icon}
                  active={activeView === item.id}
                  badge={item.badge}
                  onClick={() => onNavigate(item.id)}
                />
              ))}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer stats */}
      <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400 space-y-1">
        <div className="flex justify-between">
          <span>Ventures</span>
          <span className="text-gray-600 font-medium">{activeCount}/{cap}</span>
        </div>
        <div className="flex justify-between">
          <span>Compound</span>
          <span className="text-gray-600 font-medium">{score != null ? formatDecimal(score) : '--'}</span>
        </div>
        {data?.latestTick?.generated_at && (
          <div className="flex justify-between">
            <span>Updated</span>
            <span>{formatAge(data.latestTick.generated_at)}</span>
          </div>
        )}
      </div>
    </aside>
  )
}
