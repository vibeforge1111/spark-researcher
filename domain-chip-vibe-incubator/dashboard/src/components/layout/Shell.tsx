import type { ViewId, DashboardSnapshot } from '@/types'
import { Sidebar } from './Sidebar'

interface ShellProps {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
  data?: DashboardSnapshot | null
  children: React.ReactNode
}

export function Shell({ activeView, onNavigate, data, children }: ShellProps) {
  return (
    <div className="grid grid-cols-[240px_1fr] min-h-screen">
      <Sidebar activeView={activeView} onNavigate={onNavigate} data={data} />
      <main className="overflow-y-auto min-h-screen">
        <div className="max-w-[1400px] mx-auto px-6 py-6">
          {children}
        </div>
      </main>
    </div>
  )
}
