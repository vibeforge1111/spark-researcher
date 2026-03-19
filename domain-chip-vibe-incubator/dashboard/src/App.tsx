import { useState, useCallback } from 'react'
import type { ViewId } from '@/types'
import { useDashboard } from '@/api/queries'
import { Shell } from '@/components/layout/Shell'
import { Toast } from '@/components/ui/Toast'
import { OverviewView } from '@/components/views/OverviewView'
import { VenturesView } from '@/components/views/VenturesView'
import { ApplyView } from '@/components/views/ApplyView'
import { OperationsView } from '@/components/views/OperationsView'
import { GovernanceView } from '@/components/views/GovernanceView'
import { NetworkView } from '@/components/views/NetworkView'
import { GenesisView } from '@/components/views/GenesisView'
import { FeedView } from '@/components/views/FeedView'

export interface ToastState {
  message: string
  tone: 'success' | 'error' | 'info'
}

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>('overview')
  const [toast, setToast] = useState<ToastState | null>(null)
  const { data, isLoading, error } = useDashboard()

  const showToast = useCallback((t: ToastState) => setToast(t), [])
  const dismissToast = useCallback(() => setToast(null), [])

  if (isLoading && !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-sm">
          <p className="text-sm text-danger-600 font-medium mb-2">Failed to load dashboard</p>
          <p className="text-xs text-gray-500">{String(error)}</p>
        </div>
      </div>
    )
  }

  return (
    <Shell activeView={activeView} onNavigate={setActiveView} data={data}>
      {activeView === 'overview' && <OverviewView data={data!} onNavigate={setActiveView} />}
      {activeView === 'ventures' && <VenturesView data={data!} />}
      {activeView === 'apply' && <ApplyView data={data!} showToast={showToast} />}
      {activeView === 'operations' && <OperationsView data={data!} />}
      {activeView === 'governance' && <GovernanceView data={data!} showToast={showToast} />}
      {activeView === 'network' && <NetworkView data={data!} />}
      {activeView === 'genesis' && <GenesisView data={data!} />}
      {activeView === 'feed' && <FeedView data={data!} />}

      {toast && <Toast message={toast.message} tone={toast.tone} onDismiss={dismissToast} />}
    </Shell>
  )
}
