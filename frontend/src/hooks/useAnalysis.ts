import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchHighlights, startAnalysis } from '../api/analysis'

export function useHighlights(itemId: string) {
  return useQuery({
    queryKey: ['highlights', itemId],
    queryFn: () => fetchHighlights(itemId),
    enabled: !!itemId,
  })
}

export function useStartAnalysis() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => startAnalysis(itemId),
    onSuccess: (_data, itemId) => {
      void qc.invalidateQueries({ queryKey: ['highlights', itemId] })
      void qc.invalidateQueries({ queryKey: ['media-item', itemId] })
    },
  })
}
