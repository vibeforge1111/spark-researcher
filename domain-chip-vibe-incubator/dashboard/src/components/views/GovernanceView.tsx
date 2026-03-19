import { useState } from 'react'
import type { DashboardSnapshot } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { useGovernancePropose, useGovernanceVote, useGovernanceTally } from '@/api/mutations'

interface Props {
  data: DashboardSnapshot
  showToast: (t: { message: string; tone: 'success' | 'error' | 'info' }) => void
}

const PROPOSAL_TYPES = ['token_readiness', 'support_reserve', 'curriculum', 'contributor_reward', 'treasury_support', 'spotlight'] as const

export function GovernanceView({ data, showToast }: Props) {
  const gov = data.governance
  const proposals = gov?.proposals ?? []
  const resolutions = gov?.resolutions ?? []
  const stats = gov?.stats

  const propose = useGovernancePropose()
  const vote = useGovernanceVote()
  const tally = useGovernanceTally()

  // Proposal form state
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    proposal_id: '',
    proposal_type: PROPOSAL_TYPES[0] as string,
    venture_id: '',
    description: '',
  })

  const handlePropose = () => {
    if (!form.proposal_id || !form.description) return
    propose.mutate(form, {
      onSuccess: () => {
        showToast({ message: `Proposal ${form.proposal_id} created`, tone: 'success' })
        setShowForm(false)
        setForm({ proposal_id: '', proposal_type: PROPOSAL_TYPES[0], venture_id: '', description: '' })
      },
      onError: (err) => showToast({ message: String(err), tone: 'error' }),
    })
  }

  const handleVote = (proposalId: string, decision: string) => {
    vote.mutate(
      { proposal_id: proposalId, decision, weight: 1 },
      {
        onSuccess: () => showToast({ message: `Voted ${decision} on ${proposalId}`, tone: 'success' }),
        onError: (err) => showToast({ message: String(err), tone: 'error' }),
      },
    )
  }

  const handleTally = () => {
    tally.mutate(
      { quorum: 0.5 },
      {
        onSuccess: () => showToast({ message: 'Tally complete', tone: 'success' }),
        onError: (err) => showToast({ message: String(err), tone: 'error' }),
      },
    )
  }

  const openProposals = proposals.filter((p) => p.status === 'open')
  const closedProposals = proposals.filter((p) => p.status !== 'open')

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">Governance</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {proposals.length} proposals, {resolutions.length} resolved
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleTally}
            disabled={tally.isPending || openProposals.length === 0}
            className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50 transition-colors"
          >
            Run Tally
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
          >
            New Proposal
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <p className="text-xs text-gray-500 uppercase font-medium">Total Proposals</p>
            <p className="text-2xl font-semibold text-gray-900 mt-1">{proposals.length}</p>
          </Card>
          <Card>
            <p className="text-xs text-gray-500 uppercase font-medium">Open</p>
            <p className="text-2xl font-semibold text-gray-900 mt-1">{openProposals.length}</p>
          </Card>
          <Card>
            <p className="text-xs text-gray-500 uppercase font-medium">Resolved</p>
            <p className="text-2xl font-semibold text-gray-900 mt-1">{stats.total_resolved ?? 0}</p>
          </Card>
          <Card>
            <p className="text-xs text-gray-500 uppercase font-medium">Pass Rate</p>
            <p className="text-2xl font-semibold text-gray-900 mt-1">
              {stats.total_resolved
                ? `${Math.round(((stats.total_passed ?? 0) / stats.total_resolved) * 100)}%`
                : '--'}
            </p>
          </Card>
        </div>
      )}

      {/* New proposal form */}
      {showForm && (
        <Card accent="primary">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">New Proposal</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Proposal ID</label>
              <input
                type="text"
                value={form.proposal_id}
                onChange={(e) => setForm({ ...form, proposal_id: e.target.value })}
                placeholder="e.g. PROP-001"
                className="w-full text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Type</label>
              <select
                value={form.proposal_type}
                onChange={(e) => setForm({ ...form, proposal_type: e.target.value })}
                className="w-full text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 bg-white"
              >
                {PROPOSAL_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Venture ID (optional)</label>
              <input
                type="text"
                value={form.venture_id}
                onChange={(e) => setForm({ ...form, venture_id: e.target.value })}
                placeholder="e.g. venture-alpha"
                className="w-full text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400"
              />
            </div>
          </div>
          <div className="mb-3">
            <label className="text-xs text-gray-500 block mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2}
              placeholder="What is this proposal about?"
              className="w-full text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-400 resize-none"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowForm(false)}
              className="px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handlePropose}
              disabled={propose.isPending || !form.proposal_id || !form.description}
              className="px-3 py-1.5 text-xs font-medium bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 transition-colors"
            >
              Submit Proposal
            </button>
          </div>
        </Card>
      )}

      {/* Open proposals */}
      {openProposals.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-900">Open Proposals</h3>
          {openProposals.map((p) => {
            const total = p.votes_for + p.votes_against
            const forPct = total > 0 ? (p.votes_for / total) * 100 : 0
            return (
              <Card key={p.proposal_id}>
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-gray-900">{p.proposal_id}</span>
                      <Badge variant="info" size="sm">{p.proposal_type.replace(/_/g, ' ')}</Badge>
                    </div>
                    {p.venture_id && <p className="text-xs text-gray-500 mt-0.5">{p.venture_id}</p>}
                  </div>
                  <Badge variant="warning">Open</Badge>
                </div>
                <p className="text-sm text-gray-700 mb-3">{p.description}</p>
                {total > 0 && (
                  <div className="mb-3">
                    <ProgressBar label={`For: ${p.votes_for} / Against: ${p.votes_against}`} value={forPct} />
                  </div>
                )}
                <div className="flex gap-2 pt-2 border-t border-gray-100">
                  <button
                    onClick={() => handleVote(p.proposal_id, 'approve')}
                    disabled={vote.isPending}
                    className="px-3 py-1.5 text-xs font-medium bg-success-50 text-success-700 border border-success-200 rounded-md hover:bg-success-100 disabled:opacity-50 transition-colors"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleVote(p.proposal_id, 'reject')}
                    disabled={vote.isPending}
                    className="px-3 py-1.5 text-xs font-medium bg-danger-50 text-danger-700 border border-danger-200 rounded-md hover:bg-danger-100 disabled:opacity-50 transition-colors"
                  >
                    Reject
                  </button>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Resolutions */}
      {resolutions.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-900">Resolutions</h3>
          <Card padding="none">
            <div className="divide-y divide-gray-50">
              {resolutions.map((r, i) => (
                <div key={i} className="px-4 py-2.5 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{r.proposal_id}</span>
                    <span className="text-xs text-gray-500 ml-2">
                      {r.votes_for} for / {r.votes_against} against
                    </span>
                  </div>
                  <Badge variant={r.outcome === 'passed' ? 'success' : 'danger'} size="sm">
                    {r.outcome}
                  </Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* Closed proposals */}
      {closedProposals.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-900">Closed Proposals</h3>
          <Card padding="none">
            <div className="divide-y divide-gray-50">
              {closedProposals.map((p) => (
                <div key={p.proposal_id} className="px-4 py-2.5 flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium text-gray-900">{p.proposal_id}</span>
                    <span className="text-xs text-gray-400 ml-2">{p.proposal_type.replace(/_/g, ' ')}</span>
                  </div>
                  <Badge variant={p.status === 'passed' ? 'success' : 'danger'} size="sm">{p.status}</Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {proposals.length === 0 && !showForm && (
        <Card>
          <div className="py-8 text-center text-gray-400 text-sm">No governance proposals yet</div>
        </Card>
      )}
    </div>
  )
}
