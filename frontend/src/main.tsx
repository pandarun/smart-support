import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'

/**
 * React Query Client Configuration
 *
 * Configured for Smart Support API requirements:
 * - No automatic retries (API should respond reliably)
 * - Short stale time (data changes frequently during operator workflow)
 * - Cache time for performance (avoid re-fetching during active session)
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't retry failed requests automatically (let user retry manually)
      retry: false,
      // Mark data as stale after 30 seconds (balance freshness vs. performance)
      staleTime: 30 * 1000,
      // Keep unused data in cache for 5 minutes
      gcTime: 5 * 60 * 1000,
      // Don't refetch on window focus (operator may switch windows frequently)
      refetchOnWindowFocus: false,
      // Don't refetch on reconnect (operator should manually retry if needed)
      refetchOnReconnect: false,
    },
    mutations: {
      // Don't retry mutations (classification/retrieval should be user-initiated)
      retry: false,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
