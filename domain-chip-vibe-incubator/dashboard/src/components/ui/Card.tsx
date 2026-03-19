import clsx from 'clsx'

interface CardProps {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
  accent?: 'success' | 'warning' | 'danger' | 'primary' | null
  hoverable?: boolean
  onClick?: () => void
}

const paddings = { none: '', sm: 'p-3', md: 'p-5', lg: 'p-6' }
const accents = {
  success: 'border-l-4 border-l-success-500',
  warning: 'border-l-4 border-l-warning-500',
  danger: 'border-l-4 border-l-danger-500',
  primary: 'border-l-4 border-l-primary-500',
}

export function Card({
  children,
  className,
  padding = 'md',
  accent = null,
  hoverable = false,
  onClick,
}: CardProps) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'bg-white border border-gray-200 rounded-lg shadow-xs',
        paddings[padding],
        accent && accents[accent],
        hoverable && 'hover:shadow-sm transition-shadow cursor-pointer',
        className,
      )}
    >
      {children}
    </div>
  )
}
