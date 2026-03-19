import { useEffect } from 'react'
import clsx from 'clsx'

interface ToastProps {
  message: string
  tone: 'success' | 'error' | 'info'
  onDismiss: () => void
  duration?: number
}

const toneClasses = {
  success: 'bg-success-50 text-success-700 border-success-200',
  error: 'bg-danger-50 text-danger-700 border-danger-200',
  info: 'bg-gray-50 text-gray-700 border-gray-200',
}

export function Toast({ message, tone, onDismiss, duration = 4000 }: ToastProps) {
  useEffect(() => {
    const timer = setTimeout(onDismiss, duration)
    return () => clearTimeout(timer)
  }, [onDismiss, duration])

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-toast">
      <div
        className={clsx(
          'px-4 py-2.5 rounded-lg border shadow-md text-sm font-medium flex items-center gap-2',
          toneClasses[tone],
        )}
      >
        <span>{message}</span>
        <button onClick={onDismiss} className="ml-2 opacity-60 hover:opacity-100 text-lg leading-none">
          &times;
        </button>
      </div>
    </div>
  )
}
