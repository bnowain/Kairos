import { apiFetch } from './client'
import type { HealthStatus, Config } from './types'

export function fetchHealth(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>('/api/health')
}

export function fetchConfig(): Promise<Config> {
  return apiFetch<Config>('/api/config')
}
