import { NavLink } from 'react-router-dom'
import { Film, Scissors, Bolt, Zap, Video, Settings, ClipboardList } from 'lucide-react'
import { cn } from '../../utils/cn'

const navItems = [
  { to: '/',        label: 'Library',       icon: Film,     end: true  },
  { to: '/clips',   label: 'Clips',         icon: Scissors, end: false },
  { to: '/quick',   label: 'Quick',         icon: Bolt,     end: false },
  { to: '/jobs',    label: 'Jobs',          icon: ClipboardList, end: false },
  { to: '/stories', label: 'Story Builder', icon: Zap,      end: false },
  { to: '/render',  label: 'Render Queue',  icon: Video,    end: false },
  { to: '/settings',label: 'Settings',      icon: Settings, end: false },
]

export function Sidebar() {
  return (
    <aside className="hidden md:flex w-56 shrink-0 flex-col bg-gray-900 border-r border-gray-800 h-full">
      <div className="px-4 py-5 border-b border-gray-800">
        <span className="text-lg font-bold text-white tracking-tight">Kairos</span>
        <p className="text-xs text-gray-500 mt-0.5">AI Video Clipping</p>
      </div>
      <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-600/20 text-blue-400'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100',
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
