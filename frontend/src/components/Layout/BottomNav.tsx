import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Film, Scissors, Zap, Rss,
  Search, ClipboardList, BookOpen, Video, Type, Settings,
  MoreHorizontal, X,
} from 'lucide-react'
import { cn } from '../../utils/cn'

const primaryItems = [
  { to: '/',       label: 'Library', icon: Film,     end: true  },
  { to: '/clips',  label: 'Clips',   icon: Scissors, end: false },
  { to: '/quick',  label: 'Quick',   icon: Zap,      end: false },
  { to: '/sources',label: 'Sources', icon: Rss,      end: false },
]

const overflowItems = [
  { to: '/smart-query', label: 'Smart Query', icon: Search },
  { to: '/jobs',        label: 'Jobs',        icon: ClipboardList },
  { to: '/stories',     label: 'Stories',     icon: BookOpen },
  { to: '/render',      label: 'Render',      icon: Video },
  { to: '/captions',    label: 'Captions',    icon: Type },
  { to: '/settings',    label: 'Settings',    icon: Settings },
]

const overflowPaths = overflowItems.map((i) => i.to)

export function BottomNav() {
  const [moreOpen, setMoreOpen] = useState(false)
  const location = useLocation()
  const isOverflowActive = overflowPaths.some((p) => location.pathname.startsWith(p))

  return (
    <>
      {/* Overflow panel */}
      {moreOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 z-40 bg-black/40"
            onClick={() => setMoreOpen(false)}
          />
          <div className="md:hidden fixed bottom-[calc(3.5rem+env(safe-area-inset-bottom))] left-0 right-0 z-50 mx-2 rounded-t-xl bg-gray-900 border border-gray-800 border-b-0 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-gray-300">More</span>
              <button onClick={() => setMoreOpen(false)} className="p-1 text-gray-500 hover:text-gray-300">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {overflowItems.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setMoreOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-2 rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
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
            </div>
          </div>
        </>
      )}

      {/* Bottom bar */}
      <nav className="md:hidden flex items-center justify-around border-t border-gray-800 bg-gray-900 pb-safe">
        {primaryItems.map(({ to, label, icon: Icon, end }) => (
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
        <button
          onClick={() => setMoreOpen((v) => !v)}
          className={cn(
            'flex flex-col items-center gap-1 px-3 py-2 text-xs font-medium transition-colors',
            moreOpen || isOverflowActive ? 'text-blue-400' : 'text-gray-500',
          )}
        >
          <MoreHorizontal className="h-5 w-5" />
          More
        </button>
      </nav>
    </>
  )
}
