import type { DashboardSnapshot } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ProgressBar } from '@/components/ui/ProgressBar'
import { Radar } from '@/components/ui/Radar'

interface Props {
  data: DashboardSnapshot
}

export function GenesisView({ data }: Props) {
  const ventures = data.ventures?.filter((v) => v.status === 'active') ?? []
  const genesis = data.genesisSystem
  const curriculum = data.curriculum ?? []

  // Compute cohort-wide averages
  const avgReadiness = ventures.length > 0
    ? {
        utility: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.utility ?? 0), 0) / ventures.length),
        traction: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.traction ?? 0), 0) / ventures.length),
        governance: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.governance ?? 0), 0) / ventures.length),
        contribution: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.contribution ?? 0), 0) / ventures.length),
        trust: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.trust ?? 0), 0) / ventures.length),
        treasury: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.treasury ?? 0), 0) / ventures.length),
        overall: Math.round(ventures.reduce((s, v) => s + (v.tokenReadiness?.overall ?? 0), 0) / ventures.length),
      }
    : { utility: 0, traction: 0, governance: 0, contribution: 0, trust: 0, treasury: 0, overall: 0 }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Genesis</h2>
        <p className="text-sm text-gray-500 mt-0.5">Token readiness and SPARK system</p>
      </div>

      {/* Cohort radar + readiness bars */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Cohort Readiness</h3>
          <div className="flex justify-center">
            <Radar readiness={avgReadiness} size={260} />
          </div>
          <div className="mt-4 text-center">
            <span className="text-2xl font-bold text-gray-900">{avgReadiness.overall}%</span>
            <p className="text-xs text-gray-500 mt-0.5">Average Overall Readiness</p>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Readiness Breakdown</h3>
          <div className="space-y-3">
            <ProgressBar label="Utility" value={avgReadiness.utility} />
            <ProgressBar label="Traction" value={avgReadiness.traction} />
            <ProgressBar label="Governance" value={avgReadiness.governance} />
            <ProgressBar label="Contribution" value={avgReadiness.contribution} />
            <ProgressBar label="Trust" value={avgReadiness.trust} />
            <ProgressBar label="Treasury" value={avgReadiness.treasury} />
          </div>
          <div className="mt-4 pt-3 border-t border-gray-100">
            <div className="flex justify-between text-sm">
              <span className="font-medium text-gray-700">Overall</span>
              <span className="font-semibold text-gray-900">{avgReadiness.overall}%</span>
            </div>
          </div>
        </Card>
      </div>

      {/* SPARK System */}
      {genesis && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-4">SPARK Token System</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-xs text-gray-500 uppercase font-medium">Base Token</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{genesis.spark.baseToken}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase font-medium">Governance Token</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{genesis.spark.governanceToken}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase font-medium">Treasury Flow</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{genesis.spark.treasuryFlow}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase font-medium">Project Exposure</p>
              <p className="text-sm font-semibold text-gray-900 mt-1">{genesis.spark.projectExposure}</p>
            </div>
          </div>

          {genesis.rules.length > 0 && (
            <div className="mb-4">
              <p className="text-xs text-gray-500 uppercase font-medium mb-2">System Rules</p>
              <ul className="space-y-1">
                {genesis.rules.map((r, i) => (
                  <li key={i} className="text-xs text-gray-700 flex items-start gap-2">
                    <span className="w-1.5 h-1.5 bg-primary-400 rounded-full shrink-0 mt-1" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Genesis phases */}
      {genesis && genesis.phases.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Genesis Phases</h3>
          <div className="flex gap-2 flex-wrap">
            {genesis.phases.map((phase, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-6 h-6 rounded-full bg-primary-100 text-primary-700 text-xs font-semibold flex items-center justify-center">
                  {i + 1}
                </span>
                <span className="text-sm text-gray-700">{phase}</span>
                {i < genesis.phases.length - 1 && (
                  <span className="text-gray-300 mx-1">&rarr;</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Per-venture readiness */}
      {ventures.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Venture Readiness</h3>
          <div className="space-y-3">
            {ventures.map((v) => (
              <div key={v.venture_id} className="flex items-center gap-4">
                <span className="text-sm text-gray-700 w-36 truncate">{v.label}</span>
                <div className="flex-1">
                  <ProgressBar value={v.tokenReadiness?.overall ?? 0} />
                </div>
                <span className="text-xs font-medium text-gray-600 w-10 text-right">
                  {Math.round(v.tokenReadiness?.overall ?? 0)}%
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Curriculum */}
      {curriculum.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Curriculum</h3>
          <div className="space-y-3">
            {curriculum.map((mod) => (
              <div key={mod.id} className="px-3 py-2.5 rounded-md bg-gray-50">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-900">{mod.title}</span>
                  <Badge variant="outline" size="sm">{mod.id}</Badge>
                </div>
                <p className="text-xs text-gray-600 mb-2">{mod.description}</p>
                {mod.outputs.length > 0 && (
                  <div className="flex gap-1 flex-wrap">
                    {mod.outputs.map((o, i) => (
                      <Badge key={i} variant="default" size="sm">{o}</Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {ventures.length === 0 && !genesis && curriculum.length === 0 && (
        <Card>
          <div className="py-8 text-center text-gray-400 text-sm">No genesis data available</div>
        </Card>
      )}
    </div>
  )
}
