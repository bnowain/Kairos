import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { TopBar } from '../components/Layout/TopBar'
import { TemplateSelector } from '../components/StoryBuilder/TemplateSelector'
import { StoryForm } from '../components/StoryBuilder/StoryForm'
import { TimelinePreview } from '../components/StoryBuilder/TimelinePreview'
import { Spinner } from '../components/ui/Spinner'
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
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
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
              <div className="flex flex-col items-center justify-center h-48 rounded-lg border border-dashed border-gray-700 text-gray-500">
                <p className="text-sm">Select a template and generate a story</p>
                <p className="text-xs mt-1">The timeline preview will appear here</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
