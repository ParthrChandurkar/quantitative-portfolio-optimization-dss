import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { AlertRecord, OptiVestApi } from '../../lib/api/client'
import { ApiProvider } from '../../lib/api/context'
import { NotificationBell } from '../NotificationBell'

const alert: AlertRecord = {
  id: 'alert-1',
  portfolio_id: 'portfolio-1',
  snapshot_id: 'snapshot-2',
  stock_id: null,
  alert_type: 'RISK_DRIFT',
  severity: 'critical',
  message: 'Portfolio expected volatility is 0.31, above the moderate profile target of 0.22.',
  grounding: { expected_volatility: 0.31, recommended_risk_tolerance: 0.22 },
  acknowledged: false,
  created_at: '2026-08-22T10:00:00Z',
}

function show(overrides: Partial<OptiVestApi> = {}) {
  const api = {
    alerts: vi.fn().mockResolvedValue([alert]),
    acknowledgeAlert: vi.fn().mockResolvedValue({ ...alert, acknowledged: true }),
    ...overrides,
  } as OptiVestApi
  const query = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={query}><ApiProvider client={api}><NotificationBell/></ApiProvider></QueryClientProvider>)
  return api
}

describe('NotificationBell', () => {
  it('shows unread count, grounded alert content, and acknowledges on click', async () => {
    const api = show()
    expect(await screen.findByRole('button', { name: 'Notifications (1 unread)' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Notifications (1 unread)' }))
    expect(await screen.findByText(alert.message)).toBeInTheDocument()
    expect(screen.getByText(/grounded in expected_volatility, recommended_risk_tolerance/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /RISK DRIFT/ }))
    expect(api.acknowledgeAlert).toHaveBeenCalledWith('alert-1')
  })

  it('renders loading state while alerts are fetched', async () => {
    show({ alerts: vi.fn(() => new Promise<AlertRecord[]>(() => undefined)) })
    await userEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(screen.getByRole('status')).toHaveTextContent('Loading alerts')
  })

  it('renders a real-client error state', async () => {
    show({ alerts: vi.fn().mockRejectedValue(new Error('alerts unavailable')) })
    await userEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('alerts unavailable')
  })
})
