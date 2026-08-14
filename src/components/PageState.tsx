import { Navigate } from 'react-router-dom'
import { AlertTriangle, LoaderCircle, RefreshCw } from 'lucide-react'
import { OptiVestApiError } from '../lib/api/client'

export function PageLoading({ label = 'Loading live OptiVest data…' }: { label?: string }) {
  return <div className="page-state" role="status"><LoaderCircle className="spin"/><strong>{label}</strong><div className="skeleton-lines"><i/><i/><i/></div></div>
}

export function PageError({ error, retry }: { error: unknown; retry?: () => void }) {
  if (error instanceof OptiVestApiError && error.status === 401) return <Navigate to="/auth" replace />
  const status = error instanceof OptiVestApiError ? error.status : 0
  const message = error instanceof Error ? error.message : 'The request could not be completed.'
  return <div className="page-state error-state" role="alert"><AlertTriangle/><strong>{status === 403 ? 'Access denied' : status >= 500 ? 'OptiVest service error' : 'Unable to load data'}</strong><p>{message}</p>{retry&&<button className="secondary" onClick={retry}><RefreshCw/>Try again</button>}</div>
}

export function EmptyState({ children }: { children: React.ReactNode }) {
  return <div className="page-state"><p>{children}</p></div>
}
