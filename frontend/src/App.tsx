import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppShell } from './components/Layout/AppShell'
import LibraryPage from './pages/LibraryPage'
import ItemPage from './pages/ItemPage'
import ClipsPage from './pages/ClipsPage'
import QuickJobPage from './pages/QuickJobPage'
import JobHistoryPage from './pages/JobHistoryPage'
import StoryPage from './pages/StoryPage'
import TimelinePage from './pages/TimelinePage'
import RenderPage from './pages/RenderPage'
import SettingsPage from './pages/SettingsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5000,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell>
          <Routes>
            <Route path="/" element={<LibraryPage />} />
            <Route path="/item/:item_id" element={<ItemPage />} />
            <Route path="/clips" element={<ClipsPage />} />
            <Route path="/quick" element={<QuickJobPage />} />
            <Route path="/jobs" element={<JobHistoryPage />} />
            <Route path="/stories" element={<StoryPage />} />
            <Route path="/timeline/:timeline_id" element={<TimelinePage />} />
            <Route path="/render" element={<RenderPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </AppShell>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
