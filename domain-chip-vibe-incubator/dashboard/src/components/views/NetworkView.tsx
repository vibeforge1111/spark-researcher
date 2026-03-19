import { useMemo } from 'react'
import type { DashboardSnapshot, NetworkNode, NetworkEdge } from '@/types'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'

interface Props {
  data: DashboardSnapshot
}

const NODE_COLORS: Record<string, string> = {
  venture: '#635bff',
  founder: '#12b76a',
  mentor: '#f79009',
  investor: '#f04438',
  default: '#98a2b3',
}

const EDGE_COLORS: Record<string, string> = {
  founded: '#635bff',
  mentoring: '#f79009',
  invested: '#f04438',
  collaboration: '#12b76a',
  default: '#d0d5dd',
}

function forceLayout(nodes: NetworkNode[], edges: NetworkEdge[], width: number, height: number) {
  // Simple circular layout with type-based grouping
  const typeGroups = new Map<string, NetworkNode[]>()
  nodes.forEach((n) => {
    const group = typeGroups.get(n.type) ?? []
    group.push(n)
    typeGroups.set(n.type, group)
  })

  const positions = new Map<string, { x: number; y: number }>()
  const cx = width / 2
  const cy = height / 2
  const maxR = Math.min(width, height) * 0.38

  let i = 0
  const total = nodes.length || 1
  nodes.forEach((n) => {
    const angle = (i / total) * 2 * Math.PI - Math.PI / 2
    const r = maxR * (0.6 + Math.random() * 0.4)
    positions.set(n.id, {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    })
    i++
  })

  return positions
}

export function NetworkView({ data }: Props) {
  const nodes = data.network?.nodes ?? []
  const edges = data.network?.edges ?? []

  const WIDTH = 700
  const HEIGHT = 500

  const positions = useMemo(() => forceLayout(nodes, edges, WIDTH, HEIGHT), [nodes, edges])

  const typeCounts = useMemo(() => {
    const counts = new Map<string, number>()
    nodes.forEach((n) => counts.set(n.type, (counts.get(n.type) ?? 0) + 1))
    return counts
  }, [nodes])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Network</h2>
        <p className="text-sm text-gray-500 mt-0.5">{nodes.length} nodes, {edges.length} connections</p>
      </div>

      {/* Legend */}
      <div className="flex gap-4 flex-wrap">
        {Array.from(typeCounts.entries()).map(([type, count]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span
              className="w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: NODE_COLORS[type] ?? NODE_COLORS.default }}
            />
            <span className="text-xs text-gray-600">{type} ({count})</span>
          </div>
        ))}
      </div>

      {/* Graph */}
      <Card padding="none">
        {nodes.length > 0 ? (
          <svg
            width="100%"
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            className="block"
          >
            {/* Edges */}
            {edges.map((e) => {
              const from = positions.get(e.source)
              const to = positions.get(e.target)
              if (!from || !to) return null
              return (
                <line
                  key={e.id}
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={EDGE_COLORS[e.type] ?? EDGE_COLORS.default}
                  strokeWidth={1.5}
                  strokeOpacity={0.5}
                />
              )
            })}

            {/* Nodes */}
            {nodes.map((n) => {
              const pos = positions.get(n.id)
              if (!pos) return null
              const color = NODE_COLORS[n.type] ?? NODE_COLORS.default
              return (
                <g key={n.id}>
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={n.score ? 6 + n.score * 4 : 6}
                    fill={color}
                    fillOpacity={0.15}
                    stroke={color}
                    strokeWidth={1.5}
                  />
                  <text
                    x={pos.x}
                    y={pos.y + (n.score ? 6 + n.score * 4 : 6) + 12}
                    textAnchor="middle"
                    className="text-[9px] fill-gray-600 font-medium"
                  >
                    {n.label.length > 14 ? n.label.slice(0, 12) + '...' : n.label}
                  </text>
                </g>
              )
            })}
          </svg>
        ) : (
          <div className="py-16 text-center text-gray-400 text-sm">No network data available</div>
        )}
      </Card>

      {/* Node list */}
      {nodes.length > 0 && (
        <Card>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">Network Members</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
            {nodes.map((n) => (
              <div key={n.id} className="flex items-center justify-between px-3 py-2 rounded-md bg-gray-50">
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: NODE_COLORS[n.type] ?? NODE_COLORS.default }}
                  />
                  <span className="text-sm text-gray-900">{n.label}</span>
                </div>
                <Badge variant="outline" size="sm">{n.type}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
