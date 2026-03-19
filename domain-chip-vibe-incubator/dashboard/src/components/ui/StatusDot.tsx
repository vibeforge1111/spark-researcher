import clsx from 'clsx'

interface StatusDotProps {
  status: 'green' | 'yellow' | 'red' | 'gray'
  size?: 'sm' | 'md'
  pulse?: boolean
  className?: string
}

const colors = {
  green: 'bg-success-500',
  yellow: 'bg-warning-500',
  red: 'bg-danger-500',
  gray: 'bg-gray-400',
}

const dims = { sm: 'w-2 h-2', md: 'w-2.5 h-2.5' }

export function StatusDot({ status, size = 'md', pulse = false, className }: StatusDotProps) {
  return (
    <span
      className={clsx(
        'inline-block rounded-full shrink-0',
        colors[status],
        dims[size],
        pulse && 'animate-pulse-dot',
        className,
      )}
    />
  )
}
