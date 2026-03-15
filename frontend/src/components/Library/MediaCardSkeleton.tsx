import { Skeleton } from '../ui/Skeleton'

export function MediaCardSkeleton() {
  return (
    <div className="flex flex-row sm:flex-col rounded-lg bg-gray-900 border border-gray-800 overflow-hidden">
      <Skeleton className="w-28 h-20 sm:w-auto sm:aspect-video rounded-none" />
      <div className="flex-1 p-3 flex flex-col gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-1/3" />
      </div>
    </div>
  )
}
