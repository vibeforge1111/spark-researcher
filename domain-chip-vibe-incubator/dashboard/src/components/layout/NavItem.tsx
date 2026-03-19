import clsx from 'clsx'

interface NavItemProps {
  label: string
  icon: string
  active: boolean
  badge?: number
  onClick: () => void
}

export function NavItem({ label, icon, active, badge, onClick }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-colors text-left',
        active
          ? 'bg-primary-50 text-primary-700'
          : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
      )}
    >
      <span className="text-base leading-none w-5 text-center">{icon}</span>
      <span className="truncate">{label}</span>
      {badge != null && badge > 0 && (
        <span className="ml-auto bg-danger-500 text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
          {badge}
        </span>
      )}
    </button>
  )
}
