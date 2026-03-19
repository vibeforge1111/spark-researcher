export function formatScore(value: number | undefined | null): string {
  if (value == null) return '--'
  return (value * 100).toFixed(0) + '%'
}

export function formatDecimal(value: number | undefined | null, digits = 2): string {
  if (value == null) return '--'
  return value.toFixed(digits)
}

export function formatCurrency(value: number | undefined | null): string {
  if (value == null) return '--'
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}K`
  return `$${value.toFixed(0)}`
}

export function formatPercent(value: number | undefined | null): string {
  if (value == null) return '--'
  return `${(value * 100).toFixed(0)}%`
}

export function formatTrend(value: number | undefined | null): string {
  if (value == null) return '--'
  const pct = (value * 100).toFixed(0)
  if (value > 0) return `+${pct}%`
  return `${pct}%`
}

export function formatAge(isoDate: string | null | undefined): string {
  if (!isoDate) return '--'
  const diff = Date.now() - new Date(isoDate).getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function formatNumber(value: number | undefined | null): string {
  if (value == null) return '--'
  return value.toLocaleString()
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export function stageLabel(stage: string): string {
  return stage.replace(/_/g, ' ').split(' ').map(capitalize).join(' ')
}
