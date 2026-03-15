import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Clapperboard } from 'lucide-react'
import { TopBar } from '../components/Layout/TopBar'
import { TemplateSelector } from '../components/StoryBuilder/TemplateSelector'
import { StoryForm } from '../components/StoryBuilder/StoryForm'
import { TimelinePreview } from '../components/StoryBuilder/TimelinePreview'
import { Skeleton } from '../components/ui/Skeleton'
import { EmptyState } from '../components/ui/EmptyState'
import { fetchTemplates, generateStory } from '../api/stories'
import { fetchLibrary } from '../api/library'
import type { Timeline } from '../api/types'

export default function StoryPage() {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [generatedTimeline, setGeneratedTimeline] = useState<Timeline | null>(null)

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: fetchTemplates,
  })

  const { data: libraryData, isLoading: libraryLoading } = useQuery({
    queryKey: ['library', { page_size: 100 }],
    queryFn: () => fetchLibrary({ page_size: 100 }),
  })

  const { mutate: generate, isPending: generating } = useMutation({
    mutationFn: generateStory,
    onSuccess: (timeline) => {
      setGeneratedTimeline(timeline)
    },
  })

  if (templatesLoading || libraryLoading) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <TopBar title="Story Builder" />
        <div className="flex-1 overflow-y-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 max-w-6xl mx-auto">
            <div className="flex flex-col gap-6">
              <Skeleton className="h-40 w-full" />
              <Skeleton className="h-56 w-full" />
            </div>
            <Skeleton className="h-48 w-full rounded-lg border border-dashed border-gray-700" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <TopBar title="Story Builder" />
      <div className="flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 max-w-6xl mx-auto">
          {/* Left column */}
          <div className="flex flex-col gap-6">
            <div>
              <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
                Story Template
              </h2>
              <TemplateSelector
                templates={templates}
                selectedId={selectedTemplateId}
                onSelect={setSelectedTemplateId}
              />
            </div>

            <div>
              <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
                Configure
              </h2>
              <StoryForm
                items={libraryData?.items ?? []}
                templateId={selectedTemplateId}
                onGenerate={(params) => {
                  if (!selectedTemplateId) return
                  generate({ template_id: selectedTemplateId, ...params })
                }}
                isLoading={generating}
              />
            </div>
          </div>

          {/* Right column */}
          <div>
            {generatedTimeline ? (
              <div>
                <h2 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wide">
                  Generated Timeline
                </h2>
                <div className="rounded-lg bg-gray-900 border border-gray-800 p-4">
                  <TimelinePreview timeline={generatedTimeline} />
                </div>
              </div>
            ) : (
              <EmptyState
                icon={Clapperboard}
                heading="No timeline yet"
                description="Select a template and generate a story to see the timeline preview."
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
