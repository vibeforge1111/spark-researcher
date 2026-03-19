import type { TokenReadiness } from '@/types'

interface RadarProps {
  readiness: TokenReadiness
  size?: number
  className?: string
}

const AXES = ['utility', 'traction', 'governance', 'contribution', 'trust', 'treasury'] as const
const LABELS = ['Utility', 'Traction', 'Governance', 'Contribution', 'Trust', 'Treasury']

function polar(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

export function Radar({ readiness, size = 220, className }: RadarProps) {
  const cx = size / 2
  const cy = size / 2
  const maxR = size * 0.38
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0]
  const step = 360 / AXES.length

  // Data polygon
  const dataPoints = AXES.map((axis, i) => {
    const val = Math.min(100, readiness[axis]) / 100
    return polar(cx, cy, maxR * val, i * step)
  })
  const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') + ' Z'

  return (
    <svg width={size} height={size} className={className} viewBox={`0 0 ${size} ${size}`}>
      {/* Grid rings */}
      {rings.map((r) => (
        <polygon
          key={r}
          points={AXES.map((_, i) => {
            const p = polar(cx, cy, maxR * r, i * step)
            return `${p.x},${p.y}`
          }).join(' ')}
          fill="none"
          stroke="#e4e7ec"
          strokeWidth={1}
        />
      ))}

      {/* Axis lines */}
      {AXES.map((_, i) => {
        const p = polar(cx, cy, maxR, i * step)
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e4e7ec" strokeWidth={1} />
      })}

      {/* Data area */}
      <path d={dataPath} fill="#635bff" fillOpacity={0.15} stroke="#635bff" strokeWidth={2} />

      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill="#635bff" />
      ))}

      {/* Labels */}
      {LABELS.map((label, i) => {
        const p = polar(cx, cy, maxR + 18, i * step)
        return (
          <text
            key={i}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="text-[10px] fill-gray-500 font-medium"
          >
            {label}
          </text>
        )
      })}
    </svg>
  )
}
