import * as RadixTabs from '@radix-ui/react-tabs'
import { cn } from '../../utils/cn'
import type { ReactNode } from 'react'

interface Tab {
  value: string
  label: ReactNode
  content: ReactNode
}

interface TabsProps {
  value: string
  onValueChange: (value: string) => void
  tabs: Tab[]
  className?: string
}

export function Tabs({ value, onValueChange, tabs, className }: TabsProps) {
  return (
    <RadixTabs.Root
      value={value}
      onValueChange={onValueChange}
      className={cn('flex flex-col', className)}
    >
      <RadixTabs.List className="flex border-b border-gray-800 gap-1 px-1">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.value}
            value={tab.value}
            className="px-4 py-2.5 text-sm font-medium text-gray-500 transition-colors hover:text-gray-300 data-[state=active]:text-blue-400 data-[state=active]:border-b-2 data-[state=active]:border-blue-400 data-[state=active]:-mb-px"
          >
            {tab.label}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {tabs.map((tab) => (
        <RadixTabs.Content key={tab.value} value={tab.value} className="flex-1 overflow-auto">
          {tab.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  )
}
