import { NavLink } from 'react-router-dom'
import { Film, Scissors, Zap, Video, Settings } from 'lucide-react'
import { cn } from '../../utils/cn'

const navItems = [
  { to: '/',       label: 'Library', icon: Film,     end: true  },
  { to: '/clips',  label: 'Clips',   icon: Scissors, end: false },
  { to: '/quick',  label: 'Quick',   icon: Zap,      end: false },
  { to: '/render', label: 'Render',  icon: Video,    end: false },
  { to: '/settings', label: 'Settings', icon: Settings, end: false },
]

export function BottomNav() {
  return (
    <nav className="md:hidden flex items-center justify-around border-t border-gray-800 bg-gray-900 pb-safe">
      {navItems.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) =>
            cn(
              'flex flex-col items-center gap-1 px-3 py-2 text-xs font-medium transition-colors',
              isActive ? 'text-blue-400' : 'text-gray-500',
            )
          }
        >
          <Icon className="h-5 w-5" />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
