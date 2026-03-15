import { Skeleton } from '../ui/Skeleton'

export function ClipCardSkeleton() {
  return (
    <div className="rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
      <Skeleton className="aspect-video w-full rounded-none" />
      <div className="p-3 flex flex-col gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    </div>
  )
}
